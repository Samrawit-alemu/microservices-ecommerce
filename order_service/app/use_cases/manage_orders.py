# order_service/app/use_cases/manage_orders.py
import uuid
from typing import List
from decimal import Decimal

from app.domain.models import OrderCreate
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
        self.order_repo = order_repo
        self.product_client = product_client
        self.chapa_client = chapa_client
        self.publisher = publisher

    async def create_order(self, order_data: OrderCreate, user_id: int, email: str, callback_url: str) -> dict:
        """
        Validates stock, creates an order linked to a User ID, and initializes a payment link.
        """
        total_amount = Decimal("0.00")
        tx_ref = f"chapa-tx-{uuid.uuid4().hex[:8]}"
        prepared_items = []

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

        # Save order to DB with 'PENDING' status linked to the logged-in User ID
        db_order = await self.order_repo.create_order(
            user_id=user_id,
            total_amount=total_amount,
            tx_ref=tx_ref,
            items_data=prepared_items
        )

        # Initialize payment link using the user's secure database email
        payment_url = await self.chapa_client.initialize_payment(
            amount=Decimal(db_order.total_amount), # type: ignore
            email=email,
            tx_ref=str(db_order.tx_ref),
            callback_url=callback_url
        )

        return {
            "order": db_order,
            "payment_url": payment_url
        }

    async def confirm_payment(self, tx_ref: str) -> OrderDB:
        order = await self.order_repo.get_by_tx_ref(tx_ref)
        if not order:
            raise ValueError(f"Order with reference {tx_ref} not found")

        # Idempotent webhook: already-PAID orders must not republish order.paid
        # (replaying the same tx_ref would otherwise double-decrement stock).
        if str(order.status) == "PAID":
            print(f"[.] Payment already confirmed for tx: {tx_ref}; skipping republish")
            return order

        updated_order = await self.order_repo.update_status(int(order.id), "PAID") # type: ignore

        event_payload = {
            "order_id": int(updated_order.id), # type: ignore
            "tx_ref": str(updated_order.tx_ref),
            "items": [
                {"product_id": int(item.product_id), "quantity": int(item.quantity)} # type: ignore
                for item in updated_order.items
            ]
        }

        self.publisher.publish_event(routing_key="order.paid", message=event_payload)
        print(f"[x] Published order.paid event to RabbitMQ for tx: {tx_ref}")

        return updated_order

    async def get_order(self, order_id: int) -> OrderDB:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order with ID {order_id} not found")
        return order

    async def list_orders_for_user(self, user_id: int) -> List[OrderDB]:
        """Return order history scoped to the authenticated user."""
        return await self.order_repo.get_by_user_id(user_id)