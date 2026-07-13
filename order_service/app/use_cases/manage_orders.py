# order_service/app/use_cases/manage_orders.py
import uuid
from typing import List
from decimal import Decimal

from app.domain.models import OrderCreate
from app.infrastructure.repositories.order_repo import OrderRepository
from app.infrastructure.external_services.product_client import ProductClient
from app.infrastructure.db.models import OrderDB

class OrderUseCases:
    def __init__(self, order_repo: OrderRepository, product_client: ProductClient):
        """
        We inject both our internal Database Repository 
        and our external HTTP Product Client.
        """
        self.order_repo = order_repo
        self.product_client = product_client

    async def create_order(self, order_data: OrderCreate) -> OrderDB:
        """
        Orchestrates order validation, pricing calculation, 
        and database storage.
        """
        total_amount = Decimal("0.00")
        
        # Generate a unique reference prefix for Chapa payment gateways
        tx_ref = f"chapa-tx-{uuid.uuid4().hex[:8]}"
        prepared_items = []

        # Validate and price each requested item
        for item in order_data.items:
            # 1. Fetch live product data from Product Service
            product = await self.product_client.get_product_details(item.product_id)
            if not product:
                raise ValueError(f"Product with ID {item.product_id} does not exist")

            # 2. Enforce inventory boundaries
            if product.stock < item.quantity:
                raise ValueError(
                    f"Insufficient stock for '{product.name}'. "
                    f"Requested: {item.quantity}, Available: {product.stock}"
                )

            # 3. Calculate financial totals securely using backend database prices
            item_total = product.price * item.quantity
            total_amount += item_total

            # Prepare data dictionary for repository inserts
            prepared_items.append({
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": product.price
            })

        # 4. Save the finalized order to our database
        return await self.order_repo.create_order(
            customer_email=order_data.customer_email,
            total_amount=total_amount,
            tx_ref=tx_ref,
            items_data=prepared_items
        )

    async def get_order(self, order_id: int) -> OrderDB:
        """
        Fetches an order from the database by ID.
        """
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order with ID {order_id} not found")
        return order