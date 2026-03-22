from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Telegram
    telegram_api_id: int
    telegram_api_hash: str
    telegram_phone: str
    
    # Additional accounts
    telegram_api_id_2: Optional[int] = None
    telegram_api_hash_2: Optional[str] = None
    telegram_phone_2: Optional[str] = None
    
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
