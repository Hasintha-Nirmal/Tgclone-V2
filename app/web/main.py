from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from contextlib import asynccontextmanager
from app.web import routes
from app.web.auth import check_auth, auth_middleware
from app.utils.mongodb import connect_mongodb, disconnect_mongodb
from app.utils import db_ops
from app.auth.session_manager import session_manager
from app.worker.sync_worker import sync_worker
from app.utils.logger import logger
import asyncio

security = HTTPBasic()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting application...")

    # Connect to MongoDB
    await connect_mongodb()

    # Check for jobs interrupted by a previous VPS crash
    resumable = await db_ops.get_resumable_jobs()
    if resumable:
        logger.warning(
            f"⚠️  Found {len(resumable)} interrupted job(s) from last session. "
            f"Use POST /api/jobs/{{job_id}}/resume to continue them."
        )
        for entry in resumable:
            job = entry['job']
            cp   = entry['checkpoint']
            logger.warning(
                f"   → Job {job['job_id']} | "
                f"{job['source_channel']} → {job['target_channel']} | "
                f"last_msg={entry['resume_from_message_id']} | "
                f"processed={entry['already_processed']}"
            )

    # Initialize Telegram clients (if configured in .env)
    try:
        await session_manager.initialize_all_accounts()
    except Exception as e:
        logger.warning(f"Could not initialize .env accounts: {e}")
        logger.info("You can login accounts via the web dashboard")

    # Start sync worker
    asyncio.create_task(sync_worker.start())

    yield

    # Shutdown
    logger.info("Shutting down...")
    await sync_worker.stop()
    await session_manager.disconnect_all()
    await disconnect_mongodb()

app = FastAPI(
    title="Telegram Automation System",
    description="Channel cloning and automation system",
    version="1.0.0",
    lifespan=lifespan
)

# Add authentication middleware
app.middleware("http")(auth_middleware)

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
    return {"status": "healthy"}
