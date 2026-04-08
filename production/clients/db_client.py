# production/clients/db_client.py
import asyncpg
from contextlib import asynccontextmanager
from typing import AsyncIterator

class DatabaseClient:
    _pool: asyncpg.Pool | None = None

    @classmethod
    async def initialize(cls, dsn: str) -> None:
        """Create connection pool (call once at app startup)."""
        cls._pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=5,
            max_size=20,
            statement_cache_size=0,
        )
        print("✅ PostgreSQL connection pool initialized")

    @classmethod
    async def close(cls) -> None:
        """Close pool on shutdown."""
        if cls._pool:
            await cls._pool.close()

    @classmethod
    @asynccontextmanager
    async def get_connection(cls) -> AsyncIterator[asyncpg.Connection]:
        """Get a connection from the pool (use in services/repositories)."""
        if not cls._pool:
            raise RuntimeError("DatabaseClient not initialized")
        async with cls._pool.acquire() as conn:
            yield conn