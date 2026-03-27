#!/usr/bin/env python3
"""
Database Migration Script
Runs database migrations to create/update tables
"""
import asyncio
from app.utils.database import init_db
from app.utils.logger import logger

async def run_migration():
    """Run database migration"""
    try:
        logger.info("Starting database migration...")
        await init_db()
        logger.info("Database migration completed successfully!")
        logger.info("RateLimitEntry table created with timestamp index")
        return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_migration())
    exit(0 if success else 1)
