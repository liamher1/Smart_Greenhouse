import asyncio
from src.base.infrastructure.database import init_db
from loguru import logger

async def start_app():
    logger.info("Starting the greenhouse backend...")

    await init_db()
    logger.success("Backend is running and DB is synced!")

if __name__ == "__main__":
    asyncio.run(start_app())