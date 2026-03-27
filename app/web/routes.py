from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime
from contextlib import asynccontextmanager
import uuid
import re
import asyncio

from app.utils.database import get_db, AsyncSessionLocal, Channel, CloneJob, SyncState
from app.auth.session_manager import session_manager
from app.scraper.channel_scraper import ChannelScraper
from app.cloner.message_cloner import MessageCloner
from app.worker.sync_worker import sync_worker
from app.utils.storage import storage_manager
from app.utils.logger import logger
from app.web.telegram_auth import telegram_auth_manager
from app.utils.validators import validate_channel_id, validate_job_id
from config.settings import settings

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
    async with AsyncSessionLocal() as db:
        try:
            yield db
        except Exception:
            await db.rollback()
            raise
        finally:
            await db.close()

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
    clients = await session_manager.get_available_clients()
    return {
        "authenticated": len(clients) > 0,
        "accounts": len(clients)
    }

# Channel Routes
@channels_router.get("/list", response_model=List[ChannelResponse])
async def list_channels(
    refresh: bool = False,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """List all channels"""
    try:
        # Check if any accounts are logged in
        if not session_manager.clients:
            # No accounts logged in - clear stale channels
            try:
                await db.execute(delete(Channel))
                await db.commit()
            except Exception as db_error:
                logger.error(f"Error clearing channels: {db_error}")
                await db.rollback()
            return []
        
        if refresh:
            client = await session_manager.get_client()
            scraper = ChannelScraper(client)
            
            # Fetch channels with timeout
            channels = await asyncio.wait_for(
                scraper.get_all_channels(save_to_db=True, fetch_member_count=False),
                timeout=settings.operation_timeout
            )
            return channels
        
        # Get from database
        query = select(Channel)
        if search:
            query = query.filter(
                (Channel.title.contains(search)) | 
                (Channel.username.contains(search))
            )
        
        result = await db.execute(query)
        channels = result.scalars().all()
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
    
    except asyncio.TimeoutError:
        client_ip = request.client.host if request else "unknown"
        logger.error(f"Timeout listing channels from {client_ip}")
        raise HTTPException(status_code=408, detail="Operation timed out")
    except Exception as e:
        client_ip = request.client.host if request else "unknown"
        logger.error(f"Error listing channels from {client_ip}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@channels_router.get("/{channel_id}")
async def get_channel(channel_id: str, request: Request):
    """Get specific channel details"""
    try:
        # Validate channel ID format
        is_valid, error_msg = validate_channel_id(channel_id)
        if not is_valid:
            logger.warning(f"Invalid channel ID format from {request.client.host}: {channel_id}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Get channel with timeout
        client = await session_manager.get_client()
        scraper = ChannelScraper(client)
        
        channel = await asyncio.wait_for(
            scraper.get_channel_by_id(channel_id),
            timeout=settings.operation_timeout
        )
        
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        return channel
    
    except asyncio.TimeoutError:
        logger.error(f"Timeout getting channel {channel_id} from {request.client.host}")
        raise HTTPException(status_code=408, detail="Operation timed out")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting channel {channel_id} from {request.client.host}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# Job Routes
@jobs_router.post("/clone", response_model=CloneJobResponse)
async def create_clone_job(
    job_data: CloneJobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """Create a new clone job with validation"""
    try:
        # Additional validation beyond Pydantic
        is_valid, error_msg = validate_channel_id(job_data.source_channel)
        if not is_valid:
            client_ip = request.client.host if request else "unknown"
            logger.warning(f"Invalid source channel from {client_ip}: {job_data.source_channel}")
            raise HTTPException(status_code=400, detail=f"Invalid source channel: {error_msg}")
        
        is_valid, error_msg = validate_channel_id(job_data.target_channel)
        if not is_valid:
            client_ip = request.client.host if request else "unknown"
            logger.warning(f"Invalid target channel from {client_ip}: {job_data.target_channel}")
            raise HTTPException(status_code=400, detail=f"Invalid target channel: {error_msg}")
        
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
        await db.commit()
        await db.refresh(job)
        
        client_ip = request.client.host if request else "unknown"
        logger.info(f"Clone job created: {job_id} from {client_ip}")
        
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
    
    except HTTPException:
        raise
    except ValueError as e:
        # Pydantic validation error
        client_ip = request.client.host if request else "unknown"
        logger.warning(f"Validation error from {client_ip}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        client_ip = request.client.host if request else "unknown"
        logger.error(f"Error creating clone job from {client_ip}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create job")

@jobs_router.get("/list", response_model=List[CloneJobResponse])
async def list_jobs(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all clone jobs"""
    query = select(CloneJob)
    if status:
        query = query.filter(CloneJob.status == status)
    
    query = query.order_by(CloneJob.created_at.desc())
    result = await db.execute(query)
    jobs = result.scalars().all()
    return jobs

@jobs_router.get("/{job_id}", response_model=CloneJobResponse)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db), request: Request = None):
    """Get job details"""
    try:
        # Validate job ID format
        is_valid, error_msg = validate_job_id(job_id)
        if not is_valid:
            client_ip = request.client.host if request else "unknown"
            logger.warning(f"Invalid job ID from {client_ip}: {job_id}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        result = await db.execute(select(CloneJob).filter(CloneJob.job_id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    
    except HTTPException:
        raise
    except Exception as e:
        client_ip = request.client.host if request else "unknown"
        logger.error(f"Error getting job {job_id} from {client_ip}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@jobs_router.post("/{job_id}/stop")
async def stop_job(job_id: str, db: AsyncSession = Depends(get_db), request: Request = None):
    """Stop a running job"""
    try:
        # Validate job ID format
        is_valid, error_msg = validate_job_id(job_id)
        if not is_valid:
            client_ip = request.client.host if request else "unknown"
            logger.warning(f"Invalid job ID from {client_ip}: {job_id}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        result = await db.execute(select(CloneJob).filter(CloneJob.job_id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job.status = "stopped"
        await db.commit()
        
        if job.auto_sync:
            sync_worker.remove_job(job_id)
        
        client_ip = request.client.host if request else "unknown"
        logger.info(f"Job {job_id} stopped by {client_ip}")
        
        return {"message": "Job stopped"}
    
    except HTTPException:
        raise
    except Exception as e:
        client_ip = request.client.host if request else "unknown"
        logger.error(f"Error stopping job {job_id} from {client_ip}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@jobs_router.delete("/{job_id}")
async def delete_job(job_id: str, db: AsyncSession = Depends(get_db), request: Request = None):
    """Delete a job"""
    try:
        # Validate job ID format
        is_valid, error_msg = validate_job_id(job_id)
        if not is_valid:
            client_ip = request.client.host if request else "unknown"
            logger.warning(f"Invalid job ID from {client_ip}: {job_id}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        result = await db.execute(select(CloneJob).filter(CloneJob.job_id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Stop if running
        if job.auto_sync:
            sync_worker.remove_job(job_id)
        
        # Cleanup files
        storage_manager.cleanup_job(job_id)
        
        # Delete from database
        await db.delete(job)
        await db.commit()
        
        client_ip = request.client.host if request else "unknown"
        logger.info(f"Job {job_id} deleted by {client_ip}")
        
        return {"message": "Job deleted"}
    
    except HTTPException:
        raise
    except Exception as e:
        client_ip = request.client.host if request else "unknown"
        logger.error(f"Error deleting job {job_id} from {client_ip}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# System Routes
@system_router.get("/health")
async def health_check():
    """Health check endpoint for Docker and load balancers"""
    try:
        # Check if session manager is initialized
        if not hasattr(session_manager, 'clients'):
            return {"status": "unhealthy", "reason": "Session manager not initialized"}
        
        # Basic health check - service is running
        return {
            "status": "healthy",
            "service": "telegram-automation",
            "accounts": len(session_manager.clients) if session_manager.clients else 0
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "reason": str(e)}

@system_router.get("/stats")
async def system_stats(db: AsyncSession = Depends(get_db), request: Request = None):
    """Get system statistics"""
    try:
        # Check if any accounts are logged in
        if not session_manager.clients:
            # No accounts - clear stale channels and return zeros
            try:
                await db.execute(delete(Channel))
                await db.commit()
            except Exception as db_error:
                logger.error(f"Error clearing channels in stats: {db_error}")
                await db.rollback()
            
            total_channels = 0
        else:
            result = await db.execute(select(Channel))
            total_channels = len(result.scalars().all())
        
        result = await db.execute(select(CloneJob))
        total_jobs = len(result.scalars().all())
        
        result = await db.execute(
            select(CloneJob).filter(CloneJob.status.in_(["running", "pending"]))
        )
        active_jobs = len(result.scalars().all())
        
        disk_usage = storage_manager.get_disk_usage()
        
        return {
            "channels": total_channels,
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "disk_usage": disk_usage
        }
    
    except Exception as e:
        client_ip = request.client.host if request else "unknown"
        logger.error(f"Error getting system stats from {client_ip}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@system_router.post("/cleanup")
async def cleanup_storage(request: Request = None):
    """Cleanup old files"""
    try:
        storage_manager.cleanup_old_files(max_age_hours=24)
        
        client_ip = request.client.host if request else "unknown"
        logger.info(f"Storage cleanup initiated from {client_ip}")
        
        return {"message": "Cleanup completed"}
    
    except Exception as e:
        client_ip = request.client.host if request else "unknown"
        logger.error(f"Error during cleanup from {client_ip}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# Account Management Routes
@accounts_router.get("/list")
async def list_accounts(request: Request = None):
    """List all logged in accounts"""
    try:
        accounts = await telegram_auth_manager.get_logged_accounts()
        return {"accounts": accounts}
    except Exception as e:
        client_ip = request.client.host if request else "unknown"
        logger.error(f"Error listing accounts from {client_ip}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@accounts_router.post("/login/send-code")
async def send_login_code(request_data: TelegramLoginRequest, request: Request = None):
    """Send verification code to phone"""
    try:
        result = await asyncio.wait_for(
            telegram_auth_manager.send_code(
                request_data.phone,
                request_data.api_id,
                request_data.api_hash
            ),
            timeout=settings.operation_timeout
        )
        return result
    
    except asyncio.TimeoutError:
        client_ip = request.client.host if request else "unknown"
        logger.error(f"Timeout sending code to {request_data.phone} from {client_ip}")
        raise HTTPException(status_code=408, detail="Operation timed out")
    except Exception as e:
        client_ip = request.client.host if request else "unknown"
        logger.error(f"Error sending code from {client_ip}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to send verification code")

@accounts_router.post("/login/verify-code")
async def verify_login_code(request_data: TelegramCodeRequest, request: Request = None):
    """Verify the code and complete login"""
    try:
        result = await asyncio.wait_for(
            telegram_auth_manager.verify_code(
                request_data.phone,
                request_data.code
            ),
            timeout=settings.operation_timeout
        )
        return result
    
    except asyncio.TimeoutError:
        client_ip = request.client.host if request else "unknown"
        logger.error(f"Timeout verifying code for {request_data.phone} from {client_ip}")
        raise HTTPException(status_code=408, detail="Operation timed out")
    except Exception as e:
        client_ip = request.client.host if request else "unknown"
        logger.error(f"Error verifying code from {client_ip}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to verify code")

@accounts_router.post("/login/verify-password")
async def verify_2fa_password(request_data: TelegramPasswordRequest, request: Request = None):
    """Verify 2FA password"""
    try:
        result = await asyncio.wait_for(
            telegram_auth_manager.verify_password(
                request_data.phone,
                request_data.password
            ),
            timeout=settings.operation_timeout
        )
        return result
    
    except asyncio.TimeoutError:
        client_ip = request.client.host if request else "unknown"
        logger.error(f"Timeout verifying password for {request_data.phone} from {client_ip}")
        raise HTTPException(status_code=408, detail="Operation timed out")
    except Exception as e:
        client_ip = request.client.host if request else "unknown"
        logger.error(f"Error verifying password from {client_ip}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to verify password")

@accounts_router.post("/logout")
async def logout_account(request_data: TelegramLogoutRequest, request: Request = None):
    """Logout account and remove session"""
    try:
        result = await asyncio.wait_for(
            telegram_auth_manager.logout_account(request_data.phone),
            timeout=settings.operation_timeout
        )
        
        client_ip = request.client.host if request else "unknown"
        logger.info(f"Account logged out from {client_ip}")
        
        return result
    
    except asyncio.TimeoutError:
        client_ip = request.client.host if request else "unknown"
        logger.error(f"Timeout logging out {request_data.phone} from {client_ip}")
        raise HTTPException(status_code=408, detail="Operation timed out")
    except Exception as e:
        client_ip = request.client.host if request else "unknown"
        logger.error(f"Error logging out from {client_ip}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to logout")

# Background task with async context manager
async def run_clone_job(
    job_id: str,
    source_channel: str,
    target_channel: str,
    start_message_id: Optional[int],
    limit: Optional[int],
    auto_sync: bool
):
    """Run clone job in background with proper async context and timeout"""
    
    async with get_db_context() as db:
        try:
            # Update status to running
            result = await db.execute(
                update(CloneJob)
                .filter(CloneJob.job_id == job_id, CloneJob.status == "pending")
                .values(status="running")
            )
            await db.commit()
            
            if result.rowcount == 0:
                logger.error(f"Job {job_id} not found or not in pending state")
                return
            
            # Get client and cloner
            client = await session_manager.get_client()
            cloner = MessageCloner(client)
            
            # Clone messages with timeout
            processed = 0
            clone_operation = cloner.clone_messages(
                source_channel,
                target_channel,
                start_id=start_message_id,
                limit=limit,
                job_id=job_id
            )
            
            # Wrap the entire clone operation with timeout
            try:
                async for result in asyncio.wait_for(
                    clone_operation,
                    timeout=settings.clone_timeout
                ):
                    if result["status"] == "success":
                        processed += 1
                        # Atomic update
                        await db.execute(
                            update(CloneJob)
                            .filter(CloneJob.job_id == job_id)
                            .values(processed_messages=processed)
                        )
                        await db.commit()
            
            except asyncio.TimeoutError:
                logger.error(f"Job {job_id} timed out after {settings.clone_timeout} seconds")
                await db.execute(
                    update(CloneJob)
                    .filter(CloneJob.job_id == job_id)
                    .values(
                        status="failed",
                        error_message=f"Operation timed out after {settings.clone_timeout} seconds",
                        updated_at=datetime.utcnow()
                    )
                )
                await db.commit()
                return
            
            # Mark as completed
            await db.execute(
                update(CloneJob)
                .filter(CloneJob.job_id == job_id)
                .values(status="completed", updated_at=datetime.utcnow())
            )
            await db.commit()
            
            # Add to sync worker if auto_sync
            if auto_sync:
                sync_worker.add_job(job_id)
            
            # Cleanup job files
            storage_manager.cleanup_job(job_id)
            
        except asyncio.CancelledError:
            logger.warning(f"Job {job_id} was cancelled")
            await db.execute(
                update(CloneJob)
                .filter(CloneJob.job_id == job_id)
                .values(status="paused", updated_at=datetime.utcnow())
            )
            await db.commit()
            raise
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            await db.execute(
                update(CloneJob)
                .filter(CloneJob.job_id == job_id)
                .values(
                    status="failed",
                    error_message=str(e),
                    updated_at=datetime.utcnow()
                )
            )
            await db.commit()
