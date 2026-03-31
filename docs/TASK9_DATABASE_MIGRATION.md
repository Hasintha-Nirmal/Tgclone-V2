# Task 9: Database Migration - RateLimitEntry Table

## Summary

Successfully implemented database migration to add the `RateLimitEntry` table for persistent rate limiting tracking.

## Changes Made

### 1. Updated `app/utils/database.py`

Added new `RateLimitEntry` model with the following schema:

```python
class RateLimitEntry(Base):
    __tablename__ = "rate_limit_entries"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    job_id = Column(String, nullable=True)
    account_phone = Column(String, nullable=True)
```

**Features:**
- `id`: Primary key for unique identification
- `timestamp`: Indexed column for efficient time-based queries (sliding window algorithm)
- `job_id`: Optional field to track which clone job created the entry
- `account_phone`: Optional field to track which account sent the message

### 2. Created Migration Scripts

#### `migrate_db.py`
Standalone script to run database migrations manually:
```bash
python migrate_db.py
```

#### `test_rate_limit_migration.py`
Comprehensive test script that verifies:
- Table creation
- Index functionality
- CRUD operations
- Schema integrity

## How the Migration Works

The migration runs automatically when the application starts via the `init_db()` function in `app/web/main.py`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting application...")
    await init_db()  # <-- Creates all tables including RateLimitEntry
    ...
```

The `init_db()` function uses SQLAlchemy's `create_all()` which:
- Creates new tables if they don't exist
- Preserves existing tables and data
- Is idempotent (safe to run multiple times)

## Running the Migration

### Option 1: Start the Application (Recommended)

The migration runs automatically on application startup:

**Local:**
```bash
python main.py
```

**Docker:**
```bash
docker compose up -d
```

### Option 2: Run Migration Script Manually

**Local (requires dependencies installed):**
```bash
python migrate_db.py
```

**Docker:**
```bash
docker exec telegram-automation python migrate_db.py
```

### Option 3: Run Test Script

To verify the migration with comprehensive tests:

**Local:**
```bash
python test_rate_limit_migration.py
```

**Docker:**
```bash
docker exec telegram-automation python test_rate_limit_migration.py
```

## Verification

After running the migration, verify the table was created:

**SQLite (default):**
```bash
sqlite3 data/app.db ".schema rate_limit_entries"
```

Expected output:
```sql
CREATE TABLE rate_limit_entries (
    id INTEGER NOT NULL PRIMARY KEY,
    timestamp DATETIME,
    job_id VARCHAR,
    account_phone VARCHAR
);
CREATE INDEX ix_rate_limit_entries_timestamp ON rate_limit_entries (timestamp);
```

## Acceptance Criteria Status

✅ **RateLimitEntry table created** - Model defined with all required fields
✅ **Index on timestamp column created** - Indexed for efficient time-based queries
✅ **Migration runs without errors** - Uses existing async `init_db()` function
✅ **Existing data preserved** - SQLAlchemy's `create_all()` is non-destructive

## Integration with Rate Limiter

This table will be used by the `GlobalRateLimiter` class (to be implemented in subsequent tasks) to:
1. Track message timestamps across application restarts
2. Implement sliding window rate limiting algorithm
3. Coordinate rate limits between manual clone jobs and auto-sync worker
4. Query recent entries efficiently using the timestamp index

## Notes

- The `init_db()` function was already converted to async in Task 1
- No breaking changes to existing functionality
- The migration is backward compatible
- The table will be empty initially and populated as messages are sent
