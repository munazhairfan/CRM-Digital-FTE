"""
FlowForge FTE — Reporting Service
Generates daily sentiment reports and agent performance metrics from the database.
"""
import os
import datetime
from production.clients.db_client import DatabaseClient


class ReportingService:
    def __init__(self):
        pass

    async def get_sentiment_report(self, channel: str = None, days: int = 1) -> dict:
        """
        Generate a sentiment report for the last N days (default 24h).
        Queries real data from messages, conversations, and customers tables.
        """
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        
        async with DatabaseClient.get_connection() as conn:
            # 1. Overall Daily Sentiment & Breakdown
            if channel:
                stats_row = await conn.fetchrow(
                    """
                    SELECT 
                        AVG(c.sentiment_score) as avg_sentiment,
                        COUNT(c.id) as total_interactions,
                        COUNT(CASE WHEN c.sentiment_score > 0.6 THEN 1 END) as positive_count,
                        COUNT(CASE WHEN c.sentiment_score >= 0.4 AND c.sentiment_score <= 0.6 THEN 1 END) as neutral_count,
                        COUNT(CASE WHEN c.sentiment_score < 0.4 THEN 1 END) as negative_count
                    FROM conversations c
                    WHERE c.started_at > $1 AND c.initial_channel = $2
                    """,
                    cutoff, channel
                )
            else:
                stats_row = await conn.fetchrow(
                    """
                    SELECT 
                        AVG(c.sentiment_score) as avg_sentiment,
                        COUNT(c.id) as total_interactions,
                        COUNT(CASE WHEN c.sentiment_score > 0.6 THEN 1 END) as positive_count,
                        COUNT(CASE WHEN c.sentiment_score >= 0.4 AND c.sentiment_score <= 0.6 THEN 1 END) as neutral_count,
                        COUNT(CASE WHEN c.sentiment_score < 0.4 THEN 1 END) as negative_count
                    FROM conversations c
                    WHERE c.started_at > $1
                    """,
                    cutoff
                )

            # 2. By Channel
            by_channel = []
            channel_rows = await conn.fetch(
                """
                SELECT 
                    c.initial_channel as channel,
                    COUNT(c.id) as count,
                    ROUND(AVG(c.sentiment_score), 2) as avg_sentiment
                FROM conversations c
                WHERE c.started_at > $1
                GROUP BY c.initial_channel
                ORDER BY c.initial_channel
                """,
                cutoff
            )
            for r in channel_rows:
                by_channel.append({
                    "channel": r["channel"],
                    "count": r["count"],
                    "avg_sentiment": float(r["avg_sentiment"])
                })

            # 3. At-Risk Customers (last 2 conversations <= 0.3)
            at_risk = []
            at_risk_rows = await conn.fetch(
                """
                WITH RankedConversations AS (
                    SELECT 
                        c.customer_id,
                        c.sentiment_score,
                        c.initial_channel,
                        c.started_at,
                        ROW_NUMBER() OVER(PARTITION BY c.customer_id ORDER BY c.started_at DESC) as rn
                    FROM conversations c
                    WHERE c.started_at > $1
                )
                SELECT 
                    cust.name, cust.email, cust.phone,
                    rc1.initial_channel as channel,
                    rc1.sentiment_score as latest_sentiment,
                    rc2.sentiment_score as previous_sentiment
                FROM RankedConversations rc1
                JOIN RankedConversations rc2 
                    ON rc1.customer_id = rc2.customer_id 
                    AND rc1.rn = 1 AND rc2.rn = 2
                JOIN customers cust ON cust.id = rc1.customer_id
                WHERE rc1.sentiment_score <= 0.3 AND rc2.sentiment_score <= 0.3
                ORDER BY rc1.sentiment_score ASC
                LIMIT 10
                """,
                cutoff
            )
            for r in at_risk_rows:
                at_risk.append({
                    "name": r["name"],
                    "email": r["email"],
                    "phone": r["phone"],
                    "channel": r["channel"],
                    "latest_sentiment": float(r["latest_sentiment"]),
                    "previous_sentiment": float(r["previous_sentiment"])
                })

        return {
            "period_hours": days * 24,
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "summary": {
                "daily_average_sentiment": round(float(stats_row["avg_sentiment"]), 2) if stats_row["avg_sentiment"] else 0.0,
                "total_interactions": stats_row["total_interactions"],
                "breakdown": {
                    "positive": stats_row["positive_count"],
                    "neutral": stats_row["neutral_count"],
                    "negative": stats_row["negative_count"],
                }
            },
            "by_channel": by_channel,
            "at_risk_customers": at_risk
        }
