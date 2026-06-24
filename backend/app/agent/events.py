from app.database import SessionLocal
from app.models.agent_event import AgentEvent


async def log_event(conversation_id: str, event_type: str, payload: dict) -> None:
    async with SessionLocal() as session:
        session.add(AgentEvent(
            conversation_id=conversation_id,
            event_type=event_type,
            payload=payload,
        ))
        await session.commit()