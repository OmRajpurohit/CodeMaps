from sqlalchemy.ext.asyncio import AsyncEngine

from backend.app.core.logging import logger
from backend.app.db.base import Base


async def init_database(engine: AsyncEngine) -> None:
    """Creates all database tables based on registered SQLAlchemy models."""
    logger.info("Initializing database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized successfully.")
