# product_service/app/infrastructure/messaging/consumer.py
import pika
import json
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.infrastructure.db.config import async_session
from app.infrastructure.db.models import ProductDB

class RabbitMQConsumer:
    def __init__(self, host: str = "localhost", port: int = 5672):
        self.host = host
        self.port = port
        self.exchange_name = "order_exchange"
        self.queue_name = "product_inventory_queue"

    def start_consuming(self):
        """
        Connects to RabbitMQ, binds the queue, and starts listening for events.
        """
        # 1. Establish connection and channel
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=self.host, port=self.port)
        )
        channel = connection.channel()

        # 2. Declare the exchange (must match the publisher exactly)
        channel.exchange_declare(
            exchange=self.exchange_name, 
            exchange_type="direct", 
            durable=True
        )

        # 3. Declare our specific queue
        channel.queue_declare(queue=self.queue_name, durable=True)

        # 4. Bind the queue to the exchange for 'order.paid' events
        channel.queue_bind(
            exchange=self.exchange_name, 
            queue=self.queue_name, 
            routing_key="order.paid"
        )

        # 5. Define what to do when a message arrives
        def callback(ch, method, properties, body):
            event_data = json.loads(body)
            # Use asyncio to run our asynchronous database update in the main event loop
            asyncio.run(self.update_inventory(event_data))
            # Send acknowledgement back to RabbitMQ that the message was processed safely
            ch.basic_ack(delivery_tag=method.delivery_tag)

        # 6. Start the infinite consumer loop
        channel.basic_consume(queue=self.queue_name, on_message_callback=callback)
        channel.start_consuming()

    async def update_inventory(self, event_data: dict):
        """
        Asynchronously decrements product stock in PostgreSQL.
        """
        async with async_session() as session:
            try:
                for item in event_data.get("items", []):
                    product_id = item["product_id"]
                    quantity = item["quantity"]

                    # Query the product
                    query = select(ProductDB).where(ProductDB.id == product_id)
                    result = await session.execute(query)
                    product = result.scalar_one_or_none()

                    if product:
                        # Decrement stock (ensuring it doesn't go below 0)
                        product.stock = max(0, product.stock - quantity)
                
                await session.commit()
                print(f"[x] Inventory updated successfully for event: {event_data.get('tx_ref')}")
            except Exception as e:
                await session.rollback()
                print(f"[!] Failed to update inventory: {str(e)}")