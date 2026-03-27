# Setup Guide - Telegram Automation System

## Prerequisites

- Python 3.11 or higher
- Telegram account
- API credentials from https://my.telegram.org

## Step 1: Get Telegram API Credentials

1. Go to https://my.telegram.org
2. Log in with your phone number
3. Click on "API Development Tools"
4. Create a new application
5. Note down your `api_id` and `api_hash`

## Step 2: Local Installation

### Clone or Download

```bash
# If using git
git clone <repository-url>
cd telegram-automation

# Or extract the zip file
```

### Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

**Note**: The system now uses async SQLAlchemy with `aiosqlite` for non-blocking database operations. This dependency is included in `requirements.txt`.

### Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit .env with your credentials
# Required fields:
# - TELEGRAM_API_ID
# - TELEGRAM_API_HASH
# - TELEGRAM_PHONE
# - SECRET_KEY (generate random string)
```

### First Run

```bash
python main.py
```

On first run, you'll need to authorize your Telegram account:
1. You'll receive a code on Telegram
2. Enter the code when prompted
3. If you have 2FA, enter your password

### Access Dashboard

Open your browser and go to:
```
http://localhost:8000
```

## Step 3: Docker Installation

### Using Docker Compose (Recommended)

```bash
# Copy environment file
cp .env.example .env

# Edit .env with your credentials
nano .env

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### With Redis (Optional)

```bash
# Start with Redis
docker-compose --profile with-redis up -d
```

### With PostgreSQL (Optional)

```bash
# Update .env
DATABASE_URL=postgresql://telegram:changeme@postgres:5432/telegram_automation

# Start with PostgreSQL
docker-compose --profile with-postgres up -d
```

## Step 4: First Time Setup

### 1. Authorize Telegram Account

For Docker installations, you need to authorize manually:

```bash
# Enter container
docker exec -it telegram-automation bash

# Run Python
python

# In Python shell:
from app.auth.session_manager import session_manager
import asyncio

async def auth():
    await session_manager.initialize_all_accounts()

asyncio.run(auth())
# Follow the prompts to enter code
```

### 2. Fetch Your Channels

1. Open dashboard: http://localhost:8000
2. Go to "Channels" tab
3. Click "Refresh" button
4. Wait for channels to load

### 3. Create Your First Clone Job

1. Go to "Create Job" tab
2. Enter source channel ID (format: -1001234567890)
3. Enter target channel ID
4. Optional: Set start message ID
5. Optional: Enable auto-sync for real-time cloning
6. Click "Create Job"

## Step 5: Advanced Configuration

### Database Configuration

The system uses async SQLAlchemy with SQLite by default:

```env
# Default SQLite (async)
DATABASE_URL=sqlite+aiosqlite:///./data/app.db

# Optional: PostgreSQL (async)
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname
```

**Important**: The database URL must use an async driver:
- SQLite: `sqlite+aiosqlite://`
- PostgreSQL: `postgresql+asyncpg://`

### Multi-Account Setup

Add additional accounts in `.env`:

```env
TELEGRAM_API_ID_2=your_second_api_id
TELEGRAM_API_HASH_2=your_second_api_hash
TELEGRAM_PHONE_2=+1234567890
```

### Storage Optimization

```env
# Auto-delete files after upload (recommended)
AUTO_DELETE_FILES=true

# Maximum download size in MB
MAX_DOWNLOAD_SIZE_MB=2000

# Temporary directory
TEMP_DIR=./downloads
```

### Worker Configuration

```env
# Number of worker threads
WORKER_THREADS=3

# Sync interval in seconds
SYNC_INTERVAL_SECONDS=30

# Maximum retries for failed operations
MAX_RETRIES=3

# Flood wait multiplier
FLOOD_WAIT_MULTIPLIER=1.5

# Graceful shutdown timeout (seconds)
WORKER_SHUTDOWN_TIMEOUT=30
```

### Timeout Configuration

```env
# Operation timeout in seconds (default: 300)
OPERATION_TIMEOUT=300

# Clone job timeout in seconds (default: 3600)
CLONE_TIMEOUT=3600
```

## Troubleshooting

### Issue: "Authorization required"

**Solution**: Complete the authorization process by entering the code sent to your Telegram account.

### Issue: "FloodWaitError"

**Solution**: The system automatically handles flood waits. If using multiple accounts, it will rotate between them.

### Issue: "Channel not found"

**Solution**: 
- Ensure you're a member of the channel
- Use correct channel ID format: -1001234567890
- For private channels, you must be a member

### Issue: "Permission denied"

**Solution**: 
- Ensure your account has permission to read from source channel
- Ensure your account has admin rights in target channel

### Issue: High disk usage

**Solution**:
- Ensure `AUTO_DELETE_FILES=true` in .env
- Run cleanup: `curl -X POST http://localhost:8000/api/system/cleanup`
- Check disk usage in dashboard

## API Documentation

Access interactive API docs:
```
http://localhost:8000/docs
```

## Security Notes

1. Never share your `.env` file
2. Keep session files secure (in `sessions/` directory)
3. Use strong `SECRET_KEY` for production
4. Change default admin credentials
5. Use HTTPS in production (reverse proxy recommended)

## Production Deployment

### Using Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Using Systemd Service

Create `/etc/systemd/system/telegram-automation.service`:

```ini
[Unit]
Description=Telegram Automation System
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/telegram-automation
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable telegram-automation
sudo systemctl start telegram-automation
```

## Backup

Important directories to backup:
- `sessions/` - Telegram session files
- `data/` - Database files
- `.env` - Configuration

```bash
# Backup script
tar -czf backup-$(date +%Y%m%d).tar.gz sessions/ data/ .env
```

## Support

For issues and questions:
1. Check logs: `tail -f logs/app.log`
2. Check Docker logs: `docker-compose logs -f`
3. Review API docs: http://localhost:8000/docs
