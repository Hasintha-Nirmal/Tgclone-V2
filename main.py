#!/usr/bin/env python3
"""
Telegram Automation System
Main entry point
"""
import uvicorn
from config.settings import settings
from app.utils.logger import logger

def main():
    logger.info("Starting Telegram Automation System...")
    logger.info(f"Web interface: http://{settings.web_host}:{settings.web_port}")
    
    uvicorn.run(
        "app.web.main:app",
        host=settings.web_host,
        port=settings.web_port,
        reload=False,
        log_level=settings.log_level.lower()
    )

if __name__ == "__main__":
    main()
