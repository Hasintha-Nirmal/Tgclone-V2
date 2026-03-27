import asyncio
from typing import Dict, Set
from app.utils.logger import logger
from app.utils.database import AsyncSessionLocal, CloneJob, SyncState
from app.utils.rate_limiter import global_rate_limiter
from app.cloner.message_cloner import MessageCloner
from app.auth.session_manager import session_manager
from config.settings import settings
from datetime import datetime
from sqlalchemy import select, update

class SyncWorker:
    def __init__(self):
        self.active_jobs: Set[str] = set()
        self.running = False
        self.tasks: Dict[str, asyncio.Task] = {}
        self.shutdown_timeout = settings.worker_shutdown_timeout
    
    async def start(self):
        """Start the sync worker"""
        self.running = True
        logger.info("Sync worker started")
        
        # Load active jobs from database
        await self._load_active_jobs()
        
        # Start monitoring loop
        while self.running:
            try:
                await self._check_and_sync()
                await asyncio.sleep(settings.sync_interval_seconds)
            except Exception as e:
                logger.error(f"Sync worker error: {e}")
                await asyncio.sleep(5)
    
    async def stop(self):
        """Stop the sync worker gracefully with timeout"""
        logger.info("Initiating graceful shutdown...")
        self.running = False
        
        if not self.tasks:
            logger.info("No active tasks to shutdown")
            return
        
        # Cancel all tasks
        for job_id, task in self.tasks.items():
            logger.info(f"Cancelling task: {job_id}")
            task.cancel()
        
        # Wait for tasks to complete with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*self.tasks.values(), return_exceptions=True),
                timeout=self.shutdown_timeout
            )
            logger.info("All tasks completed gracefully")
        except asyncio.TimeoutError:
            logger.warning(f"Shutdown timeout after {self.shutdown_timeout}s - some tasks may not have completed")
        
        self.tasks.clear()
        logger.info("Sync worker stopped")
    
    async def _load_active_jobs(self):
        """Load active sync jobs from database"""
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(
                    select(CloneJob).filter(
                        CloneJob.auto_sync == True,
                        CloneJob.status.in_(["running", "pending", "paused"])
                    )
                )
                jobs = result.scalars().all()
                
                for job in jobs:
                    self.active_jobs.add(job.job_id)
                    logger.info(f"Loaded sync job: {job.job_id}")
            except Exception as e:
                logger.error(f"Error loading active jobs: {e}")
    
    async def _check_and_sync(self):
        """Check for new messages and sync with global rate limiting"""
        
        # Get current rate limit count from global rate limiter
        current_count = await global_rate_limiter.get_current_count()
        
        # Check if we've hit global limit
        if current_count >= settings.max_messages_per_hour:
            logger.warning(
                f"Global hourly message limit reached "
                f"({current_count}/{settings.max_messages_per_hour}). "
                f"Pausing sync until next hour."
            )
            return
        
        # Calculate remaining capacity
        remaining = settings.max_messages_per_hour - current_count
        
        async with AsyncSessionLocal() as db:
            try:
                for job_id in list(self.active_jobs):
                    if remaining <= 0:
                        logger.debug("No remaining capacity for this hour")
                        break
                    
                    result = await db.execute(
                        select(CloneJob).filter(CloneJob.job_id == job_id)
                    )
                    job = result.scalar_one_or_none()
                    
                    if not job or not job.auto_sync:
                        self.active_jobs.discard(job_id)
                        continue
                    
                    # Check if already syncing
                    if job_id in self.tasks and not self.tasks[job_id].done():
                        continue
                    
                    # Start sync task with exception handling
                    task = asyncio.create_task(self._sync_job(job))
                    
                    # Add exception callback to prevent silent failures
                    def handle_task_exception(t, jid=job_id):
                        try:
                            t.result()
                        except asyncio.CancelledError:
                            pass  # Expected during shutdown
                        except Exception as e:
                            logger.error(f"Sync task {jid} failed with unhandled exception: {e}", exc_info=True)
                    
                    task.add_done_callback(handle_task_exception)
                    self.tasks[job_id] = task
            except Exception as e:
                logger.error(f"Error in check_and_sync: {e}")
    
    async def _sync_job(self, job: CloneJob):
        """Sync a single job with rate limit tracking"""
        try:
            logger.info(f"Syncing job: {job.job_id}")
            
            # Get last synced message ID
            async with AsyncSessionLocal() as db:
                try:
                    result = await db.execute(
                        select(SyncState).filter(SyncState.job_id == job.job_id)
                    )
                    sync_state = result.scalar_one_or_none()
                    
                    last_message_id = sync_state.last_message_id if sync_state else None
                except Exception as e:
                    logger.error(f"Error getting sync state: {e}")
                    last_message_id = None
            
            # Get client and cloner
            client = await session_manager.get_client()
            cloner = MessageCloner(client)
            
            # Get latest message ID from source
            latest_id = await cloner.get_latest_message_id(job.source_channel)
            
            if not latest_id or (last_message_id and latest_id <= last_message_id):
                logger.debug(f"No new messages for job {job.job_id}")
                return
            
            # Clone new messages and track count
            new_count = 0
            async for result in cloner.clone_messages(
                job.source_channel,
                job.target_channel,
                start_id=last_message_id,
                job_id=job.job_id,
                timeout_seconds=300  # 5 minute timeout for sync operations
            ):
                if result["status"] == "success":
                    new_count += 1
                    await self._update_sync_state(job.job_id, result["message_id"])
                    
                    # Check if we've hit limit during sync
                    current_count = await global_rate_limiter.get_current_count()
                    if current_count >= settings.max_messages_per_hour:
                        logger.warning(
                            f"Hourly limit reached during sync. "
                            f"Stopping job {job.job_id}"
                        )
                        break
            
            logger.info(
                f"Synced {new_count} messages for job {job.job_id} "
                f"(global: {await global_rate_limiter.get_current_count()}/{settings.max_messages_per_hour})"
            )
            
            # Update job
            async with AsyncSessionLocal() as db:
                try:
                    result = await db.execute(
                        select(CloneJob).filter(CloneJob.job_id == job.job_id)
                    )
                    job = result.scalar_one_or_none()
                    if job:
                        job.processed_messages += new_count
                        job.updated_at = datetime.utcnow()
                        await db.commit()
                except Exception as e:
                    logger.error(f"Error updating job: {e}")
            
        except asyncio.CancelledError:
            logger.info(f"Sync job {job.job_id} cancelled - cleaning up gracefully")
            # State is already saved in database via update_sync_state calls
            # No additional cleanup needed - re-raise to complete cancellation
            raise
            
        except Exception as e:
            logger.error(f"Error syncing job {job.job_id}: {e}")
    
    async def _update_sync_state(self, job_id: str, message_id: int):
        """Update sync state in database"""
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(
                    select(SyncState).filter(SyncState.job_id == job_id)
                )
                sync_state = result.scalar_one_or_none()
                
                if sync_state:
                    sync_state.last_message_id = message_id
                    sync_state.updated_at = datetime.utcnow()
                else:
                    sync_state = SyncState(
                        job_id=job_id,
                        last_message_id=message_id
                    )
                    db.add(sync_state)
                
                await db.commit()
            except Exception as e:
                logger.error(f"Error updating sync state: {e}")
                await db.rollback()
    
    def add_job(self, job_id: str):
        """Add a job to active sync"""
        self.active_jobs.add(job_id)
        logger.info(f"Added sync job: {job_id}")
    
    def remove_job(self, job_id: str):
        """Remove a job from active sync"""
        if job_id in self.active_jobs:
            self.active_jobs.discard(job_id)
        
        if job_id in self.tasks:
            self.tasks[job_id].cancel()
            del self.tasks[job_id]
        
        logger.info(f"Removed sync job: {job_id}")

sync_worker = SyncWorker()
