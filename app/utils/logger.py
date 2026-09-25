import logging
import sys
from pathlib import Path
from config.settings import settings

def setup_logger(name: str = "telegram_automation") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    
    # File handler — gracefully skip if the log directory is not writable
    # (e.g. Docker bind-mount permission issue on first run)
    try:
        Path(settings.log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(settings.log_file)
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    except (PermissionError, OSError) as e:
        # Fall back to console-only — app still starts, logs go to stdout
        console_handler.setLevel(logging.DEBUG)
        logging.getLogger("setup").warning(
            f"Cannot write log file '{settings.log_file}': {e}. Logging to console only."
        )

    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()
