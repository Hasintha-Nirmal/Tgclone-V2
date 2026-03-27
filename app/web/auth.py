"""
Authentication middleware for web dashboard
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from config.settings import settings
from app.utils.logger import logger
from datetime import datetime
import secrets

security = HTTPBasic()

def get_client_ip(request: Request) -> str:
    """Get client IP address from request"""
    # Check for X-Forwarded-For header (proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    # Check for X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    # Fall back to direct client
    return request.client.host if request.client else "unknown"

def verify_credentials(credentials: HTTPBasicCredentials, request: Request = None) -> bool:
    """Verify username and password with security logging"""
    correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"),
        settings.admin_username.encode("utf8")
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        settings.admin_password.encode("utf8")
    )
    
    is_valid = correct_username and correct_password
    
    # Security logging
    client_ip = get_client_ip(request) if request else "unknown"
    timestamp = datetime.utcnow().isoformat()
    
    if not is_valid:
        logger.warning(
            f"Failed authentication attempt - "
            f"Username: {credentials.username}, "
            f"IP: {client_ip}, "
            f"Time: {timestamp}"
        )
    else:
        logger.info(
            f"Successful authentication - "
            f"Username: {credentials.username}, "
            f"IP: {client_ip}, "
            f"Time: {timestamp}"
        )
    
    return is_valid

def check_auth(credentials: HTTPBasicCredentials = None, request: Request = None):
    """Check if user is authenticated"""
    if not credentials or not verify_credentials(credentials, request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

async def auth_middleware(request: Request, call_next):
    """Middleware to check authentication on all requests"""
    # Skip auth for health check
    if request.url.path in ["/health", "/health/detailed"]:
        return await call_next(request)
    
    # Check for basic auth
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Basic "):
        client_ip = get_client_ip(request)
        logger.warning(f"Missing authentication from IP: {client_ip}")
        return HTMLResponse(
            content="Authentication required",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Telegram Automation"'}
        )
    
    try:
        # Decode and verify credentials
        import base64
        encoded_credentials = auth_header.split(" ")[1]
        decoded = base64.b64decode(encoded_credentials).decode("utf-8")
        username, password = decoded.split(":", 1)
        
        credentials = HTTPBasicCredentials(username=username, password=password)
        
        if not verify_credentials(credentials, request):
            return HTMLResponse(
                content="Invalid credentials",
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="Telegram Automation"'}
            )
        
        # Authentication successful
        response = await call_next(request)
        return response
        
    except Exception as e:
        client_ip = get_client_ip(request)
        logger.error(f"Authentication error from IP {client_ip}: {e}")
        return HTMLResponse(
            content="Authentication required",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Telegram Automation"'}
        )
