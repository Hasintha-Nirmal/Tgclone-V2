from telethon import TelegramClient
from telethon.sessions import StringSession
from typing import Dict, Optional, List
from pathlib import Path
from config.settings import settings
from app.utils.logger import logger
import asyncio

class SessionManager:
    def __init__(self):
        self.clients: Dict[str, TelegramClient] = {}
        self.session_dir = Path("sessions")
        self.session_dir.mkdir(exist_ok=True)
    
    async def create_client(
        self, 
        phone: str, 
        api_id: int, 
        api_hash: str,
        session_name: Optional[str] = None
    ) -> TelegramClient:
        """Create and connect a Telegram client"""
        if not session_name:
            session_name = phone.replace("+", "")
        
        session_file = self.session_dir / f"{session_name}.session"
        
        client = TelegramClient(str(session_file), api_id, api_hash)
        
        try:
            await client.connect()
            
            if not await client.is_user_authorized():
                logger.info(f"Authorization required for {phone}")
                await client.send_code_request(phone)
                # Note: In production, handle code input via web interface
                logger.warning(f"Please complete authorization for {phone} manually")
            else:
                logger.info(f"Client {phone} already authorized")
            
            self.clients[phone] = client
            return client
            
        except Exception as e:
            logger.error(f"Failed to create client for {phone}: {e}")
            raise
    
    async def get_client(self, phone: Optional[str] = None) -> TelegramClient:
        """Get existing client or create primary client"""
        if phone and phone in self.clients:
            return self.clients[phone]
        
        # Return primary client
        if settings.telegram_phone in self.clients:
            return self.clients[settings.telegram_phone]
        
        # Create primary client
        return await self.create_client(
            settings.telegram_phone,
            settings.telegram_api_id,
            settings.telegram_api_hash
        )
    
    async def initialize_all_accounts(self):
        """Initialize all configured accounts"""
        accounts = [
            (settings.telegram_phone, settings.telegram_api_id, settings.telegram_api_hash)
        ]
        
        if settings.telegram_phone_2 and settings.telegram_api_id_2:
            accounts.append(
                (settings.telegram_phone_2, settings.telegram_api_id_2, settings.telegram_api_hash_2)
            )
        
        for phone, api_id, api_hash in accounts:
            try:
                await self.create_client(phone, api_id, api_hash)
            except Exception as e:
                logger.error(f"Failed to initialize account {phone}: {e}")
    
    def get_available_clients(self) -> List[TelegramClient]:
        """Get list of all connected clients"""
        return list(self.clients.values())
    
    async def disconnect_all(self):
        """Disconnect all clients"""
        for phone, client in self.clients.items():
            try:
                await client.disconnect()
                logger.info(f"Disconnected client: {phone}")
            except Exception as e:
                logger.error(f"Error disconnecting {phone}: {e}")
        self.clients.clear()

session_manager = SessionManager()
