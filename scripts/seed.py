"""
Seed the database with realistic NorthShop demo data.
Usage: cd backend && python ../scripts/seed.py
"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.customer import Customer
from app.models.order import Order, OrderItem, Product
from app.models.refund import Refund
from app.database import Base

DATABASE_URL = "postgresql+asyncpg://northshop:northshop@localhost:5432/northshop"

engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(engine)

PRODUCTS = [
    Product(id=1, name="Merino Wool Sweater",  price_cents=8900,  category="Clothing"),
    Product(id=2, name="Leather Wallet",        price_cents=4500,  category="Accessories"),
    Product(id=3, name="Running Shoes",         price_cents=12000, category="Footwear"),
    Product(id=4, name="Denim Jacket",          price_cents=9500,  category="Clothing"),
    Product(id=5, name="Ceramic Coffee Mug",    price_cents=2200,  category="Homewares"),
    # Higher-value items for the >$500 escalation case
    Product(id=6, name="Cashmere Overcoat",     price_cents=28900, category="Clothing"),
    Product(id=7, name="Smart Watch",           price_cents=24900, category="Electronics"),
]

CUSTOMERS = [
    Customer(id=1, name="Alice Chen",   email="alice@example.com"),
    Customer(id=2, name="Bob Martinez", email="bob@example.com"),
    Customer(id=3, name="Carol White",  email="carol@example.com"),
    Customer(id=4, name="Diana Park",   email="diana@example.com"),
]

now = datetime.utcnow()

ORDERS = [
    # --- TIER 1: full refund (product issue, ≤30 days) ---
    Order(id=1001, customer_id=1, status="delivered", total_cents=8900,
          created_at=now - timedelta(days=5)),
    # hero demo order
    Order(id=1042, customer_id=2, status="delivered", total_cents=17900,
          created_at=now - timedelta(days=10)),

    # --- TIER 2: 75% partial (product issue, 31–60 days) ---
    # Also covers TIER 4 (no refund for changed mind >30 days)
    Order(id=1002, customer_id=1, status="delivered", total_cents=13500,
          created_at=now - timedelta(days=45)),

    # --- TIER 3: 50% partial (changed mind, ≤30 days) ---
    Order(id=1005, customer_id=3, status="delivered", total_cents=18400,
          created_at=now - timedelta(days=20)),

    # --- ESCALATE: product issue older than 60 days ---
    Order(id=1006, customer_id=1, status="delivered", total_cents=8900,
          created_at=now - timedelta(days=65)),

    # --- ESCALATE: order total exceeds $500 ---
    Order(id=1007, customer_id=4, status="delivered", total_cents=53800,
          created_at=now - timedelta(days=8)),

    # --- ALREADY REFUNDED: cannot refund again ---
    Order(id=1008, customer_id=2, status="refunded", total_cents=4500,
          created_at=now - timedelta(days=15)),

    # --- NOT YET DELIVERED ---
    Order(id=1003, customer_id=2, status="shipped",     total_cents=12000,
          created_at=now - timedelta(days=3)),

    # --- CANCEL-ELIGIBLE: processing ---
    Order(id=1004, customer_id=3, status="processing",  total_cents=4500,
          created_at=now - timedelta(days=1)),

    # --- CANCEL-ELIGIBLE: pending ---
    Order(id=1009, customer_id=3, status="pending",     total_cents=4400,
          created_at=now - timedelta(hours=2)),
]

ORDER_ITEMS = [
    # #1001 — Alice, Merino Wool Sweater ($89)
    OrderItem(order_id=1001, product_id=1, quantity=1, price_cents=8900),

    # #1042 — Bob, hero order: Merino Wool Sweater + Running Shoes ($89+$120→stored as $179)
    OrderItem(order_id=1042, product_id=1, quantity=1, price_cents=8900),
    OrderItem(order_id=1042, product_id=3, quantity=1, price_cents=9000),

    # #1002 — Alice, Running Shoes + Leather Wallet ($120+$45=$165 → stored as $135, flat)
    OrderItem(order_id=1002, product_id=3, quantity=1, price_cents=12000),
    OrderItem(order_id=1002, product_id=2, quantity=1, price_cents=4500),

    # #1005 — Carol, Denim Jacket + Merino Wool Sweater ($95+$89=$184)
    OrderItem(order_id=1005, product_id=4, quantity=1, price_cents=9500),
    OrderItem(order_id=1005, product_id=1, quantity=1, price_cents=8900),

    # #1006 — Alice, Merino Wool Sweater ($89) — old order, escalate if product issue
    OrderItem(order_id=1006, product_id=1, quantity=1, price_cents=8900),

    # #1007 — Diana, Cashmere Overcoat + Smart Watch ($289+$249=$538) — high-value, escalate
    OrderItem(order_id=1007, product_id=6, quantity=1, price_cents=28900),
    OrderItem(order_id=1007, product_id=7, quantity=1, price_cents=24900),

    # #1008 — Bob, Leather Wallet ($45) — already refunded
    OrderItem(order_id=1008, product_id=2, quantity=1, price_cents=4500),

    # #1003 — Bob, Running Shoes ($120)
    OrderItem(order_id=1003, product_id=3, quantity=1, price_cents=12000),

    # #1004 — Carol, Leather Wallet ($45) — processing, cancel-eligible
    OrderItem(order_id=1004, product_id=2, quantity=1, price_cents=4500),

    # #1009 — Carol, Ceramic Coffee Mug ×2 ($44) — pending, cancel-eligible
    OrderItem(order_id=1009, product_id=5, quantity=2, price_cents=2200),
]

# Pre-seed the refund for order #1008 so "already refunded" case is ready to demo
REFUNDS = [
    Refund(
        order_id=1008,
        amount_cents=4500,
        reason="[Product defect] Wallet stitching was coming apart on arrival",
        status="approved",
        created_at=now - timedelta(days=12),
    ),
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        session.add_all(PRODUCTS)
        await session.flush()
        session.add_all(CUSTOMERS)
        await session.flush()
        session.add_all(ORDERS)
        await session.flush()
        session.add_all(ORDER_ITEMS)
        await session.flush()
        session.add_all(REFUNDS)
        await session.commit()

    print("Seeded: 4 customers, 7 products, 10 orders")
    print()
    print("Order reference:")
    print("  #1001  Alice Chen       delivered  5d    → Tier 1: full refund (product issue)")
    print("  #1042  Bob Martinez     delivered  10d   → Tier 1: full refund (hero demo)")
    print("  #1002  Alice Chen       delivered  45d   → Tier 2: 75% partial (product issue) | Tier 4: no refund (changed mind)")
    print("  #1005  Carol White      delivered  20d   → Tier 3: 50% partial (changed mind within 30d)")
    print("  #1006  Alice Chen       delivered  65d   → Escalate: product issue >60 days old")
    print("  #1007  Diana Park       delivered  8d    → Escalate: order total >$500 ($538)")
    print("  #1008  Bob Martinez     refunded   15d   → Already refunded (wallet defect, pre-seeded)")
    print("  #1003  Bob Martinez     shipped    3d    → Not yet delivered")
    print("  #1004  Carol White      processing 1d    → Cancel-eligible (processing)")
    print("  #1009  Carol White      pending    <1d   → Cancel-eligible (pending)")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
