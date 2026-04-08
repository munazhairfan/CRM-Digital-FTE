# production/clients/kafka_client.py
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import json
import os
import asyncio

class KafkaProducer:
    _producer = None

    @classmethod
    async def get_producer(cls):
        if cls._producer is None:
            cls._producer = AIOKafkaProducer(
                bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            await cls._producer.start()
        return cls._producer

    @classmethod
    async def send_message(cls, message: dict):
        producer = await cls.get_producer()
        await producer.send_and_wait("customer-messages", message)

# Global instance
kafka_producer = KafkaProducer()