import asyncio
import os
from dotenv import load_dotenv
load_dotenv(override=True)

from production.workers.kafka_consumer import kafka_consumer

async def main():
    print("🧪 Starting Kafka Consumer Test (will timeout in 10s)...")
    try:
        # kafka_consumer() runs an infinite loop. 
        # If it connects successfully, it will wait for messages until timeout.
        await asyncio.wait_for(kafka_consumer(), timeout=10.0)
    except asyncio.TimeoutError:
        print("\n✅ SUCCESS: Consumer connected and listening for messages.")
    except ConnectionRefusedError:
        print("\n❌ FAILED: Could not connect to Kafka. Is Kafka running on localhost:9092?")
    except Exception as e:
        print(f"\n❌ FAILED: Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
