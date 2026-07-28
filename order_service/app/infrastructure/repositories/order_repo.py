# order_service/app/infrastructure/repositories/order_repo.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.infrastructure.db.models import OrderDB, OrderItemDB
from typing import List, Optional
from decimal import Decimal

class OrderRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_order(
        self, 
        user_id: int,  # Changed from customer_email to user_id
        total_amount: Decimal, 
        tx_ref: str, 
        items_data: List[dict]
    ) -> OrderDB:
        """
        Saves an order linked securely to a User ID.
        """
        db_order = OrderDB(
            user_id=user_id, # Link directly to the User ID
            total_amount=total_amount,
            tx_ref=tx_ref,
            status="PENDING"
        )

        for item in items_data:
            db_item = OrderItemDB(
                product_id=item["product_id"],
                quantity=item["quantity"],
                unit_price=item["unit_price"]
            )
            db_order.items.append(db_item)

        self.db_session.add(db_order)
        await self.db_session.flush()
        return db_order

    async def get_by_id(self, order_id: int) -> Optional[OrderDB]:
        query = (
            select(OrderDB)
            .options(selectinload(OrderDB.items))
            .where(OrderDB.id == order_id)
        )
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_tx_ref(self, tx_ref: str) -> Optional[OrderDB]:
        query = select(OrderDB).options(selectinload(OrderDB.items)).where(OrderDB.tx_ref == tx_ref)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: int) -> List[OrderDB]:
        """Return the authenticated user's orders, newest first."""
        query = (
            select(OrderDB)
            .options(selectinload(OrderDB.items))
            .where(OrderDB.user_id == user_id)
            .order_by(OrderDB.created_at.desc())
        )
        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def update_status(self, order_id: int, status: str) -> OrderDB:
        query = select(OrderDB).where(OrderDB.id == order_id)
        result = await self.db_session.execute(query)
        db_order = result.scalar_one()
        db_order.status = status  # type: ignore
        await self.db_session.flush()
        return db_order