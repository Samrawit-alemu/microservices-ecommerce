# product_service/app/infrastructure/messaging/consumer.py
import os  # Added import
import pika
import json
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.infrastructure.db.config import async_session
from app.infrastructure.db.models import ProductDB

class RabbitMQConsumer:
    def __init__(self):
        # 1. Load CloudAMQP URL from environment variable, fallback to local IPv4
        self.rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@127.0.0.1:5672//")
        self.exchange_name = "order_exchange"
        self.queue_name = "product_inventory_queue"

    def start_consuming(self):
        """
        Connects to RabbitMQ using URL parameters, binds the queue, and starts listening.
        """
        # 2. Use URLParameters instead of ConnectionParameters to support CloudAMQP
        parameters = pika.URLParameters(self.rabbitmq_url)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        channel.exchange_declare(
            exchange=self.exchange_name, 
            exchange_type="direct", 
            durable=True
        )

        channel.queue_declare(queue=self.queue_name, durable=True)

        channel.queue_bind(exchange=self.exchange_name, queue=self.queue_name, routing_key="order.paid")
        channel.queue_bind(exchange=self.exchange_name, queue=self.queue_name, routing_key="order.failed")

        def callback(ch, method, properties, body):
            event_data = json.loads(body)
            routing_key = method.routing_key
            
            asyncio.run(self.process_event(routing_key, event_data))
            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_consume(queue=self.queue_name, on_message_callback=callback)
        channel.start_consuming()

    async def process_event(self, routing_key: str, event_data: dict):
        if routing_key == "order.paid":
            await self.update_inventory(event_data, decrement=True)
        elif routing_key == "order.failed":
            await self.update_inventory(event_data, decrement=False)

    async def update_inventory(self, event_data: dict, decrement: bool):
        async with async_session() as session:
            try:
                for item in event_data.get("items", []):
                    product_id = item["product_id"]
                    quantity = item["quantity"]

                    query = select(ProductDB).where(ProductDB.id == product_id)
                    result = await session.execute(query)
                    product = result.scalar_one_or_none()

                    if product:
                        if decrement:
                            product.stock = max(0, int(product.stock) - quantity)  # type: ignore
                            action = "decremented"
                        else:
                            product.stock = int(product.stock) + quantity  # type: ignore
                            action = "restored"
                
                await session.commit()
                print(f"[x] Inventory {action} successfully for event: {event_data.get('tx_ref')}")
            except Exception as e:
                await session.rollback()
                print(f"[!] Failed to update inventory: {str(e)}")