from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime
from contextlib import asynccontextmanager
import uuid
import re
import asyncio

from app.utils.database import get_db, SessionLocal, Channel, CloneJob, SyncState
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

# Async context manager for database sessions
@asynccontextmanager
async def get_db_context():
    """Async context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# Models with validation
class ChannelResponse(BaseModel):
    channel_id: str
    title: str
    username: Optional[str]
    member_count: Optional[int]
    is_private: bool

class CloneJobCreate(BaseModel):
    """Request to create a clone job with validation"""
    source_channel: str = Field(
        ..., 
        min_length=1,
        max_length=50,
        description="Source channel ID or @username"
    )
    target_channel: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Target channel ID or @username"
    )
    start_message_id: Optional[int] = Field(
        None,
        ge=0,
        description="Start from message ID (must be >= 0)"
    )
    limit: Optional[int] = Field(
        None,
        ge=1,
        le=10000,
        description="Max messages to clone (1-10000)"
    )
    auto_sync: bool = Field(
        False,
        description="Enable auto-sync"
    )
    
    @validator('source_channel', 'target_channel')
    def validate_channel_format(cls, v):
        """Validate channel ID format"""
        # Channel IDs should be numeric (with optional -100 prefix) or @username
        if not (re.match(r'^-?100?\d+$', v) or re.match(r'^@[\w]{5,32}$', v)):
            raise ValueError(
                "Channel must be numeric ID (e.g., -1001234567890) or @username"
            )
        return v
    
    @validator('target_channel')
    def validate_different_channels(cls, v, values):
        """Ensure source and target are different"""
        if 'source_channel' in values and v == values['source_channel']:
            raise ValueError("Source and target channels must be different")
        return v

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

class TelegramLoginRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20)
    api_id: int = Field(..., gt=0)
    api_hash: str = Field(..., min_length=32, max_length=32)

class TelegramCodeRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20)
    code: str = Field(..., min_length=5, max_length=10)

class TelegramPasswordRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=1)

class TelegramLogoutRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20)

# Auth Routes
@auth_router.get("/status")
async def auth_status():
    """Check authentication status"""
    clients = session_manager.get_available_clients()
    return {
        "authenticated": len(clients) > 0,
        "accounts": len(clients)
    }

# Channel Routes
@channels_router.get("/list", response_model=List[ChannelResponse])
async def list_channels(
    refresh: bool = False,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all channels"""
    try:
        # Check if any accounts are logged in
        if not session_manager.clients:
            # No accounts logged in - clear stale channels
            db.query(Channel).delete()
            db.commit()
            return []
        
        if refresh:
            client = await session_manager.get_client()
            scraper = ChannelScraper(client)
            # Don't fetch member counts - it's slow and not critical
            channels = await scraper.get_all_channels(save_to_db=True, fetch_member_count=False)
            return channels
        
        # Get from database
        query = db.query(Channel)
        if search:
            query = query.filter(
                (Channel.title.contains(search)) | 
                (Channel.username.contains(search))
            )
        
        channels = query.all()
        return [
            {
                "channel_id": ch.channel_id,
                "title": ch.title,
                "username": ch.username,
                "member_count": ch.member_count,
                "is_private": ch.is_private
            }
            for ch in channels
        ]
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

