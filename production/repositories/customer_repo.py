import json
from uuid import UUID
from typing import Optional
import asyncpg
from production.clients.db_client import DatabaseClient
from production.models.schemas import CustomerBase

class CustomerRepository:
    async def get_or_create(self, customer_data: CustomerBase) -> dict:
        async with DatabaseClient.get_connection() as conn:
            # Try to find by email or phone first
            row = await conn.fetchrow(
                """
                SELECT id, email, phone, name
                FROM customers
                WHERE email = $1 OR phone = $2
                """,
                customer_data.email,
                customer_data.phone,
            )

            if row:
                return dict(row)

            # Create new customer
            # Fix: Explicitly serialize metadata to JSON string
            meta_json = json.dumps(customer_data.metadata or {})
            
            new_customer = await conn.fetchrow(
                """
                INSERT INTO customers (email, phone, name, metadata)
                VALUES ($1, $2, $3, $4::jsonb)
                RETURNING id, email, phone, name
                """,
                customer_data.email,
                customer_data.phone,
                customer_data.name,
                meta_json,
            )
            return dict(new_customer)