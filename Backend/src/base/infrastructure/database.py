import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from dotenv import load_dotenv

# Import models here so SQLModel knows which tables to create
from Backend.src.features.telemetry.models import TelemetryReading

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Create the async engine for PostgreSQL connection
# echo=True allows us to see the actual SQL queries in the logs
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Factory for creating new database sessions
async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    """Initialize database by creating all defined tables"""
    async with engine.begin() as conn:
        # This command actually creates the tables in the Docker container
        await conn.run_sync(SQLModel.metadata.create_all)