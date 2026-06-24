import json
import anthropic
from app.config import settings

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

VERIFIER_SYSTEM = """You are a response quality verifier for an AI customer support agent.

You will be given:
1. The agent's system prompt (which defines policies and rules)
2. The conversation history
3. The agent's most recent response (the one to verify)

Check the response for exactly three types of violations:
1. **Policy violation**: The agent promised something that violates the rules in the system prompt (e.g., offered a refund outside the allowed window, disclosed confidential info).
2. **Self-contradiction**: The agent stated something that directly contradicts a fact it established earlier in the same conversation.
3. **Unverified factual claim**: The agent stated specific order details (status, total, items, dates) without having retrieved that data via a tool call in this conversation.

Be strict about false positives — only flag when you have high confidence the response is clearly wrong.
General, hedged statements ("I can look that up for you") are NOT violations.

Respond with JSON only — no other text:
- If no violation: {"result": "ok"}
- If violation found: {"result": "correction", "text": "<the full corrected response text>"}

The corrected text should fix only the violation — keep everything else from the original response.
"""


def _safe_history(history: list[dict]) -> list[dict]:
    """Convert history to JSON-safe dicts — Anthropic SDK content blocks are not serializable."""
    result = []
    for msg in history:
        content = msg.get("content")
        if isinstance(content, str):
            result.append({"role": msg["role"], "content": content})
        elif isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "tool_result":
                        parts.append(f"[tool_result: {block.get('content', '')}]")
                    else:
                        parts.append(str(block))
                elif hasattr(block, "text"):
                    parts.append(block.text)
                elif hasattr(block, "type"):
                    parts.append(f"[{block.type}]")
                else:
                    parts.append(str(block))
            result.append({"role": msg["role"], "content": " ".join(parts)})
        else:
            result.append({"role": msg["role"], "content": str(content) if content else ""})
    return result


async def verify_response(
    response_text: str,
    conversation_history: list[dict],
    system_prompt: str,
) -> str | None:
    """Returns corrected text if a violation is found, None if response is clean."""
    prompt = f"""System prompt the agent follows:
<system_prompt>
{system_prompt}
</system_prompt>

Conversation history (most recent last):
<history>
{json.dumps(_safe_history(conversation_history[-10:]), indent=2)}
</history>

Agent's response to verify:
<response>
{response_text}
</response>

Check for violations and respond with JSON."""

    try:
        result = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=VERIFIER_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = result.content[0].text.strip()
        parsed = json.loads(raw)
        if parsed.get("result") == "correction":
            return parsed.get("text")
        return None
    except Exception:
        return None