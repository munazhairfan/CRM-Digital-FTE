import asyncio
import os
from aiokafka import AIOKafkaConsumer

async def main():
    print("👂 Listening for 5 seconds...")
    
    consumer = AIOKafkaConsumer(
        "customer-messages",
        bootstrap_servers="localhost:9092",
        group_id="test-listener",
        auto_offset_reset="earliest"
    )
    await consumer.start()
    
    try:
        async for msg in consumer:
            print(f"✅ RECEIVED: {msg.value}")
            break
    finally:
        await consumer.stop()

asyncio.run(main())
