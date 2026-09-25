import asyncio
from typing import Dict, Set
from app.utils.logger import logger
from app.utils import db_ops
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

        # Load active jobs from MongoDB
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
        """Load active sync jobs from MongoDB"""
        try:
            jobs = await db_ops.get_auto_sync_jobs()
            for job in jobs:
                self.active_jobs.add(job["job_id"])
                logger.info(f"Loaded sync job: {job['job_id']}")
        except Exception as e:
            logger.error(f"Failed to load active jobs: {e}")

    async def _check_and_sync(self):
        """Check for new messages and sync"""
        for job_id in list(self.active_jobs):
            job = await db_ops.get_job(job_id)

            if not job or not job.get("auto_sync"):
                self.active_jobs.discard(job_id)
                continue

            # Check if already syncing
            if job_id in self.tasks and not self.tasks[job_id].done():
                continue

            # Start sync task
            task = asyncio.create_task(self._sync_job(job))
            self.tasks[job_id] = task

    async def _sync_job(self, job: dict):
        """Sync a single job"""
        job_id = job["job_id"]
        try:
            logger.info(f"Syncing job: {job_id}")

            # Get last synced message ID from MongoDB
            sync_state = await db_ops.get_sync_state(job_id)
            last_message_id = sync_state["last_message_id"] if sync_state else None

            # Get client and cloner
            client = await session_manager.get_client()
            cloner = MessageCloner(client)

            # Get latest message ID from source
            latest_id = await cloner.get_latest_message_id(job["source_channel"])

            if not latest_id or (last_message_id and latest_id <= last_message_id):
                logger.debug(f"No new messages for job {job_id}")
                return

            # Clone new messages
            new_count = 0
            async for result in cloner.clone_messages(
                job["source_channel"],
                job["target_channel"],
                start_id=last_message_id,
                job_id=job_id,
            ):
                if result["status"] == "success":
                    new_count += 1
                    # Update sync state in MongoDB
                    await db_ops.update_sync_state(job_id, result["message_id"])

            logger.info(f"Synced {new_count} new messages for job {job_id}")

            # Update job progress in MongoDB
            if new_count > 0:
                current_job = await db_ops.get_job(job_id)
                if current_job:
                    await db_ops.update_job(job_id, {
                        "processed_messages": current_job["processed_messages"] + new_count
                    })

        except Exception as e:
            logger.error(f"Error syncing job {job_id}: {e}")

    def add_job(self, job_id: str):
        """Add a job to active sync"""
        self.active_jobs.add(job_id)
        logger.info(f"Added sync job: {job_id}")

    def remove_job(self, job_id: str):
        """Remove a job from active sync"""
        self.active_jobs.discard(job_id)

        if job_id in self.tasks:
            self.tasks[job_id].cancel()
            del self.tasks[job_id]

        logger.info(f"Removed sync job: {job_id}")


sync_worker = SyncWorker()
