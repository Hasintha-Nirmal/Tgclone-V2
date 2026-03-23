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
                # Don't try to send code during startup - let web handle it
                logger.warning(f"Session exists but not authorized for {phone} - login via web")
                await client.disconnect()
                return None
            else:
                logger.info(f"Client {phone} already authorized")
            
            self.clients[phone] = client
            return client
            
        except Exception as e:
            logger.error(f"Failed to create client for {phone}: {e}")
            await client.disconnect()
            return None
    
    async def get_client(self, phone: Optional[str] = None) -> TelegramClient:
        """Get existing client or create primary client"""
        # If specific phone requested and exists, return it
        if phone and phone in self.clients:
            client = self.clients[phone]
            if await client.is_user_authorized():
                return client
        
        # Return any authorized client
        for phone, client in self.clients.items():
            try:
                if await client.is_user_authorized():
                    logger.info(f"Using authorized client: {phone}")
                    return client
            except:
                continue
        
        # Try to create/use primary client from .env (if configured)
        if settings.telegram_phone and settings.telegram_api_id and settings.telegram_api_hash:
            if settings.telegram_phone in self.clients:
                client = self.clients[settings.telegram_phone]
                if await client.is_user_authorized():
                    return client
            
            # Create primary client
            return await self.create_client(
                settings.telegram_phone,
                settings.telegram_api_id,
                settings.telegram_api_hash
            )
        
        # No clients available
        raise Exception("No authorized Telegram accounts available. Please login via the Accounts tab.")
    
    async def initialize_all_accounts(self):
        """Initialize all configured accounts from .env (if any)"""
        accounts = []
        
        # Add primary account if configured
        if settings.telegram_phone and settings.telegram_api_id and settings.telegram_api_hash:
            accounts.append(
                (settings.telegram_phone, settings.telegram_api_id, settings.telegram_api_hash)
            )
        
        # Add secondary account if configured
        if settings.telegram_phone_2 and settings.telegram_api_id_2 and settings.telegram_api_hash_2:
            accounts.append(
                (settings.telegram_phone_2, settings.telegram_api_id_2, settings.telegram_api_hash_2)
            )
        
        if not accounts:
            logger.info("No accounts configured in .env - use web interface to login")
            return
        
        logger.info(f"Attempting to initialize {len(accounts)} account(s) from .env...")
        for phone, api_id, api_hash in accounts:
            try:
                client = await self.create_client(phone, api_id, api_hash)
                if client:
                    logger.info(f"Successfully initialized account: {phone}")
                else:
                    logger.warning(f"Account {phone} needs authorization via web")
            except Exception as e:
                logger.error(f"Failed to initialize account {phone}: {e}")
    
    def get_available_clients(self) -> List[TelegramClient]:
        """Get list of all connected and authorized clients"""
        available = []
        for client in self.clients.values():
            try:
                # Note: This is synchronous check, may not be 100% accurate
                # But it's good enough for listing purposes
                available.append(client)
            except:
                continue
        return available
    
    async def disconnect_all(self):
        """Disconnect all clients"""
        for phone, client in self.clients.items():
            try:
                await client.disconnect()
                logger.info(f"Disconnected client: {phone}")
            except Exception as e:
                logger.error(f"Error disconnecting {phone}: {e}")
        self.clients.clear()
    
    async def logout_account(self, phone: str) -> bool:
        """Logout and remove account session"""
        try:
            if phone in self.clients:
                client = self.clients[phone]
                
                # Logout from Telegram
                try:
                    await client.log_out()
                    logger.info(f"Logged out from Telegram: {phone}")
                except Exception as e:
                    logger.warning(f"Error during logout for {phone}: {e}")
                
                # Disconnect client
                await client.disconnect()
                
                # Remove from clients dict
                del self.clients[phone]
            
            # Delete session file
            session_name = phone.replace("+", "")
            session_file = self.session_dir / f"{session_name}.session"
            if session_file.exists():
                session_file.unlink()
                logger.info(f"Deleted session file: {session_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error logging out {phone}: {e}")
            return False

session_manager = SessionManager()
