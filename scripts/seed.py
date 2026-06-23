"""
Seed the database with realistic NorthShop demo data.
Usage: cd backend && python ../scripts/seed.py
"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.customer import Customer
from app.models.order import Order, OrderItem, Product
from app.models.refund import Refund  # noqa: F401 — required so SQLAlchemy resolves Order.refund
from app.database import Base

DATABASE_URL = "postgresql+asyncpg://northshop:northshop@localhost:5432/northshop"

engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(engine)

PRODUCTS = [
    Product(id=1, name="Merino Wool Sweater", price_cents=8900, category="Clothing"),
    Product(id=2, name="Leather Wallet", price_cents=4500, category="Accessories"),
    Product(id=3, name="Running Shoes", price_cents=12000, category="Footwear"),
    Product(id=4, name="Denim Jacket", price_cents=9500, category="Clothing"),
    Product(id=5, name="Ceramic Coffee Mug", price_cents=2200, category="Homewares"),
]

CUSTOMERS = [
    Customer(id=1, name="Alice Chen", email="x"),
    Customer(id=2, name="Bob Martinez", email="bob@example.com"),
    Customer(id=3, name="Carol White", email="carol@example.com"),
]

now = datetime.utcnow()

ORDERS = [
    # Delivered and refund-eligible (within 30 days)
    Order(id=1001, customer_id=1, status="delivered", total_cents=8900, created_at=now - timedelta(days=5)),
    # Delivered but older than 30 days (not eligible)
    Order(id=1002, customer_id=1, status="delivered", total_cents=13500, created_at=now - timedelta(days=45)),
    # In transit
    Order(id=1003, customer_id=2, status="shipped", total_cents=12000, created_at=now - timedelta(days=3)),
    # Recently placed
    Order(id=1004, customer_id=3, status="processing", total_cents=4500, created_at=now - timedelta(days=1)),
    # Delivered, eligible (hero demo order)
    Order(id=1042, customer_id=2, status="delivered", total_cents=17900, created_at=now - timedelta(days=10)),
]

ORDER_ITEMS = [
    OrderItem(order_id=1001, product_id=1, quantity=1, price_cents=8900),
    OrderItem(order_id=1002, product_id=3, quantity=1, price_cents=12000),
    OrderItem(order_id=1002, product_id=2, quantity=1, price_cents=4500),  # total 13500 but we store flat
    OrderItem(order_id=1003, product_id=3, quantity=1, price_cents=12000),
    OrderItem(order_id=1004, product_id=2, quantity=1, price_cents=4500),
    OrderItem(order_id=1042, product_id=1, quantity=1, price_cents=8900),  # hero order
    OrderItem(order_id=1042, product_id=3, quantity=1, price_cents=9000),
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
        await session.commit()

    print("Seeded: 3 customers, 5 products, 5 orders")
    print("Hero demo order: #1042 (Bob Martinez, delivered, eligible for refund)")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
