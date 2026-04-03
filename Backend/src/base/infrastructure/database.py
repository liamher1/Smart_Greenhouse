from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from Backend.config import config

# Import models here so SQLModel knows which tables to create
from Backend.src.features.telemetry.models import TelemetryReading, FailedMessage  # noqa: F401

DATABASE_URL = (
    f"postgresql+asyncpg://{config.DB_USER}:{config.DB_PASSWORD}"
    f"@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
)

# Create the async engine for PostgreSQL connection
# echo=True allows us to see the actual SQL queries in the logs
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Factory for creating new database sessions
async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
    #1
)

async def init_db():
    """Initialize database by creating all defined tables"""
    async with engine.begin() as conn:
        # This command actually creates the tables in the Docker container
        await conn.run_sync(SQLModel.metadata.create_all)