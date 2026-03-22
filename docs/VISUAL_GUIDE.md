# Visual Guide - How Everything Works

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACE                          │
│                                                             │
│  Web Dashboard (http://localhost:8000)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                │
│  │ Channels │  │   Jobs   │  │  System  │                │
│  └──────────┘  └──────────┘  └──────────┘                │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                          │
│                                                             │
│  REST API Endpoints                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Channels   │  │     Jobs     │  │    System    │    │
│  │   /api/...   │  │   /api/...   │  │   /api/...   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   CORE MODULES                              │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Session │  │ Scraper  │  │  Cloner  │  │ Uploader │  │
│  │ Manager  │  │          │  │          │  │          │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                │
│  │  Worker  │  │ Database │  │ Storage  │                │
│  │  (Sync)  │  │          │  │ Manager  │                │
│  └──────────┘  └──────────┘  └──────────┘                │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  TELEGRAM API                               │
│                                                             │
│  Telethon Client → Telegram Servers                        │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow - Clone Operation

```
1. USER ACTION
   │
   ├─→ Create Clone Job (Web Dashboard)
   │
   ▼
2. API REQUEST
   │
   ├─→ POST /api/jobs/clone
   │   {
   │     source_channel: "-1001234567890",
   │     target_channel: "-1009876543210",
   │     auto_sync: true
   │   }
   │
   ▼
3. JOB CREATION
   │
   ├─→ Generate Job ID
   ├─→ Save to Database
   ├─→ Start Background Task
   │
   ▼
4. MESSAGE CLONING
   │
   ├─→ Get Telegram Client
   ├─→ Fetch Messages from Source
   │   │
   │   ├─→ For each message:
   │   │   │
   │   │   ├─→ Has Media?
   │   │   │   │
   │   │   │   ├─→ YES: Download to /downloads/
   │   │   │   │         │
   │   │   │   │         ├─→ Upload to Target
   │   │   │   │         │
   │   │   │   │         └─→ Delete File (auto-cleanup)
   │   │   │   │
   │   │   │   └─→ NO: Send Text Only
   │   │   │
   │   │   └─→ Update Progress
   │   │
   │   └─→ Complete
   │
   ▼
5. AUTO-SYNC (if enabled)
   │
   ├─→ Background Worker Monitors
   │   │
   │   ├─→ Every 30 seconds:
   │   │   │
   │   │   ├─→ Check for New Messages
   │   │   │
   │   │   ├─→ Clone New Messages
   │   │   │
   │   │   └─→ Update Sync State
   │   │
   │   └─→ Repeat Forever
   │
   ▼
6. COMPLETION
   │
   ├─→ Update Job Status
   ├─→ Cleanup Temp Files
   └─→ Show in Dashboard
```

## Storage Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    PERSISTENT STORAGE                       │
│                                                             │
│  sessions/                                                  │
│  ├─→ 94786894833.session  ← Your Telegram session         │
│  └─→ (other accounts)                                      │
│                                                             │
│  logs/                                                      │
│  └─→ app.log  ← All activity and errors                   │
│                                                             │
│  data/                                                      │
│  └─→ app.db  ← SQLite database                            │
│      ├─→ channels                                          │
│      ├─→ clone_jobs                                        │
│      ├─→ sync_state                                        │
│      └─→ accounts                                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   TEMPORARY STORAGE                         │
│                                                             │
│  downloads/                                                 │
│  ├─→ job_id_1/                                             │
│  │   ├─→ photo_123.jpg  ← Downloaded                      │
│  │   └─→ video_456.mp4  ← Uploaded → DELETED ✓           │
│  │                                                          │
│  └─→ job_id_2/                                             │
│      └─→ (auto-cleaned after 24h)                         │
└─────────────────────────────────────────────────────────────┘
```

## Multi-Account Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  ACCOUNT ROTATION                           │
│                                                             │
│  Account 1 (+94786894833)                                  │
│  │                                                          │
│  ├─→ Upload File 1  ✓                                      │
│  ├─→ Upload File 2  ✓                                      │
│  ├─→ Upload File 3  ✗ FloodWait (60s)                     │
│  │                                                          │
│  │   Switch to Account 2                                   │
│  │   │                                                      │
│  │   ├─→ Upload File 3  ✓                                  │
│  │   ├─→ Upload File 4  ✓                                  │
│  │   └─→ Continue...                                       │
│  │                                                          │
│  └─→ (After 60s) Back to Account 1                        │
│                                                             │
│  Result: No waiting, continuous uploads!                   │
└─────────────────────────────────────────────────────────────┘
```

## Authorization Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  FIRST TIME SETUP                           │
│                                                             │
│  1. Run: python manage.py authorize --docker               │
│     │                                                       │
│     ▼                                                       │
│  2. Script connects to Telegram                            │
│     │                                                       │
│     ▼                                                       │
│  3. Telegram sends code to your phone                      │
│     │                                                       │
│     ▼                                                       │
│  4. You enter code: 12345                                  │
│     │                                                       │
│     ▼                                                       │
│  5. Session saved to: sessions/94786894833.session         │
│     │                                                       │
│     ▼                                                       │
│  6. Container restarts                                     │
│     │                                                       │
│     ▼                                                       │
│  7. ✓ Ready to use!                                        │
│                                                             │
│  Next time: No authorization needed (session persists)     │
└─────────────────────────────────────────────────────────────┘
```

## Dashboard Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    WEB DASHBOARD                            │
│                                                             │
│  http://localhost:8000                                     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  CHANNELS TAB                                       │  │
│  │                                                     │  │
│  │  [Refresh Button]  [Search: ___________]          │  │
│  │                                                     │  │
│  │  ┌──────────────────────────────────────────────┐ │  │
│  │  │ Title        │ Channel ID      │ Members     │ │  │
│  │  ├──────────────────────────────────────────────┤ │  │
│  │  │ My Channel   │ -1001234567890  │ 1,234      │ │  │
│  │  │ Tech News    │ -1009876543210  │ 5,678      │ │  │
│  │  └──────────────────────────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  CREATE JOB TAB                                     │  │
│  │                                                     │  │
│  │  Source Channel ID: [-1001234567890]              │  │
│  │  Target Channel ID: [-1009876543210]              │  │
│  │  Start Message ID:  [optional]                     │  │
│  │  Limit:            [optional]                      │  │
│  │  [✓] Enable Auto-Sync                             │  │
│  │                                                     │  │
│  │  [Create Job]                                      │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  JOBS TAB                                           │  │
│  │                                                     │  │
│  │  ┌──────────────────────────────────────────────┐ │  │
│  │  │ Job ID  │ Status    │ Progress  │ Actions   │ │  │
│  │  ├──────────────────────────────────────────────┤ │  │
│  │  │ abc123  │ Running   │ 45/100    │ [Stop]    │ │  │
│  │  │ def456  │ Completed │ 200/200   │ [Delete]  │ │  │
│  │  └──────────────────────────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   ERROR SCENARIOS                           │
│                                                             │
│  FloodWaitError                                            │
│  │                                                          │
│  ├─→ Detect wait time (e.g., 60 seconds)                  │
│  ├─→ Mark account as unavailable                          │
│  ├─→ Switch to next account                               │
│  ├─→ Continue operations                                   │
│  └─→ After wait time, account available again             │
│                                                             │
│  Network Error                                             │
│  │                                                          │
│  ├─→ Retry with exponential backoff                       │
│  │   ├─→ Attempt 1: Wait 1s                              │
│  │   ├─→ Attempt 2: Wait 2s                              │
│  │   └─→ Attempt 3: Wait 4s                              │
│  └─→ If all fail, mark job as failed                     │
│                                                             │
│  File Download Error                                       │
│  │                                                          │
│  ├─→ Log error                                            │
│  ├─→ Skip message                                         │
│  └─→ Continue with next message                           │
│                                                             │
│  Authorization Error                                       │
│  │                                                          │
│  ├─→ Log error                                            │
│  ├─→ Show in dashboard                                    │
│  └─→ User must re-authorize                               │
└─────────────────────────────────────────────────────────────┘
```

## Docker Container Structure

```
┌─────────────────────────────────────────────────────────────┐
│                  DOCKER CONTAINER                           │
│                                                             │
│  telegram-automation                                       │
│  │                                                          │
│  ├─→ /app/                                                 │
│  │   ├─→ main.py                                          │
│  │   ├─→ authorize.py                                     │
│  │   ├─→ app/                                             │
│  │   ├─→ config/                                          │
│  │   └─→ requirements.txt                                 │
│  │                                                          │
│  ├─→ /app/sessions/  ← Volume (persistent)                │
│  ├─→ /app/logs/      ← Volume (persistent)                │
│  ├─→ /app/data/      ← Volume (persistent)                │
│  └─→ /app/downloads/ ← Volume (temporary)                 │
│                                                             │
│  Exposed Port: 8000                                        │
│  Network: telegram-net                                     │
└─────────────────────────────────────────────────────────────┘
```

## Complete User Journey

```
1. SETUP
   │
   ├─→ docker-compose up -d
   │
   ▼
2. AUTHORIZE
   │
   ├─→ python manage.py authorize --docker
   ├─→ Enter code from Telegram
   │
   ▼
3. DISCOVER CHANNELS
   │
   ├─→ Open http://localhost:8000
   ├─→ Click "Channels" → "Refresh"
   ├─→ See all your channels with IDs
   │
   ▼
4. CREATE CLONE JOB
   │
   ├─→ Copy source channel ID
   ├─→ Copy target channel ID
   ├─→ Go to "Create Job" tab
   ├─→ Paste IDs
   ├─→ Enable auto-sync
   ├─→ Click "Create Job"
   │
   ▼
5. MONITOR PROGRESS
   │
   ├─→ Go to "Jobs" tab
   ├─→ Watch real-time progress
   ├─→ Files auto-deleted after upload
   │
   ▼
6. AUTO-SYNC RUNNING
   │
   ├─→ New messages detected automatically
   ├─→ Cloned in real-time
   ├─→ Runs in background forever
   │
   ▼
7. ENJOY! 🎉
```

This visual guide shows how all components work together to create a seamless Telegram automation experience!
