import asyncio
from typing import Dict, Set
from app.utils.logger import logger
from app.utils.database import SessionLocal, CloneJob, SyncState
from app.cloner.message_cloner import MessageCloner
from app.auth.session_manager import session_manager
from config.settings import settings
from datetime import datetime

class SyncWorker:
    def __init__(self):
        self.active_jobs: Set[str] = set()
        self.running = False
        self.tasks: Dict[str, asyncio.Task] = {}
    
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
        """Stop the sync worker"""
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks.values():
            task.cancel()
        
        logger.info("Sync worker stopped")
    
    async def _load_active_jobs(self):
        """Load active sync jobs from database"""
        db = SessionLocal()
        try:
            jobs = db.query(CloneJob).filter(
                CloneJob.auto_sync == True,
                CloneJob.status.in_(["running", "pending"])
            ).all()
            
            for job in jobs:
                self.active_jobs.add(job.job_id)
                logger.info(f"Loaded sync job: {job.job_id}")
        finally:
            db.close()
    
    async def _check_and_sync(self):
        """Check for new messages and sync"""
        db = SessionLocal()
        try:
            for job_id in list(self.active_jobs):
                job = db.query(CloneJob).filter(CloneJob.job_id == job_id).first()
                
                if not job or not job.auto_sync:
                    self.active_jobs.remove(job_id)
                    continue
                
                # Check if already syncing
                if job_id in self.tasks and not self.tasks[job_id].done():
                    continue
                
                # Start sync task
                task = asyncio.create_task(self._sync_job(job))
                self.tasks[job_id] = task
        finally:
            db.close()
    
    async def _sync_job(self, job: CloneJob):
        """Sync a single job"""
        try:
            logger.info(f"Syncing job: {job.job_id}")
            
            # Get last synced message ID
            db = SessionLocal()
            sync_state = db.query(SyncState).filter(
                SyncState.job_id == job.job_id
            ).first()
            
            last_message_id = sync_state.last_message_id if sync_state else None
            db.close()
            
            # Get client and cloner
            client = await session_manager.get_client()
            cloner = MessageCloner(client)
            
            # Get latest message ID from source
            latest_id = await cloner.get_latest_message_id(job.source_channel)
            
            if not latest_id or (last_message_id and latest_id <= last_message_id):
                logger.debug(f"No new messages for job {job.job_id}")
                return
            
            # Clone new messages
            new_count = 0
            async for result in cloner.clone_messages(
                job.source_channel,
                job.target_channel,
                start_id=last_message_id,
                job_id=job.job_id
            ):
                if result["status"] == "success":
                    new_count += 1
                    # Update sync state
                    self._update_sync_state(job.job_id, result["message_id"])
            
            logger.info(f"Synced {new_count} new messages for job {job.job_id}")
            
            # Update job
            db = SessionLocal()
            job = db.query(CloneJob).filter(CloneJob.job_id == job.job_id).first()
            if job:
                job.processed_messages += new_count
                job.updated_at = datetime.utcnow()
                db.commit()
            db.close()
            
        except Exception as e:
            logger.error(f"Error syncing job {job.job_id}: {e}")
    
    def _update_sync_state(self, job_id: str, message_id: int):
        """Update sync state in database"""
        db = SessionLocal()
        try:
            sync_state = db.query(SyncState).filter(
                SyncState.job_id == job_id
            ).first()
            
            if sync_state:
                sync_state.last_message_id = message_id
                sync_state.updated_at = datetime.utcnow()
            else:
                sync_state = SyncState(
                    job_id=job_id,
                    last_message_id=message_id
                )
                db.add(sync_state)
            
            db.commit()
        finally:
            db.close()
    
    def add_job(self, job_id: str):
        """Add a job to active sync"""
        self.active_jobs.add(job_id)
        logger.info(f"Added sync job: {job_id}")
    
    def remove_job(self, job_id: str):
        """Remove a job from active sync"""
        if job_id in self.active_jobs:
            self.active_jobs.remove(job_id)
        
        if job_id in self.tasks:
            self.tasks[job_id].cancel()
            del self.tasks[job_id]
        
        logger.info(f"Removed sync job: {job_id}")

sync_worker = SyncWorker()
