from telethon import TelegramClient
from telethon.tl.types import Message, MessageMediaPhoto, MessageMediaDocument
from telethon.errors import FloodWaitError, NetworkError, TimeoutError as TelethonTimeoutError
from typing import Optional, AsyncGenerator
from pathlib import Path
from app.utils.logger import logger
from app.utils.storage import storage_manager
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
        self.message_timestamps = []  # Track message times for rate limiting
    
    async def clone_messages(
        self,
        source_channel: str,
        target_channel: str,
        start_id: Optional[int] = None,
        limit: Optional[int] = None,
        job_id: Optional[str] = None,
        timeout_seconds: int = 3600
    ) -> AsyncGenerator[dict, None]:
        """Clone messages from source to target channel with timeout"""
        
        try:
            source_entity = await self.client.get_entity(int(source_channel))
            target_entity = await self.client.get_entity(int(target_channel))
            
            logger.info(f"Starting clone from {source_channel} to {target_channel}")
            
            message_count = 0
            async for message in self.client.iter_messages(
                source_entity,
                min_id=start_id if start_id else 0,
                limit=limit,
                reverse=True
            ):
                try:
                    # Check hourly rate limit
                    await self._check_rate_limit()
                    
                    result = await self._clone_single_message_with_retry(
                        message, 
                        target_entity, 
                        job_id
                    )
                    message_count += 1
                    
                    # Track this message for rate limiting
                    self.message_timestamps.append(datetime.utcnow())
                    
                    yield {
                        "status": "success",
                        "message_id": message.id,
                        "count": message_count,
                        "has_media": bool(message.media)
                    }
                    
                except FloodWaitError as e:
                    logger.warning(f"Flood wait: {e.seconds}s. Pausing...")
                    await asyncio.sleep(e.seconds + 1)
                    # Retry this message
                    try:
                        result = await self._clone_single_message(message, target_entity, job_id)
                        message_count += 1
                        self.message_timestamps.append(datetime.utcnow())
                        yield {
                            "status": "success",
                            "message_id": message.id,
                            "count": message_count,
                            "has_media": bool(message.media)
                        }
                    except Exception as retry_error:
                        logger.error(f"Failed to clone message {message.id} after flood wait: {retry_error}")
                        yield {
                            "status": "error",
                            "message_id": message.id,
                            "error": str(retry_error)
                        }
                except Exception as e:
                    logger.error(f"Failed to clone message {message.id}: {e}")
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
            logger.error(f"Clone operation failed: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((NetworkError, TelethonTimeoutError, ConnectionError)),
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
        try:
            # Download media
            file_path = await self._download_media(message, job_id)
            
            if file_path and file_path.exists():
                # Upload to target - use absolute path
                await self.client.send_file(
                    target_entity,
                    str(file_path.absolute()),
                    caption=message.text or "",
                    formatting_entities=message.entities
                )
                
                # Auto-delete if enabled
                if settings.auto_delete_files:
                    storage_manager.cleanup_file(file_path)
            else:
                logger.error(f"File not found or download failed: {file_path}")
            
        except Exception as e:
            logger.error(f"Error cloning message with media: {e}")
            raise
        finally:
            # Ensure cleanup
            if file_path and settings.auto_delete_files and file_path.exists():
                storage_manager.cleanup_file(file_path)
    
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
            logger.info(f"Downloading media: {filename}")
            downloaded_path = await self.client.download_media(
                message.media,
                file=str(file_path)
            )
            
            return Path(downloaded_path) if downloaded_path else None
            
        except Exception as e:
            logger.error(f"Failed to download media: {e}")
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
            entity = await self.client.get_entity(int(channel))
            async for message in self.client.iter_messages(entity, limit=1):
                return message.id
        except Exception as e:
            logger.error(f"Failed to get latest message ID: {e}")
        return None
    
    async def _check_rate_limit(self):
        """Check if we're within safe rate limits"""
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        
        # Remove timestamps older than 1 hour
        self.message_timestamps = [
            ts for ts in self.message_timestamps 
            if ts > one_hour_ago
        ]
        
        # Check if we've hit the hourly limit
        if len(self.message_timestamps) >= settings.max_messages_per_hour:
            wait_time = 3600  # Wait 1 hour
            logger.warning(
                f"Hourly rate limit reached ({settings.max_messages_per_hour} messages/hour). "
                f"Waiting {wait_time} seconds to protect account..."
            )
            await asyncio.sleep(wait_time)
            self.message_timestamps.clear()
