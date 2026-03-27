from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool
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

# Database setup with proper connection pooling
if "sqlite" in settings.database_url:
    # SQLite uses StaticPool for file-based databases
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
else:
    # PostgreSQL uses QueuePool with optimized settings
    engine = create_engine(
        settings.database_url,
        poolclass=QueuePool,
        pool_size=10,              # Steady-state connections
        max_overflow=20,           # Burst capacity (total max = 30)
        pool_pre_ping=True,        # Verify connections before use
        pool_recycle=3600,         # Recycle connections after 1 hour
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
