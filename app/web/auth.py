"""
Authentication middleware for web dashboard
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from config.settings import settings
import secrets

security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials) -> bool:
    """Verify username and password"""
    correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"),
        settings.admin_username.encode("utf8")
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        settings.admin_password.encode("utf8")
    )
    return correct_username and correct_password

def check_auth(credentials: HTTPBasicCredentials = None):
    """Check if user is authenticated"""
    if not credentials or not verify_credentials(credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

async def auth_middleware(request: Request, call_next):
    """Middleware to check authentication on all requests"""
    # Skip auth for health check
    if request.url.path == "/health":
        return await call_next(request)
    
    # Check for basic auth
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Basic "):
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
        
        if not verify_credentials(credentials):
            return HTMLResponse(
                content="Invalid credentials",
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="Telegram Automation"'}
            )
        
        # Authentication successful
        response = await call_next(request)
        return response
        
    except Exception as e:
        return HTMLResponse(
            content="Authentication required",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Telegram Automation"'}
        )
