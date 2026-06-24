from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class EscalationHandoff(Base):
    __tablename__ = "escalation_handoffs"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(String, nullable=False, unique=True)
    reason = Column(Text)
    customer = Column(String)
    orders_reviewed = Column(JSONB)
    actions_attempted = Column(JSONB)
    sentiment = Column(String(50))
    recommended_next_step = Column(Text)
    raw_summary = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)