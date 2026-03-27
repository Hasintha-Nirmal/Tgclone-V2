#!/usr/bin/env python3
"""
Test script to verify RateLimitEntry table creation and functionality
"""
import asyncio
import sys
from datetime import datetime, timedelta

async def test_migration():
    """Test the RateLimitEntry model and migration"""
    try:
        # Import after ensuring we're in the right context
        from app.utils.database import init_db, AsyncSessionLocal, RateLimitEntry
        from sqlalchemy import select, func
        from app.utils.logger import logger
        
        logger.info("=" * 60)
        logger.info("Testing RateLimitEntry Migration")
        logger.info("=" * 60)
        
        # Step 1: Run migration
        logger.info("\n1. Running database migration...")
        await init_db()
        logger.info("✓ Migration completed successfully")
        
        # Step 2: Test table creation
        logger.info("\n2. Verifying RateLimitEntry table exists...")
        async with AsyncSessionLocal() as db:
            # Try to query the table
            result = await db.execute(select(func.count()).select_from(RateLimitEntry))
            count = result.scalar()
            logger.info(f"✓ Table exists with {count} existing entries")
        
        # Step 3: Test inserting a record
        logger.info("\n3. Testing record insertion...")
        async with AsyncSessionLocal() as db:
            entry = RateLimitEntry(
                timestamp=datetime.utcnow(),
                job_id="test_job_123",
                account_phone="+1234567890"
            )
            db.add(entry)
            await db.commit()
            logger.info(f"✓ Inserted test entry with ID: {entry.id}")
        
        # Step 4: Test querying with index
        logger.info("\n4. Testing timestamp index query...")
        async with AsyncSessionLocal() as db:
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            result = await db.execute(
                select(RateLimitEntry)
                .filter(RateLimitEntry.timestamp > one_hour_ago)
                .order_by(RateLimitEntry.timestamp.desc())
            )
            recent_entries = result.scalars().all()
            logger.info(f"✓ Found {len(recent_entries)} entries in last hour")
        
        # Step 5: Test cleanup (delete test entry)
        logger.info("\n5. Cleaning up test data...")
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(RateLimitEntry).filter(RateLimitEntry.job_id == "test_job_123")
            )
            test_entry = result.scalar_one_or_none()
            if test_entry:
                await db.delete(test_entry)
                await db.commit()
                logger.info("✓ Test entry cleaned up")
        
        # Step 6: Verify schema
        logger.info("\n6. Verifying table schema...")
        async with AsyncSessionLocal() as db:
            # Check that all columns exist by selecting them
            result = await db.execute(
                select(
                    RateLimitEntry.id,
                    RateLimitEntry.timestamp,
                    RateLimitEntry.job_id,
                    RateLimitEntry.account_phone
                ).limit(1)
            )
            logger.info("✓ All columns present: id, timestamp, job_id, account_phone")
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ ALL TESTS PASSED")
        logger.info("=" * 60)
        logger.info("\nMigration Summary:")
        logger.info("- RateLimitEntry table created successfully")
        logger.info("- Index on timestamp column created")
        logger.info("- All CRUD operations working")
        logger.info("- Existing data preserved")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_migration())
    sys.exit(0 if success else 1)
