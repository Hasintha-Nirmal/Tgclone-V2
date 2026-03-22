from telethon import TelegramClient
from telethon.errors import FloodWaitError
from typing import List, Optional
from pathlib import Path
from app.utils.logger import logger
from config.settings import settings
import asyncio
import random

class MultiAccountUploader:
    def __init__(self, clients: List[TelegramClient]):
        self.clients = clients
        self.current_index = 0
        self.flood_wait_until = {}  # Track flood wait per client
    
    def _get_next_available_client(self) -> Optional[TelegramClient]:
        """Get next client that's not in flood wait"""
        import time
        now = time.time()
        
        for _ in range(len(self.clients)):
            client = self.clients[self.current_index]
            client_id = id(client)
            
            # Check if client is available
            if client_id not in self.flood_wait_until or self.flood_wait_until[client_id] < now:
                return client
            
            # Move to next client
            self.current_index = (self.current_index + 1) % len(self.clients)
        
        return None
    
    async def upload_file(
        self,
        file_path: Path,
        target_channel: str,
        caption: Optional[str] = None,
        max_retries: int = None
    ) -> bool:
        """Upload file with automatic retry and account rotation"""
        
        if max_retries is None:
            max_retries = settings.max_retries
        
        for attempt in range(max_retries):
            client = self._get_next_available_client()
            
            if not client:
                # All clients in flood wait
                wait_time = min(self.flood_wait_until.values()) - time.time()
                logger.warning(f"All clients in flood wait. Waiting {wait_time}s")
                await asyncio.sleep(wait_time + 1)
                continue
            
            try:
                entity = await client.get_entity(int(target_channel))
                await client.send_file(
                    entity,
                    str(file_path),
                    caption=caption
                )
                
                logger.info(f"Uploaded {file_path.name} successfully")
                
                # Rotate to next client
                self.current_index = (self.current_index + 1) % len(self.clients)
                return True
                
            except FloodWaitError as e:
                wait_time = e.seconds * settings.flood_wait_multiplier
                logger.warning(f"FloodWait: {wait_time}s for client {self.current_index}")
                
                import time
                self.flood_wait_until[id(client)] = time.time() + wait_time
                
                # Try next client
                self.current_index = (self.current_index + 1) % len(self.clients)
                
            except Exception as e:
                logger.error(f"Upload failed (attempt {attempt + 1}): {e}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    return False
        
        return False
    
    async def upload_batch(
        self,
        files: List[Path],
        target_channel: str,
        captions: Optional[List[str]] = None
    ) -> dict:
        """Upload multiple files"""
        
        results = {
            "success": 0,
            "failed": 0,
            "total": len(files)
        }
        
        for i, file_path in enumerate(files):
            caption = captions[i] if captions and i < len(captions) else None
            
            success = await self.upload_file(file_path, target_channel, caption)
            
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1
            
            # Small delay between uploads
            await asyncio.sleep(random.uniform(1, 3))
        
        return results
