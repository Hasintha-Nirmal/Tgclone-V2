from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

from app.utils.database import get_db, Channel, CloneJob, SyncState
from app.auth.session_manager import session_manager
from app.scraper.channel_scraper import ChannelScraper
from app.cloner.message_cloner import MessageCloner
from app.worker.sync_worker import sync_worker
from app.utils.storage import storage_manager
from app.utils.logger import logger

# Routers
auth_router = APIRouter()
channels_router = APIRouter()
jobs_router = APIRouter()
system_router = APIRouter()

# Models
class ChannelResponse(BaseModel):
    channel_id: str
    title: str
    username: Optional[str]
    member_count: Optional[int]
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
        if refresh:
            client = await session_manager.get_client()
            scraper = ChannelScraper(client)
            channels = await scraper.get_all_channels(save_to_db=True)
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
    """Create a new clone job"""
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
    except Exception as e:
        logger.error(f"Error creating clone job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

# Background task
async def run_clone_job(
    job_id: str,
    source_channel: str,
    target_channel: str,
    start_message_id: Optional[int],
    limit: Optional[int],
    auto_sync: bool
):
    """Run clone job in background"""
    from app.utils.database import SessionLocal
    
    db = SessionLocal()
    
    try:
        # Update status
        job = db.query(CloneJob).filter(CloneJob.job_id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return
            
        job.status = "running"
        db.commit()
        
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
                job.processed_messages = processed
                db.commit()
        
        # Update final status
        job.status = "completed"
        job.updated_at = datetime.utcnow()
        db.commit()
        
        # Add to sync worker if auto_sync
        if auto_sync:
            sync_worker.add_job(job_id)
        
        # Cleanup job files
        storage_manager.cleanup_job(job_id)
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        try:
            job = db.query(CloneJob).filter(CloneJob.job_id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(e)
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update job status: {db_error}")
    finally:
        db.close()
