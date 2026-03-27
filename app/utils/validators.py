"""Input validation utilities for API endpoints"""
import re
from typing import Optional


def validate_channel_id(channel_id: str) -> tuple[bool, Optional[str]]:
    """
    Validate channel ID format.
    
    Valid formats:
    - Numeric ID: -1001234567890 or 1234567890
    - Username: @username or username
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not channel_id or not isinstance(channel_id, str):
        return False, "Channel ID must be a non-empty string"
    
    channel_id = channel_id.strip()
    
    # Check for numeric ID (with optional -100 prefix)
    if re.match(r'^-?100?\d+$', channel_id):
        return True, None
    
    # Check for username format (@username or username)
    if re.match(r'^@?[\w]{5,32}$', channel_id):
        return True, None
    
    return False, "Channel ID must be numeric (e.g., -1001234567890) or username (e.g., @username)"


def validate_job_id(job_id: str) -> tuple[bool, Optional[str]]:
    """
    Validate job ID format (UUID).
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not job_id or not isinstance(job_id, str):
        return False, "Job ID must be a non-empty string"
    
    job_id = job_id.strip()
    
    # Check for UUID format
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if re.match(uuid_pattern, job_id, re.IGNORECASE):
        return True, None
    
    return False, "Job ID must be a valid UUID"
