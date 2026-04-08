# production/repositories/ticket_repo.py
from uuid import UUID
import asyncpg
from production.clients.db_client import DatabaseClient
from production.models.schemas import TicketCreate

class TicketRepository:
    async def create(self, ticket: TicketCreate) -> dict:
        async with DatabaseClient.get_connection() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO tickets (
                    conversation_id, customer_id, source_channel, 
                    category, priority, status
                )
                VALUES ($1, $2, $3, $4, $5, 'open')
                RETURNING id, ticket_number, status, created_at
                """,
                ticket.conversation_id,
                ticket.customer_id,
                ticket.source_channel,
                ticket.category,
                ticket.priority,
            )
            return dict(row)

    async def mark_escalated(self, ticket_id: UUID, reason: str) -> None:
        async with DatabaseClient.get_connection() as conn:
            await conn.execute(
                """
                UPDATE tickets 
                SET status = 'escalated', escalated_reason = $2
                WHERE id = $1
                """,
                ticket_id,
                reason,
            )