# Job Routes
@jobs_router.post("/clone", response_model=CloneJobResponse)
async def create_clone_job(
    job_data: CloneJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a new clone job with validation"""
    try:
        job_id = str(uuid.uuid4())
        
        # Create job in database
        job = CloneJob(
            job_id=job_id,
            source_channel=job_data.source_channel,
            target_channel=job_data.target_channel,
            start_message_id=job_data.start_message_id,
            auto_sync=job_data.auto_sync,
            status="pending"
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Start cloning in background
        background_tasks.add_task(
            run_clone_job,
            job_id,
            job_data.source_channel,
            job_data.target_channel,
            job_data.start_message_id,
            job_data.limit,
            job_data.auto_sync
        )
        
        return job
    except ValueError as e:
        # Pydantic validation error
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating clone job: {e}")
        raise HTTPException(status_code=500, detail="Failed to create job")

@jobs_router.get("/list", response_model=List[CloneJobResponse])
async def list_jobs(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all clone jobs"""
    query = db.query(CloneJob)
    if status:
        query = query.filter(CloneJob.status == status)
    
    jobs = query.order_by(CloneJob.created_at.desc()).all()
    return jobs

@jobs_router.get("/{job_id}", response_model=CloneJobResponse)
async def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get job details"""
    job = db.query(CloneJob).filter(CloneJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@jobs_router.post("/{job_id}/stop")
async def stop_job(job_id: str, db: Session = Depends(get_db)):
    """Stop a running job"""
    job = db.query(CloneJob).filter(CloneJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job.status = "stopped"
    db.commit()
    
    if job.auto_sync:
        sync_worker.remove_job(job_id)
    
    return {"message": "Job stopped"}

@jobs_router.delete("/{job_id}")
async def delete_job(job_id: str, db: Session = Depends(get_db)):
    """Delete a job"""
    job = db.query(CloneJob).filter(CloneJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Stop if running
    if job.auto_sync:
        sync_worker.remove_job(job_id)
    
    # Cleanup files
    storage_manager.cleanup_job(job_id)
    
    # Delete from database
    db.delete(job)
    db.commit()
    
    return {"message": "Job deleted"}

# System Routes
@system_router.get("/stats")
async def system_stats(db: Session = Depends(get_db)):
    """Get system statistics"""
    # Check if any accounts are logged in
    if not session_manager.clients:
        # No accounts - clear stale channels and return zeros
        db.query(Channel).delete()
        db.commit()
        
        total_channels = 0
    else:
        total_channels = db.query(Channel).count()
    
    total_jobs = db.query(CloneJob).count()
    active_jobs = db.query(CloneJob).filter(
        CloneJob.status.in_(["running", "pending"])
    ).count()
    
    disk_usage = storage_manager.get_disk_usage()
    
    return {
        "channels": total_channels,
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "disk_usage": disk_usage
    }

@system_router.post("/cleanup")
async def cleanup_storage():
    """Cleanup old files"""
    storage_manager.cleanup_old_files(max_age_hours=24)
    return {"message": "Cleanup completed"}

# Account Management Routes
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
            request.phone,
            request.api_id,
            request.api_hash
        )
        return result
    except Exception as e:
        logger.error(f"Error sending code: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@accounts_router.post("/login/verify-code")
async def verify_login_code(request: TelegramCodeRequest):
    """Verify the code and complete login"""
    try:
        result = await telegram_auth_manager.verify_code(
            request.phone,
            request.code
        )
        return result
    except Exception as e:
        logger.error(f"Error verifying code: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@accounts_router.post("/login/verify-password")
async def verify_2fa_password(request: TelegramPasswordRequest):
    """Verify 2FA password"""
    try:
        result = await telegram_auth_manager.verify_password(
            request.phone,
            request.password
        )
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

# Background task with async context manager
async def run_clone_job(
    job_id: str,
    source_channel: str,
    target_channel: str,
    start_message_id: Optional[int],
    limit: Optional[int],
    auto_sync: bool
):
    """Run clone job in background with proper async context"""
    
    async with get_db_context() as db:
        try:
            # Update status to running
            result = db.query(CloneJob).filter(
                CloneJob.job_id == job_id,
                CloneJob.status == "pending"
            ).update({"status": "running"})
            db.commit()
            
            if result == 0:
                logger.error(f"Job {job_id} not found or not in pending state")
                return
            
            # Get client and cloner
            client = await session_manager.get_client()
            cloner = MessageCloner(client)
            
            # Clone messages
            processed = 0
            async for result in cloner.clone_messages(
                source_channel,
                target_channel,
                start_id=start_message_id,
                limit=limit,
                job_id=job_id
            ):
                if result["status"] == "success":
                    processed += 1
                    # Atomic update
                    db.query(CloneJob).filter(
                        CloneJob.job_id == job_id
                    ).update({"processed_messages": processed})
                    db.commit()
            
            # Mark as completed
            db.query(CloneJob).filter(
                CloneJob.job_id == job_id
            ).update({
                "status": "completed",
                "updated_at": datetime.utcnow()
            })
            db.commit()
            
            # Add to sync worker if auto_sync
            if auto_sync:
                sync_worker.add_job(job_id)
            
            # Cleanup job files
            storage_manager.cleanup_job(job_id)
            
        except asyncio.CancelledError:
            logger.warning(f"Job {job_id} was cancelled")
            db.query(CloneJob).filter(
                CloneJob.job_id == job_id
            ).update({
                "status": "paused",
                "updated_at": datetime.utcnow()
            })
            db.commit()
            raise
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            db.query(CloneJob).filter(
                CloneJob.job_id == job_id
            ).update({
                "status": "failed",
                "error_message": str(e),
                "updated_at": datetime.utcnow()
            })
            db.commit()
