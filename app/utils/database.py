from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool, NullPool
from datetime import datetime
from config.settings import settings

Base = declarative_base()

class Channel(Base):
    __tablename__ = "channels"
    
    id = Column(Integer, primary_key=True)
    channel_id = Column(String, unique=True, index=True)
    title = Column(String, index=True)
    username = Column(String, nullable=True, index=True)
    member_count = Column(Integer, nullable=True)
    is_private = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class CloneJob(Base):
    __tablename__ = "clone_jobs"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String, unique=True, index=True)
    source_channel = Column(String, index=True)
    target_channel = Column(String, index=True)
    status = Column(String, default="pending", index=True)  # pending, running, completed, failed, paused
    total_messages = Column(Integer, default=0)
    processed_messages = Column(Integer, default=0)
    start_message_id = Column(Integer, nullable=True)
    auto_sync = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    error_message = Column(Text, nullable=True)
    
    # Composite indexes for common queries
    __table_args__ = (
        Index('idx_status_created', 'status', 'created_at'),
        Index('idx_auto_sync_status', 'auto_sync', 'status'),
    )

class SyncState(Base):
    __tablename__ = "sync_state"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String, index=True, unique=True)
    last_message_id = Column(Integer)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True)
    phone = Column(String, unique=True, index=True)
    session_name = Column(String)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class RateLimitEntry(Base):
    __tablename__ = "rate_limit_entries"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    job_id = Column(String, nullable=True)
    account_phone = Column(String, nullable=True)

# Database setup with async engine and proper connection pooling
if "sqlite" in settings.database_url:
    # Convert SQLite URL to async format
    async_url = settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
    # SQLite uses NullPool for async operations to avoid connection issues
    engine = create_async_engine(
        async_url,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
        echo=False
    )
else:
    # PostgreSQL uses asyncpg driver
    async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(
        async_url,
        poolclass=QueuePool,
        pool_size=10,              # Steady-state connections
        max_overflow=20,           # Burst capacity (total max = 30)
        pool_pre_ping=True,        # Verify connections before use
        pool_recycle=3600,         # Recycle connections after 1 hour
        echo=False
    )

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def init_db():
    """Initialize database tables asynchronously"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """Async generator for database sessions"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
