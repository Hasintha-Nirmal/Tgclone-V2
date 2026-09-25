from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import Channel, Chat
from typing import List, Dict, Optional
from app.utils.logger import logger
from app.utils import db_ops

class ChannelScraper:
    def __init__(self, client: TelegramClient):
        self.client = client
    
    async def get_all_channels(self, save_to_db: bool = True, fetch_member_count: bool = False) -> List[Dict]:
        """Fetch all joined channels
        
        Args:
            save_to_db: Save channels to database
            fetch_member_count: Fetch member count (slow, makes extra API calls)
        """
        channels = []
        
        try:
            async for dialog in self.client.iter_dialogs():
                if isinstance(dialog.entity, Channel):
                    channel_info = await self._extract_channel_info(dialog.entity, fetch_member_count)
                    channels.append(channel_info)
                    
                    if save_to_db:
                        await self._save_channel_to_db(channel_info)
            
            logger.info(f"Found {len(channels)} channels")
            return channels
            
        except Exception as e:
            logger.error(f"Error fetching channels: {e}")
            raise
    
    async def _extract_channel_info(self, channel: Channel, fetch_member_count: bool = False) -> Dict:
        """Extract detailed channel information
        
        Args:
            channel: Channel entity
            fetch_member_count: Whether to fetch member count (requires extra API call)
        """
        member_count = None
        
        # Only fetch member count if explicitly requested (slow operation)
        if fetch_member_count:
            try:
                full_channel = await self.client(GetFullChannelRequest(channel))
                member_count = full_channel.full_chat.participants_count
            except:
                member_count = None
        
        # Format channel ID to -100 format
        channel_id = f"-100{channel.id}"
        
        return {
            "channel_id": channel_id,
            "title": channel.title,
            "username": channel.username,
            "member_count": member_count,
            "is_private": not channel.username,
            "is_megagroup": channel.megagroup,
            "is_broadcast": channel.broadcast,
            "access_hash": channel.access_hash
        }
    
    async def _save_channel_to_db(self, channel_info: Dict):
        """Save channel to MongoDB"""
        try:
            await db_ops.save_channel(channel_info)
        except Exception as e:
            logger.error(f"Error saving channel to DB: {e}")
    
    async def search_channels(self, query: str) -> List[Dict]:
        """Search channels by name or username"""
        all_channels = await self.get_all_channels(save_to_db=False)
        query_lower = query.lower()
        
        return [
            ch for ch in all_channels
            if query_lower in ch["title"].lower() or 
               (ch["username"] and query_lower in ch["username"].lower())
        ]
    
    async def get_channel_by_id(self, channel_id: str) -> Optional[Dict]:
        """Get specific channel by ID"""
        try:
            entity = await self.client.get_entity(int(channel_id))
            if isinstance(entity, Channel):
                return await self._extract_channel_info(entity)
        except Exception as e:
            logger.error(f"Error getting channel {channel_id}: {e}")
        return None
