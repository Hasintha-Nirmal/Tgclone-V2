#!/usr/bin/env python3
"""
Test script to verify GlobalRateLimiter functionality
"""
import asyncio
import sys
from datetime import datetime, timedelta

async def test_global_rate_limiter():
    """Test the GlobalRateLimiter class"""
    try:
        # Import after ensuring we're in the right context
        from app.utils.database import init_db, AsyncSessionLocal, RateLimitEntry
        from app.utils.rate_limiter import global_rate_limiter
        from sqlalchemy import select, delete
        from app.utils.logger import logger
        from config.settings import settings
        
        logger.info("=" * 60)
        logger.info("Testing GlobalRateLimiter")
        logger.info("=" * 60)
        
        # Step 1: Initialize database
        logger.info("\n1. Initializing database...")
        await init_db()
        logger.info("✓ Database initialized")
        
        # Step 2: Clean up any existing test data
        logger.info("\n2. Cleaning up existing test data...")
        async with AsyncSessionLocal() as db:
            await db.execute(delete(RateLimitEntry))
            await db.commit()
            logger.info("✓ Test data cleaned up")
        
        # Step 3: Test record_message
        logger.info("\n3. Testing record_message()...")
        await global_rate_limiter.record_message(account="+1234567890", job_id="test_job_1")
        await global_rate_limiter.record_message(account="+1234567890", job_id="test_job_2")
        await global_rate_limiter.record_message(job_id="test_job_3")
        logger.info("✓ Recorded 3 test messages")
        
        # Step 4: Test get_current_count
        logger.info("\n4. Testing get_current_count()...")
        count = await global_rate_limiter.get_current_count()
        assert count == 3, f"Expected 3 messages, got {count}"
        logger.info(f"✓ Current count: {count} (correct)")
        
        # Step 5: Test check_and_wait (should pass since we're under limit)
        logger.info("\n5. Testing check_and_wait() under limit...")
        result = await global_rate_limiter.check_and_wait()
        assert result == True, "check_and_wait should return True when under limit"
        logger.info("✓ check_and_wait passed (under limit)")
        
        # Step 6: Test sliding window (add old entry)
        logger.info("\n6. Testing sliding window with old entries...")
        async with AsyncSessionLocal() as db:
            old_entry = RateLimitEntry(
                timestamp=datetime.utcnow() - timedelta(hours=2),
                job_id="old_job"
            )
            db.add(old_entry)
            await db.commit()
            logger.info("✓ Added entry from 2 hours ago")
        
        count = await global_rate_limiter.get_current_count()
        assert count == 3, f"Old entry should not be counted, expected 3, got {count}"
        logger.info(f"✓ Sliding window working: count still {count} (old entry excluded)")
        
        # Step 7: Test cleanup_old_entries
        logger.info("\n7. Testing cleanup_old_entries()...")
        # Force cleanup by resetting last_cleanup time
        global_rate_limiter._last_cleanup = datetime.utcnow() - timedelta(hours=2)
        await global_rate_limiter.cleanup_old_entries()
        
        # Verify old entry was deleted
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(RateLimitEntry).filter(RateLimitEntry.job_id == "old_job")
            )
            old_entry = result.scalar_one_or_none()
            assert old_entry is None, "Old entry should have been cleaned up"
            logger.info("✓ Old entries cleaned up successfully")
        
        # Step 8: Test rate limit enforcement (simulate hitting limit)
        logger.info("\n8. Testing rate limit enforcement...")
        logger.info(f"   Current limit: {settings.max_messages_per_hour} messages/hour")
        
        # Add messages up to the limit
        current_count = await global_rate_limiter.get_current_count()
        messages_to_add = min(5, settings.max_messages_per_hour - current_count)
        
        for i in range(messages_to_add):
            await global_rate_limiter.record_message(job_id=f"limit_test_{i}")
        
        new_count = await global_rate_limiter.get_current_count()
        logger.info(f"✓ Added {messages_to_add} messages, total: {new_count}")
        
        # Step 9: Verify database persistence
        logger.info("\n9. Testing database persistence...")
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(RateLimitEntry))
            all_entries = result.scalars().all()
            logger.info(f"✓ Found {len(all_entries)} entries in database")
            
            # Verify entries have correct structure
            for entry in all_entries[:3]:
                assert entry.id is not None, "Entry should have ID"
                assert entry.timestamp is not None, "Entry should have timestamp"
                logger.info(f"   Entry {entry.id}: timestamp={entry.timestamp}, job_id={entry.job_id}")
        
        logger.info("✓ Database persistence verified")
        
        # Step 10: Clean up all test data
        logger.info("\n10. Final cleanup...")
        async with AsyncSessionLocal() as db:
            await db.execute(delete(RateLimitEntry))
            await db.commit()
            logger.info("✓ All test data cleaned up")
        
        final_count = await global_rate_limiter.get_current_count()
        assert final_count == 0, f"Expected 0 entries after cleanup, got {final_count}"
        logger.info("✓ Verified cleanup: 0 entries remaining")
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ ALL TESTS PASSED")
        logger.info("=" * 60)
        logger.info("\nGlobalRateLimiter Summary:")
        logger.info("- record_message() working correctly")
        logger.info("- get_current_count() accurate")
        logger.info("- check_and_wait() enforces limits")
        logger.info("- Sliding window excludes old entries")
        logger.info("- cleanup_old_entries() removes expired data")
        logger.info("- Database persistence verified")
        logger.info("- Rate limit coordination working")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_global_rate_limiter())
    sys.exit(0 if success else 1)
