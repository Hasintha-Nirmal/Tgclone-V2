"""
Centralized rate limiting system with database persistence.

This module provides a global rate limiter that coordinates rate limits
across all jobs (manual and auto-sync) and survives application restarts
by persisting rate limit data to the database.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, delete
from app.utils.database import AsyncSessionLocal, RateLimitEntry
from app.utils.logger import logger
from config.settings import settings


class GlobalRateLimiter:
    """
    Centralized rate limiter using database persistence.
    
    Implements a sliding window algorithm to track message sending
    and enforce hourly rate limits across all jobs and application restarts.
    """
    
    def __init__(self):
        self._lock = asyncio.Lock()
        self._cleanup_interval = 3600  # Cleanup every hour
        self._last_cleanup = datetime.utcnow()
    
    async def check_and_wait(self, account: Optional[str] = None) -> bool:
        """
        Check if we're within rate limits. If at limit, wait until we can proceed.
        
        Args:
            account: Optional account phone number for per-account tracking
            
        Returns:
            bool: True if within limits or after waiting, False if error occurred
        """
        async with self._lock:
            try:
                current_count = await self.get_current_count()
                
                if current_count >= settings.max_messages_per_hour:
                    # Calculate wait time until oldest entry expires
                    wait_time = await self._calculate_wait_time()
                    
                    if wait_time > 0:
                        logger.warning(
                            f"Hourly rate limit reached ({current_count}/{settings.max_messages_per_hour}). "
                            f"Waiting {wait_time} seconds to protect account..."
                        )
                        await asyncio.sleep(wait_time)
                        
                        # After waiting, cleanup old entries
                        await self.cleanup_old_entries()
                
                return True
                
            except Exception as e:
                logger.error(f"Error checking rate limit: {e}")
                return False
    
    async def record_message(self, account: Optional[str] = None, job_id: Optional[str] = None):
        """
        Record a message send event to the database.
        
        Args:
            account: Optional account phone number
            job_id: Optional job ID for tracking
        """
        try:
            async with AsyncSessionLocal() as db:
                entry = RateLimitEntry(
                    timestamp=datetime.utcnow(),
                    account_phone=account,
                    job_id=job_id
                )
                db.add(entry)
                await db.commit()
                
                logger.debug(f"Recorded message: account={account}, job_id={job_id}")
                
        except Exception as e:
            logger.error(f"Error recording message: {e}")
    
    async def get_current_count(self) -> int:
        """
        Get the count of messages sent in the last hour.
        
        Returns:
            int: Number of messages in the current sliding window
        """
        try:
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(RateLimitEntry).filter(
                        RateLimitEntry.timestamp > one_hour_ago
                    )
                )
                entries = result.scalars().all()
                count = len(entries)
                
                logger.debug(f"Current rate limit count: {count}/{settings.max_messages_per_hour}")
                return count
                
        except Exception as e:
            logger.error(f"Error getting current count: {e}")
            return 0
    
    async def cleanup_old_entries(self):
        """
        Remove rate limit entries older than 1 hour from the database.
        
        This should be called periodically to prevent the table from growing indefinitely.
        """
        try:
            # Only cleanup if enough time has passed
            now = datetime.utcnow()
            if (now - self._last_cleanup).total_seconds() < self._cleanup_interval:
                return
            
            one_hour_ago = now - timedelta(hours=1)
            
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    delete(RateLimitEntry).filter(
                        RateLimitEntry.timestamp <= one_hour_ago
                    )
                )
                await db.commit()
                
                deleted_count = result.rowcount
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old rate limit entries")
                
                self._last_cleanup = now
                
        except Exception as e:
            logger.error(f"Error cleaning up old entries: {e}")
    
    async def _calculate_wait_time(self) -> int:
        """
        Calculate how long to wait until the oldest entry expires.
        
        Returns:
            int: Wait time in seconds
        """
        try:
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            async with AsyncSessionLocal() as db:
                # Get the oldest entry in the current window
                result = await db.execute(
                    select(RateLimitEntry)
                    .filter(RateLimitEntry.timestamp > one_hour_ago)
                    .order_by(RateLimitEntry.timestamp.asc())
                    .limit(1)
                )
                oldest_entry = result.scalar_one_or_none()
                
                if oldest_entry:
                    # Calculate when this entry will expire (1 hour after it was created)
                    expiry_time = oldest_entry.timestamp + timedelta(hours=1)
                    wait_seconds = (expiry_time - datetime.utcnow()).total_seconds()
                    
                    # Add a small buffer
                    return max(int(wait_seconds) + 5, 0)
                
                return 0
                
        except Exception as e:
            logger.error(f"Error calculating wait time: {e}")
            # Default to waiting 1 hour if we can't calculate
            return 3600


# Global singleton instance
global_rate_limiter = GlobalRateLimiter()
