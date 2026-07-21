# order_service/app/infrastructure/messaging/publisher.py
import pika
import json

class RabbitMQPublisher:
    def __init__(self, host: str = "127.0.0.1", port: int = 5672):
        self.host = host
        self.port = port
        self.exchange_name = "order_exchange"

    def publish_event(self, routing_key: str, message: dict):
        """
        Connects to RabbitMQ, declares an exchange, and publishes a JSON message.
        """
        # 1. Establish connection to RabbitMQ
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=self.host, port=self.port)
        )
        channel = connection.channel()

        # 2. Declare a 'direct' exchange
        channel.exchange_declare(
            exchange=self.exchange_name, 
            exchange_type="direct", 
            durable=True
        )

        # 3. Publish the message serialized as JSON
        channel.basic_publish(
            exchange=self.exchange_name,
            routing_key=routing_key,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2  # Make the message persistent on disk
            )
        )

        # 4. Close connection
        connection.close()