"""
Authentication rate limiter to prevent brute force attacks
"""
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from config.settings import settings


class AuthRateLimiter:
    """Rate limiter for authentication attempts per IP address"""
    
    def __init__(self):
        self.attempts: Dict[str, List[datetime]] = {}
        self.max_attempts = settings.auth_max_attempts
        self.window_minutes = settings.auth_window_minutes
        self._last_cleanup = datetime.utcnow()
        self._cleanup_interval = 3600  # Cleanup every hour
    
    def check_rate_limit(self, ip: str) -> Tuple[bool, Optional[int]]:
        """
        Check if IP is within rate limit
        
        Args:
            ip: Client IP address
            
        Returns:
            Tuple of (allowed, wait_seconds)
            - allowed: True if request is allowed, False if rate limited
            - wait_seconds: Number of seconds to wait if rate limited, None if allowed
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=self.window_minutes)
        
        # Periodic cleanup to prevent memory growth
        if (now - self._last_cleanup).total_seconds() > self._cleanup_interval:
            self.cleanup_old_entries()
            self._last_cleanup = now
        
        # Clean old attempts for this IP
        if ip in self.attempts:
            self.attempts[ip] = [t for t in self.attempts[ip] if t > cutoff]
        
        # Check if at limit
        attempts_count = len(self.attempts.get(ip, []))
        if attempts_count >= self.max_attempts:
            # Calculate wait time until oldest attempt expires
            oldest = self.attempts[ip][0]
            wait = int((oldest + timedelta(minutes=self.window_minutes) - now).total_seconds())
            return False, max(wait, 1)  # At least 1 second
        
        return True, None
    
    def record_attempt(self, ip: str):
        """
        Record a failed authentication attempt
        
        Args:
            ip: Client IP address
        """
        if ip not in self.attempts:
            self.attempts[ip] = []
        self.attempts[ip].append(datetime.utcnow())
    
    def cleanup_old_entries(self):
        """Remove old entries to prevent memory growth"""
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=self.window_minutes)
        
        # Clean all IPs
        for ip in list(self.attempts.keys()):
            self.attempts[ip] = [t for t in self.attempts[ip] if t > cutoff]
            # Remove IP if no recent attempts
            if not self.attempts[ip]:
                del self.attempts[ip]


# Global instance
auth_rate_limiter = AuthRateLimiter()
