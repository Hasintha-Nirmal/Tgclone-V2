from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from contextlib import asynccontextmanager
from app.web import routes
from app.web.auth import check_auth, auth_middleware
from app.utils.database import init_db, AsyncSessionLocal, CloneJob
from app.auth.session_manager import session_manager
from app.worker.sync_worker import sync_worker
from app.utils.logger import logger
from config.settings import settings
from datetime import datetime
from sqlalchemy import select, update
import asyncio

security = HTTPBasic()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting application...")
    app.start_time = datetime.utcnow()
    await init_db()
    
    # Initialize Telegram clients (if configured in .env)
    try:
        await session_manager.initialize_all_accounts()
    except Exception as e:
        logger.warning(f"Could not initialize .env accounts: {e}")
        logger.info("You can login accounts via the web dashboard")
    
    # Start sync worker with exception handling
    sync_task = asyncio.create_task(sync_worker.start())
    
    # Add exception callback to log any unhandled errors
    def handle_sync_worker_exception(task):
        try:
            task.result()
        except asyncio.CancelledError:
            pass  # Expected during shutdown
        except Exception as e:
            logger.error(f"Sync worker crashed with unhandled exception: {e}", exc_info=True)
    
    sync_task.add_done_callback(handle_sync_worker_exception)
    
    yield
    
    # Shutdown - graceful cleanup
    logger.info("Shutting down gracefully...")
    
    # Stop sync worker first
    logger.info("Stopping sync worker...")
    await sync_worker.stop()
    logger.info("Sync worker stopped successfully")
    
    # Mark running jobs as paused (not failed)
    logger.info("Updating job statuses...")
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                update(CloneJob)
                .filter(CloneJob.status == "running")
                .values(status="paused")
            )
            await db.commit()
            if result.rowcount > 0:
                logger.info(f"Marked {result.rowcount} running jobs as paused")
        except Exception as e:
            logger.error(f"Error updating job statuses: {e}")
    
    # Disconnect clients
    logger.info("Disconnecting Telegram clients...")
    await session_manager.disconnect_all()
    logger.info("All clients disconnected")
    
    logger.info("Shutdown complete")

app = FastAPI(
    title="Telegram Automation System",
    description="Channel cloning and automation system",
    version="1.0.0",
    lifespan=lifespan
)

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # X-Frame-Options: Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    
    # X-Content-Type-Options: Prevent MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # X-XSS-Protection: Enable XSS filter
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # HSTS: Force HTTPS (if enabled)
    if settings.enable_hsts:
        response.headers["Strict-Transport-Security"] = f"max-age={settings.hsts_max_age}; includeSubDomains"
    
    return response

# Add HTTPS redirect middleware (if enabled)
if settings.force_https:
    @app.middleware("http")
    async def https_redirect(request: Request, call_next):
        """Redirect HTTP to HTTPS"""
        # Skip redirect for health checks
        if request.url.path in ["/health", "/health/detailed"]:
            return await call_next(request)
        
        # Check if request is HTTP
        if request.url.scheme == "http":
            # Build HTTPS URL
            https_url = request.url.replace(scheme="https")
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=str(https_url), status_code=301)
        
        return await call_next(request)

# Add authentication middleware
app.middleware("http")(auth_middleware)

# CORS - Restricted to specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PUT"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=3600,
)

# Include routers
app.include_router(routes.auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(routes.channels_router, prefix="/api/channels", tags=["channels"])
app.include_router(routes.jobs_router, prefix="/api/jobs", tags=["jobs"])
app.include_router(routes.system_router, prefix="/api/system", tags=["system"])
app.include_router(routes.accounts_router, prefix="/api/accounts", tags=["accounts"])

# Serve static files
try:
    app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
except Exception as e:
    logger.debug(f"Static files directory not found: {e}")

@app.get("/", response_class=HTMLResponse)
async def root(credentials: HTTPBasicCredentials = Depends(security)):
    """Serve main dashboard"""
    check_auth(credentials)
    try:
        with open("app/web/templates/index.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        return """
        <html>
            <head><title>Telegram Automation</title></head>
            <body>
                <h1>Telegram Automation System</h1>
                <p>API Documentation: <a href="/docs">/docs</a></p>
            </body>
        </html>
        """

@app.get("/health")
async def health():
    """Basic health check"""
    return {"status": "healthy"}

@app.get("/health/detailed")
async def health_detailed():
    """Detailed health check with system status"""
    from app.utils.database import AsyncSessionLocal, CloneJob
    from sqlalchemy import select, text
    
    try:
        # Check database
        async with AsyncSessionLocal() as db:
            try:
                await db.execute(text("SELECT 1"))
                db_status = "healthy"
            except Exception as e:
                logger.error(f"Database health check failed: {e}")
                db_status = "unhealthy"
        
        # Check Telegram accounts
        accounts = len(await session_manager.get_available_clients())
        
        # Check active jobs
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(
                    select(CloneJob).filter(CloneJob.status.in_(["running", "pending"]))
                )
                active_jobs = len(result.scalars().all())
            except Exception:
                active_jobs = 0
        
        # Check sync worker
        sync_status = "running" if sync_worker.running else "stopped"
        
        # Calculate uptime
        uptime_seconds = (datetime.utcnow() - app.start_time).total_seconds() if hasattr(app, 'start_time') else 0
        
        overall_status = "healthy" if db_status == "healthy" and accounts > 0 else "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_status,
            "telegram_accounts": accounts,
            "active_jobs": active_jobs,
            "sync_worker": sync_status,
            "uptime_seconds": uptime_seconds
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
