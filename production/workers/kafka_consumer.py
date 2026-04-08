# production/workers/kafka_consumer.py
from aiokafka import AIOKafkaConsumer
import json
import asyncio
import os
from production.services.agent_service import process_customer_message

async def kafka_consumer():
    consumer = AIOKafkaConsumer(
        "customer-messages",
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        group_id="flowforge-agent-group",
        value_deserializer=lambda v: json.loads(v.decode('utf-8'))
    )
    await consumer.start()

    print("🚀 Kafka consumer started — listening for messages")

    try:
        async for msg in consumer:
            data = msg.value
            print(f"📨 Kafka received: {data['channel']} message")

            # If already processed by webhook, just log
            if data.get("processed"):
                print(f"   → Already processed by webhook: {data.get('response')[:100]}...")
                continue

            # Otherwise process with agent
            await process_customer_message(data)

    finally:
        await consumer.stop()