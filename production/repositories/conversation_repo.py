"""
production/repositories/conversation_repo.py
Manages conversation lifecycle across all channels.
Conversations are unified per customer regardless of channel.
"""

import uuid
from typing import Optional
from production.clients.db_client import DatabaseClient


class ConversationRepository:
    async def get_or_create_conversation(
        self,
        customer_id: str,
        initial_channel: str,
    ) -> str:
        """
        Return the active conversation_id for this customer.
        If no active conversation exists within 7 days, create a new one.
        """
        async with DatabaseClient.get_connection() as conn:
            # Look for active conversation within last 7 days
            row = await conn.fetchrow(
                """
                SELECT id FROM conversations
                WHERE customer_id = $1
                  AND status = 'active'
                  AND started_at > NOW() - INTERVAL '7 days'
                ORDER BY started_at DESC
                LIMIT 1
                """,
                uuid.UUID(customer_id),
            )

            if row:
                return str(row["id"])

            # Create new conversation
            conversation_id = uuid.uuid4()
            await conn.execute(
                """
                INSERT INTO conversations
                    (id, customer_id, initial_channel, status, started_at)
                VALUES
                    ($1, $2, $3, 'active', NOW())
                """,
                conversation_id,
                uuid.UUID(customer_id),
                initial_channel,
            )

            return str(conversation_id)

    async def update_status(
        self,
        conversation_id: str,
        status: str,
        sentiment_score: Optional[float] = None,
        resolution_type: Optional[str] = None,
    ) -> None:
        """Update conversation status and optional sentiment/resolution."""
        # Fix: Truncate resolution_type to fit DB schema (VARCHAR 50)
        if resolution_type and len(resolution_type) > 45:
            resolution_type = resolution_type[:45] + "..."
            
        async with DatabaseClient.get_connection() as conn:
            await conn.execute(
                """
                UPDATE conversations
                SET status           = $1::text,
                    sentiment_score  = COALESCE($2, sentiment_score),
                    resolution_type  = COALESCE($3::text, resolution_type),
                    ended_at         = CASE WHEN $1::text IN ('resolved','escalated')
                                            THEN NOW() ELSE ended_at END
                WHERE id = $4
                """,
                str(status),
                sentiment_score,
                resolution_type,
                uuid.UUID(conversation_id),
            )
