"""
MongoDB async client using Motor.
Replaces SQLite/SQLAlchemy for persistent cloud-ready storage.
VPS destroy වුනාත් MongoDB Atlas ලෙ data safe.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from typing import Optional
from app.utils.logger import logger
from config.settings import settings

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def connect_mongodb() -> AsyncIOMotorDatabase:
    """Connect to MongoDB and return database instance"""
    global _client, _db

    if _db is not None:
        return _db

    try:
        _client = AsyncIOMotorClient(
            settings.mongodb_url,
            serverSelectionTimeoutMS=5000,
        )
        # Test connection
        await _client.admin.command("ping")
        _db = _client[settings.mongodb_db_name]

        # Create indexes
        await _setup_indexes(_db)

        logger.info(f"✅ Connected to MongoDB: {settings.mongodb_db_name}")
        return _db

    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        raise


async def disconnect_mongodb():
    """Disconnect from MongoDB"""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB disconnected")


async def get_db() -> AsyncIOMotorDatabase:
    """Get the MongoDB database instance (connect if needed)"""
    global _db
    if _db is None:
        return await connect_mongodb()
    return _db


async def _setup_indexes(db: AsyncIOMotorDatabase):
    """Create MongoDB indexes for performance"""
    try:
        # clone_jobs indexes
        await db.clone_jobs.create_index([("job_id", ASCENDING)], unique=True)
        await db.clone_jobs.create_index([("status", ASCENDING)])
        await db.clone_jobs.create_index([("created_at", DESCENDING)])

        # channels indexes
        await db.channels.create_index([("channel_id", ASCENDING)], unique=True)
        await db.channels.create_index([("title", ASCENDING)])

        # sync_state indexes
        await db.sync_state.create_index([("job_id", ASCENDING)], unique=True)

        # job_checkpoints indexes (new - for resume feature)
        await db.job_checkpoints.create_index([("job_id", ASCENDING)], unique=True)
        await db.job_checkpoints.create_index([("updated_at", DESCENDING)])

        logger.info("MongoDB indexes created successfully")
    except Exception as e:
        logger.warning(f"Index creation warning: {e}")
