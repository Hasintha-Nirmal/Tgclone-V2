from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional
import os

class Settings(BaseSettings):
    # Telegram (now optional - can login via web)
    telegram_api_id: Optional[int] = None
    telegram_api_hash: Optional[str] = None
    telegram_phone: Optional[str] = None
    
    # Additional accounts
    telegram_api_id_2: Optional[int] = None
    telegram_api_hash_2: Optional[str] = None
    telegram_phone_2: Optional[str] = None
    
    @field_validator('telegram_api_id', 'telegram_api_id_2', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        """Convert empty string to None for optional integer fields"""
        if v == '' or v is None:
            return None
        return v
    
    @field_validator('telegram_api_hash', 'telegram_api_hash_2', 'telegram_phone', 'telegram_phone_2', mode='before')
    @classmethod
    def empty_str_to_none_str(cls, v):
        """Convert empty string to None for optional string fields"""
        if v == '':
            return None
        return v
    
    # Database
    database_url: str = "sqlite:///./data/app.db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    use_redis: bool = False
    
    # Web
    web_host: str = "0.0.0.0"
    web_port: int = 8000
    secret_key: str
    admin_username: str = "admin"
    admin_password: str = "changeme"
    
    # Storage
    auto_delete_files: bool = True
    max_download_size_mb: int = 2000
    temp_dir: str = "./downloads"
    
    # Worker
    worker_threads: int = 3
    sync_interval_seconds: int = 30
    max_retries: int = 3
    flood_wait_multiplier: float = 1.5
    
    # Rate Limiting (protect from ban)
    delay_between_messages: float = 1.0  # seconds between text messages
    delay_between_media: float = 2.0     # seconds between media messages
    break_every_n_messages: int = 10     # take a break every N messages
    break_duration: float = 5.0          # break duration in seconds
    max_messages_per_hour: int = 200     # maximum messages per hour (safety limit)
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

# Ensure directories exist
os.makedirs("sessions", exist_ok=True)
os.makedirs("logs", exist_ok=True)
os.makedirs("downloads", exist_ok=True)
os.makedirs("data", exist_ok=True)
