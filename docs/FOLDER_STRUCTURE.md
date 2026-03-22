# Documentation Folder Structure

All documentation has been organized in the `docs/` folder for better project organization.

## 📁 Documentation Files

### 🚀 Getting Started (Read These First)
- **[START_HERE.txt](START_HERE.txt)** - Quick reference card
- **[NEXT_STEPS.md](NEXT_STEPS.md)** ⭐ - Your immediate next steps
- **[QUICKSTART.md](QUICKSTART.md)** - 2-minute quick start guide

### 📖 Setup & Configuration
- **[SETUP.md](SETUP.md)** - Comprehensive setup guide
  - Local installation
  - Docker deployment
  - Configuration options
  - Production deployment
  - Troubleshooting

- **[AUTHORIZATION.md](AUTHORIZATION.md)** - Authorization guide
  - Fix "key not registered" error
  - 2FA setup
  - Multi-account authorization
  - Session management

### 📚 Reference Documentation
- **[FEATURES.md](FEATURES.md)** - Complete feature list
  - All capabilities
  - API endpoints
  - Technical specifications
  - System requirements

- **[VISUAL_GUIDE.md](VISUAL_GUIDE.md)** - Architecture & diagrams
  - System architecture
  - Data flow diagrams
  - User journey maps
  - Component interactions

- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Technical overview
  - File structure
  - Architecture details
  - Technical highlights
  - Implementation details

- **[PROJECT_TREE.txt](PROJECT_TREE.txt)** - File structure tree
  - Complete project layout
  - File descriptions
  - Statistics

### 📋 Index & Navigation
- **[INDEX.md](INDEX.md)** - Complete documentation index
  - All documentation links
  - Quick navigation
  - By use case
  - By topic

- **[README.md](README.md)** - Documentation overview
  - Quick navigation
  - Common use cases
  - Quick commands

### 🎉 Project Information
- **[COMPLETION_SUMMARY.md](COMPLETION_SUMMARY.md)** - Project completion
  - What was delivered
  - Statistics
  - Success metrics
  - Next steps

## 🗂️ Root Level Files

These files remain in the project root:

### Application Files
- `main.py` - Application entry point
- `authorize.py` - Authorization helper script
- `manage.py` - Management CLI
- `check-system.py` - System checker
- `requirements.txt` - Python dependencies

### Configuration
- `.env.example` - Configuration template
- `.gitignore` - Git exclusions

### Docker
- `Dockerfile` - Container image
- `docker-compose.yml` - Orchestration
- `.dockerignore` - Build exclusions
- `docker-authorize.sh` - Linux/Mac auth helper
- `docker-authorize.bat` - Windows auth helper

### Main Documentation
- `README.md` - Main project README (links to docs/)

## 📖 How to Navigate

### If you're just starting:
1. Read [START_HERE.txt](START_HERE.txt)
2. Follow [NEXT_STEPS.md](NEXT_STEPS.md)
3. Check [QUICKSTART.md](QUICKSTART.md)

### If you need setup help:
1. Read [SETUP.md](SETUP.md)
2. Check [AUTHORIZATION.md](AUTHORIZATION.md) if needed

### If you want to explore:
1. Browse [INDEX.md](INDEX.md)
2. Read [FEATURES.md](FEATURES.md)
3. Check [VISUAL_GUIDE.md](VISUAL_GUIDE.md)

### If you're troubleshooting:
1. Check [AUTHORIZATION.md](AUTHORIZATION.md)
2. Read [SETUP.md](SETUP.md) troubleshooting section
3. Run `python manage.py check`

## 🔗 Quick Links

- **Main README:** [../README.md](../README.md)
- **API Docs:** http://localhost:8000/docs
- **Dashboard:** http://localhost:8000
- **Health Check:** http://localhost:8000/health

## 📊 Documentation Statistics

- Total documentation files: 12
- Getting started guides: 3
- Setup guides: 2
- Reference docs: 5
- Index/navigation: 2

## 🎯 Documentation Goals

This documentation structure aims to:
- ✅ Provide quick access to essential information
- ✅ Separate concerns (getting started vs reference)
- ✅ Make navigation intuitive
- ✅ Support different user needs
- ✅ Keep project root clean

---

**Start here:** [NEXT_STEPS.md](NEXT_STEPS.md) 🚀
