from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.utils import db_ops
from app.auth.session_manager import session_manager
from app.scraper.channel_scraper import ChannelScraper
from app.cloner.message_cloner import MessageCloner
from app.worker.sync_worker import sync_worker
from app.utils.storage import storage_manager
from app.utils.logger import logger
from app.web.telegram_auth import telegram_auth_manager

# Routers
auth_router = APIRouter()
channels_router = APIRouter()
jobs_router = APIRouter()
system_router = APIRouter()
accounts_router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ChannelResponse(BaseModel):
    channel_id: str
    title: str
    username: Optional[str] = None
    member_count: Optional[int] = None
    is_private: bool


class CloneJobCreate(BaseModel):
    source_channel: str
    target_channel: str
    start_message_id: Optional[int] = None
    limit: Optional[int] = None
    auto_sync: bool = False


class CloneJobResponse(BaseModel):
    job_id: str
    source_channel: str
    target_channel: str
    status: str
    total_messages: int
    processed_messages: int
    auto_sync: bool
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None


class TelegramLoginRequest(BaseModel):
    phone: str
    api_id: int
    api_hash: str


class TelegramCodeRequest(BaseModel):
    phone: str
    code: str


class TelegramPasswordRequest(BaseModel):
    phone: str
    password: str


class TelegramLogoutRequest(BaseModel):
    phone: str


# ---------------------------------------------------------------------------
# Auth Routes
# ---------------------------------------------------------------------------

@auth_router.get("/status")
async def auth_status():
    """Check authentication status"""
    clients = session_manager.get_available_clients()
    return {
        "authenticated": len(clients) > 0,
        "accounts": len(clients),
    }


# ---------------------------------------------------------------------------
# Channel Routes
# ---------------------------------------------------------------------------

