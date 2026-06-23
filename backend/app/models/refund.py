from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(50), default="approved")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    order: Mapped["Order"] = relationship(back_populates="refund")  # noqa: F821
