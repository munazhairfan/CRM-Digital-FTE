import asyncio
import os
from dotenv import load_dotenv
load_dotenv(override=True)

from production.clients.kafka_client import kafka_producer

async def main():
    print("📤 Testing Kafka Producer...")
    try:
        # 1. Create a test message
        test_message = {
            "channel": "whatsapp",
            "content": "Hello Kafka!",
            "customer_name": "TestUser",
            "metadata": {"wa_id": "12345"},
            "test": True
        }
        
        # 2. Send to Kafka
        await kafka_producer.send_message(test_message)
        print("✅ Message sent to Kafka successfully!")
        
    except Exception as e:
        print(f"❌ Failed to send message: {e}")

asyncio.run(main())
