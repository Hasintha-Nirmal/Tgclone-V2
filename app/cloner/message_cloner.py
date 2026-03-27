from telethon import TelegramClient
from telethon.tl.types import Message, MessageMediaPhoto, MessageMediaDocument
from telethon.errors import FloodWaitError
from typing import Optional, AsyncGenerator
from pathlib import Path
from app.utils.logger import logger
from app.utils.storage import storage_manager
from app.utils.rate_limiter import global_rate_limiter
from config.settings import settings
import asyncio
from datetime import datetime, timedelta
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)


class MessageCloner:
    def __init__(self, client: TelegramClient):
        self.client = client
    
    async def clone_messages(
        self,
        source_channel: str,
        target_channel: str,
        start_id: Optional[int] = None,
        limit: Optional[int] = None,
        job_id: Optional[str] = None,
        timeout_seconds: int = 3600
    ) -> AsyncGenerator[dict, None]:
        """Clone messages from source to target channel with timeout and error handling"""
        
        try:
            # Verify client is connected
            if not self.client.is_connected():
                await self.client.connect()
            
            # Convert channel IDs to int, handling both numeric and username formats
            try:
                source_entity = await self.client.get_entity(int(source_channel))
            except ValueError:
                # Not a numeric ID, try as username
                source_entity = await self.client.get_entity(source_channel)
            
            try:
                target_entity = await self.client.get_entity(int(target_channel))
            except ValueError:
                # Not a numeric ID, try as username
                target_entity = await self.client.get_entity(target_channel)
            
            logger.info(f"Starting clone from {source_channel} to {target_channel}")
            
            message_count = 0
            async for message in self.client.iter_messages(
                source_entity,
                min_id=start_id if start_id else 0,
                limit=limit,
                reverse=True
            ):
                try:
                    # Check hourly rate limit using global rate limiter
                    await global_rate_limiter.check_and_wait()
                    
                    result = await self._clone_single_message_with_retry(
                        message, 
                        target_entity, 
                        job_id
                    )
                    message_count += 1
                    
                    # Record this message in global rate limiter
                    await global_rate_limiter.record_message(job_id=job_id)
                    
                    yield {
                        "status": "success",
                        "message_id": message.id,
                        "count": message_count,
                        "has_media": bool(message.media)
                    }
                    
                except FloodWaitError as e:
                    logger.warning(f"Flood wait for message {message.id}: {e.seconds}s. Pausing...")
                    await asyncio.sleep(e.seconds + 1)
                    # Retry this message
                    try:
                        result = await self._clone_single_message(message, target_entity, job_id)
                        message_count += 1
                        await global_rate_limiter.record_message(job_id=job_id)
                        yield {
                            "status": "success",
                            "message_id": message.id,
                            "count": message_count,
                            "has_media": bool(message.media)
                        }
                    except Exception as retry_error:
                        logger.error(f"Failed to clone message {message.id} after flood wait: {retry_error}")
                        # Yield error instead of raising - continue processing
                        yield {
                            "status": "error",
                            "message_id": message.id,
                            "error": str(retry_error)
                        }
                
                except Exception as e:
                    # Log error with message context and yield error result
                    logger.error(f"Failed to clone message {message.id} from job {job_id}: {e}", exc_info=True)
                    # Yield error instead of raising - continue processing remaining messages
                    yield {
                        "status": "error",
                        "message_id": message.id,
                        "error": str(e)
                    }
                
                # Smart delay to avoid flood and protect account
                if message.media:
                    await asyncio.sleep(settings.delay_between_media)
                else:
                    await asyncio.sleep(settings.delay_between_messages)
                
                # Extra break every N messages to avoid detection
                if message_count % settings.break_every_n_messages == 0:
                    logger.info(f"Processed {message_count} messages, taking a {settings.break_duration}s break")
                    await asyncio.sleep(settings.break_duration)
            
            logger.info(f"Cloned {message_count} messages")
        
        except Exception as e:
            # Log critical error with job context
            logger.error(f"Clone operation failed for job {job_id}: {e}", exc_info=True)
            # Yield final error result
            yield {
                "status": "error",
                "message_id": None,
                "error": f"Clone operation failed: {str(e)}"
            }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((OSError, ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logger.level)
    )
    async def _clone_single_message_with_retry(
        self,
        message: Message,
        target_entity,
        job_id: Optional[str] = None
    ):
        """Clone a single message with automatic retry on transient failures"""
        return await self._clone_single_message(message, target_entity, job_id)
    
    async def _clone_single_message(
        self,
        message: Message,
        target_entity,
        job_id: Optional[str] = None
    ):
        """Clone a single message with media"""
        
        # Text-only message
        if not message.media:
            await self.client.send_message(
                target_entity,
                message.text or "",
                formatting_entities=message.entities
            )
            return
        
        # Message with media
        file_path = None
        upload_success = False
        
        try:
            # Download media
            logger.debug(f"Starting file download for message {message.id}")
            file_path = await self._download_media(message, job_id)
            
            if file_path and file_path.exists():
                logger.info(f"File download complete: {file_path}")
                
                # Upload to target - use absolute path
                logger.debug(f"Starting file upload for message {message.id}")
                result = await self.client.send_file(
                    target_entity,
                    str(file_path.absolute()),
                    caption=message.text or "",
                    formatting_entities=message.entities
                )
                
                # Verify upload succeeded
                if result and result.id:
                    upload_success = True
                    logger.info(f"Upload verified: message {result.id}")
                else:
                    logger.error(f"Upload verification failed for {file_path} - no result ID")
                    raise Exception("Upload verification failed: no result ID returned")
            else:
                logger.error(f"File not found or download failed: {file_path}")
                raise Exception(f"File download failed: {file_path}")
            
        except Exception as e:
            logger.error(f"Error cloning message with media: {e}")
            # Don't delete file on failure - keep for retry
            raise
        
        finally:
            # Only cleanup on successful upload
            if file_path and settings.auto_delete_files:
                if upload_success:
                    try:
                        if file_path.exists():
                            logger.debug(f"Cleaning up file after successful upload: {file_path}")
                            storage_manager.cleanup_file(file_path)
                        else:
                            logger.warning(f"File already removed: {file_path}")
                    except Exception as cleanup_error:
                        logger.error(f"Error during file cleanup: {cleanup_error}")
                else:
                    logger.info(f"Retaining file due to upload failure: {file_path}")
            elif file_path:
                logger.debug(f"Auto-delete disabled, file retained: {file_path}")
    
    async def _download_media(
        self,
        message: Message,
        job_id: Optional[str] = None
    ) -> Optional[Path]:
        """Download media from message"""
        
        if not message.media:
            return None
        
        try:
            # Generate filename
            filename = self._get_media_filename(message)
            file_path = storage_manager.get_download_path(filename, job_id)
            
            # Download
            logger.info(f"Downloading media: {filename} for message {message.id}")
            downloaded_path = await self.client.download_media(
                message.media,
                file=str(file_path)
            )
            
            if downloaded_path:
                logger.debug(f"Download complete: {downloaded_path}")
                return Path(downloaded_path)
            else:
                logger.error(f"Download returned None for message {message.id}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to download media for message {message.id}: {e}")
            return None
    
    def _get_media_filename(self, message: Message) -> str:
        """Generate filename for media"""
        
        if isinstance(message.media, MessageMediaPhoto):
            return f"photo_{message.id}.jpg"
        elif isinstance(message.media, MessageMediaDocument):
            doc = message.media.document
            # Try to get original filename
            for attr in doc.attributes:
                if hasattr(attr, 'file_name'):
                    return f"{message.id}_{attr.file_name}"
            return f"document_{message.id}"
        else:
            return f"media_{message.id}"
    
    async def get_latest_message_id(self, channel: str) -> Optional[int]:
        """Get the latest message ID from a channel"""
        try:
            # Verify client is connected
            if not self.client.is_connected():
                await self.client.connect()
            
            # Convert channel ID to int, handling both numeric and username formats
            try:
                entity = await self.client.get_entity(int(channel))
            except ValueError:
                # Not a numeric ID, try as username
                entity = await self.client.get_entity(channel)
            async for message in self.client.iter_messages(entity, limit=1):
                return message.id
        except Exception as e:
            logger.error(f"Failed to get latest message ID for {channel}: {e}")
        return None
