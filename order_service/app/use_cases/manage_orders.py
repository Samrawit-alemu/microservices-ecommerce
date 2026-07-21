# order_service/app/use_cases/manage_orders.py
import uuid
from typing import List
from decimal import Decimal

from app.domain.models import OrderCreate, Order as OrderDomain
from app.infrastructure.repositories.order_repo import OrderRepository
from app.infrastructure.external_services.product_client import ProductClient
from app.infrastructure.external_services.chapa_client import ChapaClient
from app.infrastructure.messaging.publisher import RabbitMQPublisher
from app.infrastructure.db.models import OrderDB

class OrderUseCases:
    def __init__(
        self, 
        order_repo: OrderRepository, 
        product_client: ProductClient,
        chapa_client: ChapaClient,
        publisher: RabbitMQPublisher
    ):
        """
        Inject internal db repository and external messaging & api clients.
        """
        self.order_repo = order_repo
        self.product_client = product_client
        self.chapa_client = chapa_client
        self.publisher = publisher

    async def create_order(self, order_data: OrderCreate, callback_url: str) -> dict:
        """
        Validates stock, creates a pending order, and initializes a Chapa payment link.
        """
        total_amount = Decimal("0.00")
        tx_ref = f"chapa-tx-{uuid.uuid4().hex[:8]}"
        prepared_items = []

        # Validate stock and calculate secure prices
        for item in order_data.items:
            product = await self.product_client.get_product_details(item.product_id)
            if not product:
                raise ValueError(f"Product with ID {item.product_id} does not exist")

            if product.stock < item.quantity:
                raise ValueError(
                    f"Insufficient stock for '{product.name}'. "
                    f"Requested: {item.quantity}, Available: {product.stock}"
                )

            item_total = product.price * item.quantity
            total_amount += item_total

            prepared_items.append({
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": product.price
            })

        # Save order to DB with 'PENDING' status
        db_order = await self.order_repo.create_order(
            customer_email=order_data.customer_email,
            total_amount=total_amount,
            tx_ref=tx_ref,
            items_data=prepared_items
        )

        # Initialize payment link from Chapa
        payment_url = await self.chapa_client.initialize_payment(
            amount=db_order.total_amount,
            email=db_order.customer_email,
            tx_ref=db_order.tx_ref,
            callback_url=callback_url
        )

        return {
            "order": db_order,
            "payment_url": payment_url
        }

    async def confirm_payment(self, tx_ref: str) -> OrderDB:
        """
        Saves order payment status and publishes an event to RabbitMQ.
        """
        order = await self.order_repo.get_by_tx_ref(tx_ref)
        if not order:
            raise ValueError(f"Order with reference {tx_ref} not found")

        # Update order status to PAID
        updated_order = await self.order_repo.update_status(order.id, "PAID")

        # Map our order items data into a clean JSON event payload
        event_payload = {
            "order_id": updated_order.id,
            "tx_ref": updated_order.tx_ref,
            "items": [
                {"product_id": item.product_id, "quantity": item.quantity}
                for item in updated_order.items
            ]
        }

        # Publish the "order.paid" event to RabbitMQ
        self.publisher.publish_event(routing_key="order.paid", message=event_payload)
        print(f"[x] Published order.paid event to RabbitMQ for tx: {tx_ref}")

        return updated_order

    async def get_order(self, order_id: int) -> OrderDB:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order with ID {order_id} not found")
        return order