@channels_router.get("/list", response_model=List[ChannelResponse])
async def list_channels(
    refresh: bool = False,
    search: Optional[str] = None,
):
    """List all channels"""
    try:
        if not session_manager.clients:
            await db_ops.delete_all_channels()
            return []

        if refresh:
            client = await session_manager.get_client()
            scraper = ChannelScraper(client)
            channels = await scraper.get_all_channels(save_to_db=True, fetch_member_count=False)
            return channels

        return await db_ops.get_all_channels(search=search)

    except Exception as e:
        logger.error(f"Error listing channels: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@channels_router.get("/{channel_id}")
async def get_channel(channel_id: str):
    """Get specific channel details"""
    try:
        client = await session_manager.get_client()
        scraper = ChannelScraper(client)
        channel = await scraper.get_channel_by_id(channel_id)

        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")

        return channel
    except Exception as e:
        logger.error(f"Error getting channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Job Routes
# ---------------------------------------------------------------------------

@jobs_router.post("/clone", response_model=CloneJobResponse)
async def create_clone_job(
    job_data: CloneJobCreate,
    background_tasks: BackgroundTasks,
):
    """Create a new clone job"""
    try:
        job = await db_ops.create_job(
            source_channel=job_data.source_channel,
            target_channel=job_data.target_channel,
            start_message_id=job_data.start_message_id,
            limit=job_data.limit,
            auto_sync=job_data.auto_sync,
        )

        background_tasks.add_task(
            run_clone_job,
            job["job_id"],
            job_data.source_channel,
            job_data.target_channel,
            job_data.start_message_id,
            job_data.limit,
            job_data.auto_sync,
            resume_from_id=None,
        )

        return job
    except Exception as e:
        logger.error(f"Error creating clone job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@jobs_router.get("/list", response_model=List[CloneJobResponse])
async def list_jobs(status: Optional[str] = None):
    """List all clone jobs"""
    return await db_ops.get_all_jobs(status=status)


@jobs_router.get("/resumable")
async def list_resumable_jobs():
    """
    List jobs that were interrupted (VPS crash/restart) and can be resumed.
    Returns job details + checkpoint (last message ID that was successfully cloned).
    """
    try:
        resumable = await db_ops.get_resumable_jobs()
        return {"resumable_jobs": resumable, "count": len(resumable)}
    except Exception as e:
        logger.error(f"Error fetching resumable jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@jobs_router.post("/{job_id}/resume")
async def resume_job(job_id: str, background_tasks: BackgroundTasks):
    """
    Resume an interrupted clone job from its last checkpoint.
    Use this after a VPS restart to continue from where it left off.
    """
    job = await db_ops.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    checkpoint = await db_ops.get_checkpoint(job_id)
    resume_from_id = checkpoint["last_message_id"] if checkpoint else job.get("start_message_id")
    already_processed = checkpoint["processed_messages"] if checkpoint else 0

    logger.info(
        f"Resuming job {job_id} from message_id={resume_from_id} "
        f"({already_processed} already processed)"
    )

    # Mark as running again
    await db_ops.update_job(job_id, {
        "status": "running",
        "processed_messages": already_processed,
    })

    background_tasks.add_task(
        run_clone_job,
        job_id,
        job["source_channel"],
        job["target_channel"],
        job.get("start_message_id"),
        job.get("limit"),
        job.get("auto_sync", False),
        resume_from_id=resume_from_id,
    )

    return {
        "message": f"Resuming job {job_id} from message_id={resume_from_id}",
        "already_processed": already_processed,
        "resume_from_message_id": resume_from_id,
    }


@jobs_router.get("/{job_id}", response_model=CloneJobResponse)
async def get_job(job_id: str):
    """Get job details"""
    job = await db_ops.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@jobs_router.get("/{job_id}/checkpoint")
async def get_job_checkpoint(job_id: str):
    """
    Get the saved checkpoint for a job.
    Shows exactly which message was last successfully cloned.
    """
    job = await db_ops.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    checkpoint = await db_ops.get_checkpoint(job_id)
    return {
        "job_id": job_id,
        "job_status": job["status"],
        "checkpoint": checkpoint,
        "can_resume": job["status"] in ("running", "pending", "failed") and checkpoint is not None,
    }


@jobs_router.post("/{job_id}/stop")
async def stop_job(job_id: str):
    """Stop a running job"""
    job = await db_ops.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    await db_ops.update_job(job_id, {"status": "stopped"})

    if job.get("auto_sync"):
        sync_worker.remove_job(job_id)

    return {"message": "Job stopped"}


@jobs_router.delete("/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its checkpoint"""
    job = await db_ops.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("auto_sync"):
        sync_worker.remove_job(job_id)

    storage_manager.cleanup_job(job_id)
    await db_ops.delete_checkpoint(job_id)
    await db_ops.delete_job(job_id)

    return {"message": "Job deleted"}


# ---------------------------------------------------------------------------
# System Routes
# ---------------------------------------------------------------------------

@system_router.get("/stats")
async def system_stats():
    """Get system statistics"""
    if not session_manager.clients:
        await db_ops.delete_all_channels()
        total_channels = 0
    else:
        channels = await db_ops.get_all_channels()
        total_channels = len(channels)

    all_jobs = await db_ops.get_all_jobs()
    active_jobs = sum(1 for j in all_jobs if j["status"] in ("running", "pending"))
    resumable = await db_ops.get_resumable_jobs()

    disk_usage = storage_manager.get_disk_usage()

    return {
        "channels": total_channels,
        "total_jobs": len(all_jobs),
        "active_jobs": active_jobs,
        "resumable_jobs": len(resumable),   # ← how many jobs can be resumed
        "disk_usage": disk_usage,
    }


@system_router.post("/cleanup")
async def cleanup_storage():
    """Cleanup old files"""
    storage_manager.cleanup_old_files(max_age_hours=24)
    return {"message": "Cleanup completed"}


# ---------------------------------------------------------------------------
# Account Management Routes
# ---------------------------------------------------------------------------

@accounts_router.get("/list")
async def list_accounts():
    """List all logged in accounts"""
    try:
        accounts = await telegram_auth_manager.get_logged_accounts()
        return {"accounts": accounts}
    except Exception as e:
        logger.error(f"Error listing accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@accounts_router.post("/login/send-code")
async def send_login_code(request: TelegramLoginRequest):
    """Send verification code to phone"""
    try:
        result = await telegram_auth_manager.send_code(
            request.phone, request.api_id, request.api_hash
        )
        return result
    except Exception as e:
        logger.error(f"Error sending code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@accounts_router.post("/login/verify-code")
async def verify_login_code(request: TelegramCodeRequest):
    """Verify the code and complete login"""
    try:
        result = await telegram_auth_manager.verify_code(request.phone, request.code)
        return result
    except Exception as e:
        logger.error(f"Error verifying code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@accounts_router.post("/login/verify-password")
async def verify_2fa_password(request: TelegramPasswordRequest):
    """Verify 2FA password"""
    try:
        result = await telegram_auth_manager.verify_password(request.phone, request.password)
        return result
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@accounts_router.post("/logout")
async def logout_account(request: TelegramLogoutRequest):
    """Logout account and remove session"""
    try:
        result = await telegram_auth_manager.logout_account(request.phone)
        return result
    except Exception as e:
        logger.error(f"Error logging out: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------

async def run_clone_job(
    job_id: str,
    source_channel: str,
    target_channel: str,
    start_message_id: Optional[int],
    limit: Optional[int],
    auto_sync: bool,
    resume_from_id: Optional[int] = None,
):
    """Run clone job in background (supports resume)"""
    try:
        await db_ops.update_job(job_id, {"status": "running"})

        client = await session_manager.get_client()
        cloner = MessageCloner(client)

        processed = 0
        async for result in cloner.clone_messages(
            source_channel,
            target_channel,
            start_id=start_message_id,
            limit=limit,
            job_id=job_id,
            resume_from_id=resume_from_id,  # ← pass resume point
        ):
            if result["status"] == "success":
                processed += 1
                await db_ops.increment_job_progress(job_id)

        await db_ops.update_job(job_id, {"status": "completed"})

        if auto_sync:
            sync_worker.add_job(job_id)

        # Job completed cleanly — mark checkpoint as completed so it won't show as
        # resumable, but keep it in MongoDB for history. User deletes it via the UI.
        await db_ops.save_checkpoint_completed(job_id)

        storage_manager.cleanup_job(job_id)

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        await db_ops.update_job(job_id, {
            "status": "failed",
            "error_message": str(e),
        })
        # Keep checkpoint intact so user can resume later
