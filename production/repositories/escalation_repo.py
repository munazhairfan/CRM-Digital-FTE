# production/repositories/escalation_repo.py
from uuid import UUID
import asyncpg
from production.clients.db_client import DatabaseClient

class EscalationRepository:
    async def create(self, ticket_id: UUID, reason: str, urgency: str, notes: str = None) -> dict:
        async with DatabaseClient.get_connection() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO escalated_tickets (ticket_id, reason, urgency, notes)
                VALUES ($1, $2, $3, $4)
                RETURNING id, escalated_at, status
                """,
                ticket_id,
                reason,
                urgency,
                notes,
            )
            return dict(row)