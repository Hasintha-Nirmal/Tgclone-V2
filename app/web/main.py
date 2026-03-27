from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from contextlib import asynccontextmanager
from app.web import routes
from app.web.auth import check_auth, auth_middleware
from app.utils.database import init_db, SessionLocal, CloneJob
from app.auth.session_manager import session_manager
from app.worker.sync_worker import sync_worker
from app.utils.logger import logger
from config.settings import settings
from datetime import datetime
import asyncio

security = HTTPBasic()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting application...")
    app.start_time = datetime.utcnow()
    init_db()
    
    # Initialize Telegram clients (if configured in .env)
    try:
        await session_manager.initialize_all_accounts()
    except Exception as e:
        logger.warning(f"Could not initialize .env accounts: {e}")
        logger.info("You can login accounts via the web dashboard")
    
    # Start sync worker
    asyncio.create_task(sync_worker.start())
    
    yield
    
    # Shutdown - graceful cleanup
    logger.info("Shutting down gracefully...")
    
    # Stop sync worker
    await sync_worker.stop()
    
    # Mark running jobs as paused (not failed)
    db = SessionLocal()
    try:
        updated = db.query(CloneJob).filter(
            CloneJob.status == "running"
        ).update({"status": "paused"})
        db.commit()
        if updated > 0:
            logger.info(f"Marked {updated} running jobs as paused")
    except Exception as e:
        logger.error(f"Error updating job statuses: {e}")
    finally:
        db.close()
    
    # Disconnect clients
    await session_manager.disconnect_all()
    
    logger.info("Shutdown complete")

app = FastAPI(
    title="Telegram Automation System",
    description="Channel cloning and automation system",
    version="1.0.0",
    lifespan=lifespan
)

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
except:
    pass

@app.get("/", response_class=HTMLResponse)
async def root(credentials: HTTPBasicCredentials = Depends(security)):
    """Serve main dashboard"""
    check_auth(credentials)
    try:
        with open("app/web/templates/index.html", "r") as f:
            return f.read()
    except:
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
    from app.utils.database import SessionLocal, CloneJob
    
    try:
        # Check database
        db = SessionLocal()
        try:
            db.execute("SELECT 1")
            db_status = "healthy"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            db_status = "unhealthy"
        finally:
            db.close()
        
        # Check Telegram accounts
        accounts = len(session_manager.get_available_clients())
        
        # Check active jobs
        db = SessionLocal()
        try:
            active_jobs = db.query(CloneJob).filter(
                CloneJob.status.in_(["running", "pending"])
            ).count()
        finally:
            db.close()
        
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
