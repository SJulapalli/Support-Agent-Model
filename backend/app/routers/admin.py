from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from app.database import get_db
from app.models.order import Order, OrderItem
from app.models.customer import Customer
from app.models.refund import Refund

router = APIRouter()


class RefundRequest(BaseModel):
    reason: str


@router.get("/orders")
async def list_orders(
    name: str | None = Query(default=None),
    email: str | None = Query(default=None),
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

    refund = Refund(order_id=order_id, amount_cents=order.total_cents, reason=req.reason)
    order.status = "refunded"
    db.add(refund)
    await db.commit()
    return {"status": "ok", "refund_id": refund.id}


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
