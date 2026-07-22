# order_service/app/infrastructure/messaging/publisher.py
import os

import pika
import json

class RabbitMQPublisher:
    def __init__(self):
        self.rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@127.0.0.1:5672//")
        self.exchange_name = "order_exchange"

    def publish_event(self, routing_key: str, message: dict):
        parameters = pika.URLParameters(self.rabbitmq_url)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()