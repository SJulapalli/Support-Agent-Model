from typing import AsyncIterator
import json
import anthropic
from app.config import settings
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import TOOLS
from app.browser.agent import run_browser_task
from app.rag.retrieve import retrieve_context

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

# In-memory conversation store keyed by conversation_id.
# Replace with DB-backed storage for production.
_conversations: dict[str, list[dict]] = {}


async def run_agent(conversation_id: str, user_message: str) -> AsyncIterator[str]:
    history = _conversations.setdefault(conversation_id, [])
    history.append({"role": "user", "content": user_message})

    context = await retrieve_context(user_message)
    system = SYSTEM_PROMPT
    if context:
        system += f"\n\nRelevant policy context:\n{context}"

    while True:
        full_text = ""

        async with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            messages=history,
            tools=TOOLS,
        ) as s:
            async for event in s:
                if event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        full_text += event.delta.text
                        yield _sse("text", event.delta.text)

            final = await s.get_final_message()

        stop_reason = final.stop_reason

        if stop_reason == "tool_use":
            for block in final.content:
                if block.type == "tool_use":
                    yield _sse("status", "agent_working")
                    task = block.input.get("task", "")
                    result = await run_browser_task(task)

                    history.append({"role": "assistant", "content": final.content})
                    history.append({
                        "role": "user",
                        "content": [{"type": "tool_result", "tool_use_id": block.id, "content": result}],
                    })
                    break
            continue

        history.append({"role": "assistant", "content": final.content})

        if "[ESCALATE]" in full_text:
            yield _sse("status", "escalated")

        yield _sse("done", "")
        break


def _sse(event_type: str, content: str) -> str:
    return f"data: {json.dumps({'type': event_type, 'content': content})}\n\n"
