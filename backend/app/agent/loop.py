from typing import AsyncIterator
import asyncio
import json
import re
import anthropic
from app.config import settings
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import TOOLS
from app.agent.events import log_event
from app.agent.verifier import verify_response
from app.browser.agent import run_browser_task
from app.browser.site_config import active_site
from app.rag.retrieve import retrieve_context

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

_conversations: dict[str, list[dict]] = {}


async def run_agent(conversation_id: str, user_message: str) -> AsyncIterator[str]:
    history = _conversations.setdefault(conversation_id, [])
    history.append({"role": "user", "content": user_message})

    context = await retrieve_context(user_message)
    site = active_site()

    # Build system prompt: generic base + site workflows/policies + RAG context
    system = SYSTEM_PROMPT

    system += (
        f"\n\nYou are working on behalf of a support team for this portal:\n{site.orientation}"
        f"\n\nWorkflows you are authorised to perform:\n"
        + "\n".join(f"- {w}" for w in site.workflows)
        + f"\n\nPolicies you must follow:\n"
        + "\n".join(f"- {p}" for p in site.policies)
    )

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

                    await log_event(conversation_id, "tool_call", {"tool_name": block.name, "input": task})
                    yield _sse("action_log", {"event_type": "tool_call", "payload": {"tool_name": block.name, "input": task}})

                    result = await run_browser_task(task, conversation_id=conversation_id)

                    result_summary = result[:500]
                    await log_event(conversation_id, "tool_result", {"tool_name": block.name, "result_summary": result_summary})
                    yield _sse("action_log", {"event_type": "tool_result", "payload": {"tool_name": block.name, "result_summary": result_summary}})

                    history.append({"role": "assistant", "content": final.content})
                    history.append({
                        "role": "user",
                        "content": [{"type": "tool_result", "tool_use_id": block.id, "content": result}],
                    })
                    break
            continue

        # End-of-turn text response — run verifier before finalizing
        if "[ESCALATE]" in full_text:
            handoff = _extract_handoff(full_text, conversation_id)
            clean_text = _strip_handoff_from_text(full_text)
            await _persist_handoff(conversation_id, handoff, full_text)
            await log_event(conversation_id, "agent_escalate", {"reason": handoff.get("reason", "unspecified")})
            # Replace the streamed text (which contains the raw JSON block) with the clean version
            yield _sse("correction", clean_text)
            yield _sse("handoff", handoff)
            yield _sse("status", "escalated")
            history.append({"role": "assistant", "content": final.content})
            yield _sse("done", "")
            break

        # Run verifier in parallel; await before emitting done so correction arrives while client is pacing
        correction = await verify_response(full_text, history, system)

        history.append({"role": "assistant", "content": final.content})

        if correction:
            yield _sse("correction", correction)

        yield _sse("done", "")
        break


def _strip_handoff_from_text(text: str) -> str:
    clean = re.sub(r"```json\s*\{.*?\}\s*```", "", text, flags=re.DOTALL).strip()
    clean = clean.replace("[ESCALATE]", "").strip()
    return clean


def _extract_handoff(full_text: str, conversation_id: str) -> dict:
    match = re.search(r"```json\s*(\{.*?\})\s*```", full_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return {}


async def _persist_handoff(conversation_id: str, handoff: dict, raw_text: str) -> None:
    from app.database import SessionLocal
    from app.models.escalation_handoff import EscalationHandoff
    async with SessionLocal() as session:
        record = EscalationHandoff(
            conversation_id=conversation_id,
            reason=handoff.get("reason"),
            customer=handoff.get("customer"),
            orders_reviewed=handoff.get("orders_reviewed"),
            actions_attempted=handoff.get("actions_attempted"),
            sentiment=handoff.get("sentiment"),
            recommended_next_step=handoff.get("recommended_next_step"),
            raw_summary=raw_text if not handoff else None,
        )
        session.add(record)
        try:
            await session.commit()
        except Exception:
            await session.rollback()


def _sse(event_type: str, content) -> str:
    return f"data: {json.dumps({'type': event_type, 'content': content})}\n\n"