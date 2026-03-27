"""
Telegram account authentication via web interface
"""
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from pathlib import Path
from typing import Optional, Dict
from app.utils.logger import logger
from app.auth.session_manager import session_manager
import asyncio

class TelegramAuthManager:
    def __init__(self):
        self.pending_auths: Dict[str, dict] = {}  # Store pending auth sessions
    
    async def send_code(self, phone: str, api_id: int, api_hash: str) -> dict:
        """Send verification code to phone"""
        try:
            session_name = phone.replace("+", "")
            session_file = Path("sessions") / f"{session_name}.session"
            
            client = TelegramClient(str(session_file), api_id, api_hash)
            await client.connect()
            
            # Check if already authorized
            if await client.is_user_authorized():
                me = await client.get_me()
                
                # Add to session manager so it can be used
                session_manager.clients[phone] = client
                
                logger.info(f"Account {phone} already authorized and added to session manager")
                
                return {
                    "status": "already_authorized",
                    "user": {
                        "first_name": me.first_name,
                        "last_name": me.last_name or "",
                        "username": me.username or "",
                        "phone": me.phone
                    }
                }
            
            # Send code
            result = await client.send_code_request(phone)
            
            # Store client for later use
            self.pending_auths[phone] = {
                "client": client,
                "phone_code_hash": result.phone_code_hash,
                "api_id": api_id,
                "api_hash": api_hash
            }
            
            logger.info(f"Verification code sent to {phone}")
            
            return {
                "status": "code_sent",
                "phone": phone,
                "message": "Verification code sent to your Telegram app"
            }
            
        except Exception as e:
            logger.error(f"Failed to send code to {phone}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def verify_code(self, phone: str, code: str) -> dict:
        """Verify the code and complete sign in"""
        try:
            if phone not in self.pending_auths:
                return {
                    "status": "error",
                    "message": "No pending authentication for this phone. Please request code first."
                }
            
            auth_data = self.pending_auths[phone]
            client = auth_data["client"]
            
            try:
                # Try to sign in with code
                await client.sign_in(phone, code)
                
                # Success - get user info
                me = await client.get_me()
                
                # Add to session manager
                session_manager.clients[phone] = client
                
                # Clean up pending auth
                del self.pending_auths[phone]
                
                logger.info(f"Successfully authenticated {phone}")
                
                return {
                    "status": "success",
                    "message": "Successfully authenticated!",
                    "user": {
                        "first_name": me.first_name,
                        "last_name": me.last_name or "",
                        "username": me.username or "",
                        "phone": me.phone
                    }
                }
                
            except SessionPasswordNeededError:
                # 2FA is enabled
                logger.info(f"2FA required for {phone}")
                return {
                    "status": "password_required",
                    "message": "Two-factor authentication is enabled. Please enter your password."
                }
                
            except PhoneCodeInvalidError:
                return {
                    "status": "error",
                    "message": "Invalid verification code. Please try again."
                }
                
        except Exception as e:
            logger.error(f"Failed to verify code for {phone}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def verify_password(self, phone: str, password: str) -> dict:
        """Verify 2FA password"""
        try:
            if phone not in self.pending_auths:
                return {
                    "status": "error",
                    "message": "No pending authentication for this phone."
                }
            
            auth_data = self.pending_auths[phone]
            client = auth_data["client"]
            
            try:
                # Sign in with password
                await client.sign_in(password=password)
                
                # Success - get user info
                me = await client.get_me()
                
                # Add to session manager
                session_manager.clients[phone] = client
                
                # Clean up pending auth
                del self.pending_auths[phone]
                
                logger.info(f"Successfully authenticated {phone} with 2FA")
                
                return {
                    "status": "success",
                    "message": "Successfully authenticated with 2FA!",
                    "user": {
                        "first_name": me.first_name,
                        "last_name": me.last_name or "",
                        "username": me.username or "",
                        "phone": me.phone
                    }
                }
                
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Invalid password: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Failed to verify password for {phone}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def logout_account(self, phone: str) -> dict:
        """Logout and remove account session"""
        try:
            # Use session manager's logout method
            success = await session_manager.logout_account(phone)
            
            if not success:
                return {
                    "status": "error",
                    "message": "Failed to logout account"
                }
            
            # Remove from pending auths if exists
            if phone in self.pending_auths:
                try:
                    await self.pending_auths[phone]["client"].disconnect()
                except Exception as e:
                    logger.debug(f"Error disconnecting pending auth client: {e}")
                del self.pending_auths[phone]
            
            # Clear channels from database for this account
            from app.utils.database import AsyncSessionLocal, Channel
            from sqlalchemy import delete
            async with AsyncSessionLocal() as db:
                try:
                    # Delete all channels (they were fetched with this account)
                    # We'll clear all channels since we don't track which account fetched which channel
                    result = await db.execute(delete(Channel))
                    await db.commit()
                    logger.info(f"Deleted {result.rowcount} channels from database after logout")
                except Exception as e:
                    logger.error(f"Error deleting channels: {e}")
                    await db.rollback()
            
            logger.info(f"Successfully logged out {phone}")
            
            return {
                "status": "success",
                "message": f"Successfully logged out {phone} and cleared channel list"
            }
            
        except Exception as e:
            logger.error(f"Failed to logout {phone}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def get_logged_accounts(self) -> list:
        """Get list of currently logged in accounts"""
        accounts = []
        
        for phone, client in session_manager.clients.items():
            try:
                if await client.is_user_authorized():
                    me = await client.get_me()
                    accounts.append({
                        "phone": phone,
                        "first_name": me.first_name,
                        "last_name": me.last_name or "",
                        "username": me.username or "",
                        "user_id": me.id
                    })
            except Exception as e:
                logger.error(f"Error getting info for {phone}: {e}")
        
        return accounts

telegram_auth_manager = TelegramAuthManager()
