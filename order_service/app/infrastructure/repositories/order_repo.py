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
        customer_email: str, 
        total_amount: Decimal, 
        tx_ref: str, 
        items_data: List[dict]
    ) -> OrderDB:
        """
        Saves an order and all of its items inside a single database transaction.
        """
        # 1. Create and add the parent Order row
        db_order = OrderDB(
            customer_email=customer_email,
            total_amount=total_amount,
            tx_ref=tx_ref,
            status="PENDING"
        )
        self.db_session.add(db_order)
        # Flush pushes the order to PostgreSQL to generate db_order.id
        await self.db_session.flush()

        # 2. Iterate through items, attach the order ID, and save them
        for item in items_data:
            db_item = OrderItemDB(
                order_id=db_order.id,
                product_id=item["product_id"],
                quantity=item["quantity"],
                unit_price=item["unit_price"]
            )
            self.db_session.add(db_item)

        await self.db_session.flush()
        return db_order

    async def get_by_id(self, order_id: int) -> Optional[OrderDB]:
        """
        Queries an order and automatically pre-loads its child order items.
        """
        query = (
            select(OrderDB)
            .options(selectinload(OrderDB.items))  # Preloads the related items
            .where(OrderDB.id == order_id)
        )
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()