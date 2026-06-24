from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class AgentEvent(Base):
    __tablename__ = "agent_events"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(JSONB, nullable=False, server_default="{}")