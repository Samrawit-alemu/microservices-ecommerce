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
        Saves an order and all its items safely, keeping relationships loaded in-memory.
        """
        # 1. Create the parent Order object (without adding to session yet)
        db_order = OrderDB(
            customer_email=customer_email,
            total_amount=total_amount,
            tx_ref=tx_ref,
            status="PENDING"
        )

        # 2. Append children directly to the parent's 'items' relationship in-memory
        for item in items_data:
            db_item = OrderItemDB(
                product_id=item["product_id"],
                quantity=item["quantity"],
                unit_price=item["unit_price"]
                # Notice: We DO NOT set 'order_id' manually. 
                # SQLAlchemy handles this when we append to db_order.items!
            )
            db_order.items.append(db_item)

        # 3. Adding the parent automatically adds all appended children in one batch
        self.db_session.add(db_order)
        
        # 4. Flush once to save everything and generate the IDs
        await self.db_session.flush()
        
        return db_order

    async def get_by_id(self, order_id: int) -> Optional[OrderDB]:
        """
        Queries an order and pre-loads its child items.
        """
        query = (
            select(OrderDB)
            .options(selectinload(OrderDB.items))
            .where(OrderDB.id == order_id)
        )
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_tx_ref(self, tx_ref: str) -> Optional[OrderDB]:
        """
        Queries an order using its unique Chapa transaction reference.
        """
        query = select(OrderDB).options(selectinload(OrderDB.items)).where(OrderDB.tx_ref == tx_ref)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()

    async def update_status(self, order_id: int, status: str) -> OrderDB:
        """
        Updates the status of an order (e.g., 'PENDING' -> 'PAID').
        """
        query = select(OrderDB).where(OrderDB.id == order_id)
        result = await self.db_session.execute(query)
        db_order = result.scalar_one()
        db_order.status = status
        await self.db_session.flush()
        return db_order