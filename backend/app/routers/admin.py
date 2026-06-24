import re
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from app.database import get_db
from app.models.order import Order, OrderItem
from app.models.customer import Customer
from app.models.refund import Refund
from app.models.agent_event import AgentEvent
from app.models.escalation_handoff import EscalationHandoff

_ORDER_URL_RE = re.compile(r'/orders/(\d+)')

router = APIRouter()


class RefundRequest(BaseModel):
    reason: str
    category: str = "Other"
    amount_cents: int | None = None


class CancelRequest(BaseModel):
    reason: str


@router.get("/orders")
async def list_orders(
    name: str | None = Query(default=None),
    email: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Order)
        .join(Order.customer)
        .options(selectinload(Order.customer))
        .order_by(Order.created_at.desc())
    )
    if name:
        stmt = stmt.where(Customer.name.ilike(f"%{name}%"))
    if email:
        stmt = stmt.where(Customer.email.ilike(f"%{email}%"))
    if status:
        stmt = stmt.where(Order.status == status)

    result = await db.execute(stmt)
    orders = result.scalars().all()
    return [_serialize_order_summary(o) for o in orders]


@router.get("/orders/{order_id}")
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.customer),
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.refund),
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _serialize_order_detail(order)


@router.post("/orders/{order_id}/refund")
async def issue_refund(order_id: int, req: RefundRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.refund))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "delivered":
        raise HTTPException(status_code=400, detail="Order not eligible for refund")
    if order.refund:
        raise HTTPException(status_code=400, detail="Refund already issued")

    amount = req.amount_cents if req.amount_cents and req.amount_cents < order.total_cents else order.total_cents
    stored_reason = f"[{req.category}] {req.reason}"
    refund = Refund(order_id=order_id, amount_cents=amount, reason=stored_reason)
    order.status = "refunded"
    db.add(refund)
    await db.commit()
    return {"status": "ok", "refund_id": refund.id}


@router.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: int, req: CancelRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in ("pending", "processing"):
        raise HTTPException(status_code=400, detail="Only pending or processing orders can be cancelled")

    order.status = "cancelled"
    await db.commit()
    return {"status": "ok"}


def _serialize_order_summary(order: Order) -> dict:
    return {
        "id": order.id,
        "customerId": order.customer_id,
        "customerName": order.customer.name,
        "customerEmail": order.customer.email,
        "status": order.status,
        "totalCents": order.total_cents,
        "createdAt": order.created_at.isoformat(),
    }


def _serialize_order_detail(order: Order) -> dict:
    return {
        **_serialize_order_summary(order),
        "items": [
            {
                "id": item.id,
                "productName": item.product.name,
                "quantity": item.quantity,
                "priceCents": item.price_cents,
            }
            for item in order.items
        ],
        "refund": {
            "id": order.refund.id,
            "orderId": order.refund.order_id,
            "amountCents": order.refund.amount_cents,
            "reason": order.refund.reason,
            "status": order.refund.status,
            "createdAt": order.refund.created_at.isoformat(),
        } if order.refund else None,
    }


@router.get("/conversations")
async def list_conversations(db: AsyncSession = Depends(get_db)):
    agg = await db.execute(
        select(
            AgentEvent.conversation_id,
            func.min(AgentEvent.timestamp).label("first_event"),
            func.max(AgentEvent.timestamp).label("last_event"),
            func.count().label("event_count"),
        )
        .group_by(AgentEvent.conversation_id)
        .order_by(func.max(AgentEvent.timestamp).desc())
    )
    rows = agg.all()
    if not rows:
        return []

    conv_ids = [r.conversation_id for r in rows]

    esc_res = await db.execute(
        select(EscalationHandoff).where(EscalationHandoff.conversation_id.in_(conv_ids))
    )
    escalations = {h.conversation_id: h for h in esc_res.scalars().all()}

    nav_res = await db.execute(
        select(AgentEvent.conversation_id, AgentEvent.payload)
        .where(
            AgentEvent.conversation_id.in_(conv_ids),
            AgentEvent.event_type == "browser_action",
        )
    )
    order_ids_by_conv: dict[str, list[int]] = {}
    for nav_row in nav_res.all():
        p = nav_row.payload or {}
        if p.get("action") == "navigate":
            url = (p.get("details") or {}).get("url", "")
            m = _ORDER_URL_RE.search(url)
            if m:
                oid = int(m.group(1))
                lst = order_ids_by_conv.setdefault(nav_row.conversation_id, [])
                if oid not in lst:
                    lst.append(oid)

    return [
        {
            "conversationId": r.conversation_id,
            "firstEvent": r.first_event.isoformat(),
            "lastEvent": r.last_event.isoformat(),
            "eventCount": r.event_count,
            "escalated": r.conversation_id in escalations,
            "customer": escalations[r.conversation_id].customer if r.conversation_id in escalations else None,
            "escalationReason": escalations[r.conversation_id].reason if r.conversation_id in escalations else None,
            "orderIds": order_ids_by_conv.get(r.conversation_id, []),
        }
        for r in rows
    ]


@router.get("/conversations/{conversation_id}/events")
async def get_conversation_events(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AgentEvent)
        .where(AgentEvent.conversation_id == conversation_id)
        .order_by(AgentEvent.timestamp.asc())
    )
    events = result.scalars().all()
    return [
        {
            "id": e.id,
            "conversationId": e.conversation_id,
            "timestamp": e.timestamp.isoformat(),
            "eventType": e.event_type,
            "payload": e.payload,
        }
        for e in events
    ]


@router.get("/conversations/{conversation_id}/handoff")
async def get_conversation_handoff(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EscalationHandoff).where(EscalationHandoff.conversation_id == conversation_id)
    )
    handoff = result.scalar_one_or_none()
    if not handoff:
        return None
    return {
        "conversationId": handoff.conversation_id,
        "reason": handoff.reason,
        "customer": handoff.customer,
        "ordersReviewed": handoff.orders_reviewed,
        "actionsAttempted": handoff.actions_attempted,
        "sentiment": handoff.sentiment,
        "recommendedNextStep": handoff.recommended_next_step,
        "createdAt": handoff.created_at.isoformat(),
    }
