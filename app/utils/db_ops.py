"""
MongoDB-backed database operations.
All CRUD operations for clone_jobs, channels, sync_state, accounts.
Backward-compatible API to minimize changes in routes.py and other callers.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.utils.mongodb import get_db
from app.utils.logger import logger
import uuid


# ---------------------------------------------------------------------------
# Channel operations
# ---------------------------------------------------------------------------

async def save_channel(channel_info: dict):
    """Upsert a channel document"""
    db = await get_db()
    await db.channels.update_one(
        {"channel_id": channel_info["channel_id"]},
        {"$set": {**channel_info, "updated_at": datetime.utcnow()}},
        upsert=True
    )


async def get_all_channels(search: Optional[str] = None) -> List[dict]:
    """Return all channels, optionally filtered by search string"""
    db = await get_db()
    query = {}
    if search:
        query = {
            "$or": [
                {"title": {"$regex": search, "$options": "i"}},
                {"username": {"$regex": search, "$options": "i"}},
            ]
        }
    cursor = db.channels.find(query, {"_id": 0})
    return await cursor.to_list(length=None)


async def delete_all_channels():
    """Delete all channels (called on account logout)"""
    db = await get_db()
    result = await db.channels.delete_many({})
    return result.deleted_count


async def get_channel_by_id(channel_id: str) -> Optional[dict]:
    """Get a single channel by its channel_id"""
    db = await get_db()
    return await db.channels.find_one({"channel_id": channel_id}, {"_id": 0})


# ---------------------------------------------------------------------------
# Clone job operations
# ---------------------------------------------------------------------------

async def create_job(
    source_channel: str,
    target_channel: str,
    start_message_id: Optional[int] = None,
    limit: Optional[int] = None,
    auto_sync: bool = False,
) -> dict:
    """Create a new clone job and persist it to MongoDB"""
    db = await get_db()
    job_id = str(uuid.uuid4())
    now = datetime.utcnow()
    job = {
        "job_id": job_id,
        "source_channel": source_channel,
        "target_channel": target_channel,
        "status": "pending",          # pending | running | completed | failed | stopped
        "total_messages": 0,
        "processed_messages": 0,
        "start_message_id": start_message_id,
        "limit": limit,
        "auto_sync": auto_sync,
        "error_message": None,
        "created_at": now,
        "updated_at": now,
    }
    await db.clone_jobs.insert_one(job)
    job.pop("_id", None)
    return job


async def get_job(job_id: str) -> Optional[dict]:
    """Get a clone job by its job_id"""
    db = await get_db()
    return await db.clone_jobs.find_one({"job_id": job_id}, {"_id": 0})


async def get_all_jobs(status: Optional[str] = None) -> List[dict]:
    """Return all clone jobs, newest first"""
    db = await get_db()
    query = {}
    if status:
        query["status"] = status
    cursor = db.clone_jobs.find(query, {"_id": 0}).sort("created_at", -1)
    return await cursor.to_list(length=None)


async def update_job(job_id: str, fields: dict):
    """Partially update a clone job"""
    db = await get_db()
    fields["updated_at"] = datetime.utcnow()
    await db.clone_jobs.update_one(
        {"job_id": job_id},
        {"$set": fields}
    )


async def increment_job_progress(job_id: str, count: int = 1):
    """Increment processed_messages counter atomically"""
    db = await get_db()
    await db.clone_jobs.update_one(
        {"job_id": job_id},
        {
            "$inc": {"processed_messages": count},
            "$set": {"updated_at": datetime.utcnow()},
        }
    )


async def delete_job(job_id: str):
    """Delete a clone job"""
    db = await get_db()
    await db.clone_jobs.delete_one({"job_id": job_id})


# ---------------------------------------------------------------------------
# Checkpoint operations  ← KEY FEATURE for VPS resume
# ---------------------------------------------------------------------------

async def save_checkpoint(job_id: str, last_message_id: int, processed: int):
    """
    Save job progress checkpoint to MongoDB.
    Called after every successfully cloned message so we can resume
    from the exact point if the VPS is destroyed mid-job.
    """
    db = await get_db()
    await db.job_checkpoints.update_one(
        {"job_id": job_id},
        {
            "$set": {
                "job_id": job_id,
                "last_message_id": last_message_id,
                "processed_messages": processed,
                "updated_at": datetime.utcnow(),
            }
        },
        upsert=True
    )


async def get_checkpoint(job_id: str) -> Optional[dict]:
    """Get the saved checkpoint for a job (used on resume)"""
    db = await get_db()
    return await db.job_checkpoints.find_one({"job_id": job_id}, {"_id": 0})


async def delete_checkpoint(job_id: str):
    """Delete checkpoint after job completes successfully"""
    db = await get_db()
    await db.job_checkpoints.delete_one({"job_id": job_id})


async def get_resumable_jobs() -> List[dict]:
    """
    Return jobs that were interrupted (status=running/pending) along
    with their last checkpoint.  Called on startup to show the user
    which jobs can be resumed.
    """
    db = await get_db()
    # Find all jobs that were running or pending when the VPS died
    interrupted_cursor = db.clone_jobs.find(
        {"status": {"$in": ["running", "pending"]}},
        {"_id": 0}
    )
    interrupted_jobs = await interrupted_cursor.to_list(length=None)

    results = []
    for job in interrupted_jobs:
        checkpoint = await db.job_checkpoints.find_one(
            {"job_id": job["job_id"]}, {"_id": 0}
        )
        results.append({
            "job": job,
            "checkpoint": checkpoint,
            "resume_from_message_id": checkpoint["last_message_id"] if checkpoint else job.get("start_message_id"),
            "already_processed": checkpoint["processed_messages"] if checkpoint else 0,
        })

    return results


# ---------------------------------------------------------------------------
# Sync state operations
# ---------------------------------------------------------------------------

async def update_sync_state(job_id: str, last_message_id: int):
    """Update the last synced message ID for an auto-sync job"""
    db = await get_db()
    await db.sync_state.update_one(
        {"job_id": job_id},
        {
            "$set": {
                "job_id": job_id,
                "last_message_id": last_message_id,
                "updated_at": datetime.utcnow(),
            }
        },
        upsert=True
    )


async def get_sync_state(job_id: str) -> Optional[dict]:
    """Get sync state for a job"""
    db = await get_db()
    return await db.sync_state.find_one({"job_id": job_id}, {"_id": 0})


async def get_auto_sync_jobs() -> List[dict]:
    """Return all jobs with auto_sync=True that are active"""
    db = await get_db()
    cursor = db.clone_jobs.find(
        {"auto_sync": True, "status": {"$in": ["running", "pending", "completed"]}},
        {"_id": 0}
    )
    return await cursor.to_list(length=None)
