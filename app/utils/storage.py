import os
import shutil
from pathlib import Path
from typing import Optional
from config.settings import settings
from app.utils.logger import logger

class StorageManager:
    def __init__(self):
        self.temp_dir = Path(settings.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def get_download_path(self, filename: str, job_id: Optional[str] = None) -> Path:
        """Get path for downloading file"""
        if job_id:
            path = self.temp_dir / job_id
            path.mkdir(parents=True, exist_ok=True)
            return path / filename
        return self.temp_dir / filename
    
    def cleanup_file(self, filepath: Path) -> bool:
        """Delete a single file"""
        try:
            if filepath.exists() and filepath.is_file():
                filepath.unlink()
                logger.info(f"Deleted file: {filepath}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete {filepath}: {e}")
        return False
    
    def cleanup_job(self, job_id: str) -> bool:
        """Delete all files for a job"""
        try:
            job_dir = self.temp_dir / job_id
            if job_dir.exists() and job_dir.is_dir():
                shutil.rmtree(job_dir)
                logger.info(f"Cleaned up job directory: {job_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to cleanup job {job_id}: {e}")
        return False
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """Clean up files older than specified hours"""
        import time
        now = time.time()
        cutoff = now - (max_age_hours * 3600)
        
        for item in self.temp_dir.rglob("*"):
            if item.is_file():
                try:
                    if item.stat().st_mtime < cutoff:
                        item.unlink()
                        logger.info(f"Cleaned up old file: {item}")
                except Exception as e:
                    logger.error(f"Failed to cleanup {item}: {e}")
    
    def get_disk_usage(self) -> dict:
        """Get disk usage statistics"""
        import psutil
        usage = psutil.disk_usage(str(self.temp_dir))
        return {
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "percent": usage.percent
        }

storage_manager = StorageManager()
