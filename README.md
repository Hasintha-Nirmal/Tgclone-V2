# Telegram Channel Automation System

A complete Python-based Telegram automation system for channel management, cloning, and synchronization.

## Features

- **Channel ID Extractor**: Fetch and display all joined channels with details
- **Private Channel Support**: Clone from private/restricted channels
- **Channel Cloner**: Clone messages with media preservation
- **Auto Sync**: Real-time message detection and cloning
- **Multi-Account Support**: Manage multiple Telegram accounts
- **Web Dashboard**: FastAPI-based UI for management
- **Storage Optimized**: Auto-delete files after upload
- **Docker Ready**: Full containerization support

## Quick Start

### Local Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. Authorize your Telegram account:
```bash
python authorize.py
```
Follow the prompts to enter the verification code from Telegram.

4. Run the application:
```bash
python main.py
```

5. Access dashboard:
```
http://localhost:8000
```

### Docker Setup

```bash
# Start the system
docker-compose up -d

# Authorize your Telegram account (REQUIRED on first run)
# Windows:
docker-authorize.bat

# Linux/Mac:
chmod +x docker-authorize.sh
./docker-authorize.sh
```

## Project Structure

```
telegram-automation/
├── app/
│   ├── auth/          # Authentication & session management
│   ├── scraper/       # Channel discovery & info extraction
│   ├── cloner/        # Message cloning logic
│   ├── uploader/      # Multi-account upload system
│   ├── worker/        # Background workers & auto-sync
│   ├── web/           # FastAPI web dashboard
│   └── utils/         # Shared utilities
├── config/            # Configuration files
├── docs/              # 📚 All documentation files
├── sessions/          # Telegram session files (persistent)
├── logs/              # Application logs (persistent)
├── downloads/         # Temporary media storage (auto-clean)
├── main.py            # Application entry point
├── manage.py          # Management CLI
└── docker-compose.yml # Docker orchestration
```

## Documentation

📚 **[Complete Documentation Index](docs/INDEX.md)** - Find everything here!

Quick links:
- **[NEXT_STEPS.md](docs/NEXT_STEPS.md)** - What to do right now ⭐
- [SETUP.md](docs/SETUP.md) - Detailed setup instructions
- [AUTHORIZATION.md](docs/AUTHORIZATION.md) - Authorization troubleshooting
- [RATE_LIMITING.md](docs/RATE_LIMITING.md) - Account protection & rate limits 🛡️
- [FEATURES.md](docs/FEATURES.md) - Complete feature list
- [VISUAL_GUIDE.md](docs/VISUAL_GUIDE.md) - Architecture diagrams
- [QUICKSTART.md](docs/QUICKSTART.md) - Quick start guide

## Important: First-Time Authorization

After starting the system, you MUST authorize your Telegram account:

**Docker:**
```bash
python manage.py authorize --docker
# Or use the helper scripts:
docker-authorize.bat    # Windows
./docker-authorize.sh   # Linux/Mac
```

**Local:**
```bash
python manage.py authorize
# Or directly:
python authorize.py
```

You'll receive a verification code in your Telegram app. Enter it when prompted.

## 🔒 Security Notice

The web dashboard is protected with HTTP Basic Authentication.

**Default credentials** (⚠️ CHANGE IMMEDIATELY):
```
Username: admin
Password: changeme123
```

**To change**: Edit `.env` file and restart:
```bash
ADMIN_USERNAME=your_username
ADMIN_PASSWORD=your_strong_password
docker-compose restart telegram-automation
```

See [SECURITY.md](docs/SECURITY.md) for complete security guide.

## Management CLI

Quick commands for common tasks:

```bash
# Start/Stop
python manage.py start --docker      # Start with Docker
python manage.py stop --docker       # Stop Docker
python manage.py restart --docker    # Restart

# Authorization
python manage.py authorize --docker  # Authorize account

# Monitoring
python manage.py status              # Check system status
python manage.py logs --docker       # View logs

# Maintenance
python manage.py cleanup --docker    # Clean old files
python manage.py check               # Run system checks
python manage.py shell               # Open Docker shell
```
