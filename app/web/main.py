from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.web import routes
from app.utils.database import init_db
from app.auth.session_manager import session_manager
from app.worker.sync_worker import sync_worker
from app.utils.logger import logger
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting application...")
    init_db()
    
    # Initialize Telegram clients
    try:
        await session_manager.initialize_all_accounts()
    except Exception as e:
        logger.error(f"Failed to initialize accounts: {e}")
    
    # Start sync worker
    asyncio.create_task(sync_worker.start())
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await sync_worker.stop()
    await session_manager.disconnect_all()

app = FastAPI(
    title="Telegram Automation System",
    description="Channel cloning and automation system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(routes.channels_router, prefix="/api/channels", tags=["channels"])
app.include_router(routes.jobs_router, prefix="/api/jobs", tags=["jobs"])
app.include_router(routes.system_router, prefix="/api/system", tags=["system"])

# Serve static files
try:
    app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
except:
    pass

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main dashboard"""
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
    return {"status": "healthy"}
