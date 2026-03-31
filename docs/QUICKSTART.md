# Quick Start - You're Almost There! 🚀

Your system is running but needs authorization. Here's what to do:

## ⚡ IMMEDIATE ACTION REQUIRED

You're seeing this error:
```
The key is not registered in the system
```

This is normal on first run. Just authorize your account (takes 1 minute):

## Current Status ✓

- ✓ Docker container is running
- ✓ Web server is up (http://localhost:8000)
- ✓ Database is initialized
- ⚠ **Needs authorization** (that's why you see the error)

## Fix It Now (2 minutes)

### Step 1: Run Authorization Script

**Windows:**
```bash
docker-authorize.bat
```

**Linux/Mac:**
```bash
chmod +x docker-authorize.sh
./docker-authorize.sh
```

**Or manually:**
```bash
docker exec -it telegram-automation python authorize.py
```

### Step 2: Enter Verification Code

1. Check your Telegram app
2. You'll receive a message with a code (like `12345`)
3. Enter the code when prompted
4. If you have 2FA, enter your password too

### Step 3: Done!

The container will restart automatically. Then:

1. Open http://localhost:8000
2. Click "Channels" → "Refresh"
3. Your channels will load!

## What You'll See

After authorization, the dashboard will show:
- All your joined channels with IDs
- Ability to create clone jobs
- Real-time sync status
- System statistics

## Example: Clone a Channel

1. **Get Channel IDs:**
   - Go to "Channels" tab
   - Click "Refresh"
   - Copy the channel IDs (format: `-1001234567890`)

2. **Create Clone Job:**
   - Go to "Create Job" tab
   - Paste source channel ID
   - Paste target channel ID
   - Enable "Auto-Sync" for real-time cloning
   - Click "Create Job"

3. **Monitor Progress:**
   - Go to "Clone Jobs" tab
   - Watch real-time progress
   - Files are auto-deleted after upload (storage optimized!)

## Private Channels

Works with private/restricted channels! Just make sure:
- You're a member of the source channel
- You have admin rights in the target channel

## Troubleshooting

### Still seeing errors?

Check logs:
```bash
docker compose logs -f telegram-automation
```

### Need to re-authorize?

Delete session and try again:
```bash
docker exec telegram-automation rm sessions/*.session
docker compose restart telegram-automation
./docker-authorize.sh
```

### Wrong phone number?

Edit `.env` file and restart:
```bash
nano .env  # or use any text editor
docker compose restart telegram-automation
```

## Advanced Features

### Multi-Account Upload

Add more accounts in `.env`:
```env
TELEGRAM_API_ID_2=your_api_id
TELEGRAM_API_HASH_2=your_api_hash  
TELEGRAM_PHONE_2=+1234567890
```

System will automatically rotate between accounts to avoid rate limits!

### Auto-Sync

Enable "Auto-Sync" when creating a job. The system will:
- Check for new messages every 30 seconds (configurable)
- Automatically clone new content
- Run in background
- Resume after restarts

### Storage Management

Files are automatically deleted after upload. Check disk usage in dashboard.

Manual cleanup:
```bash
curl -X POST http://localhost:8000/api/system/cleanup
```

## API Access

Full REST API available at:
```
http://localhost:8000/docs
```

Use it to:
- Integrate with other tools
- Automate workflows
- Build custom interfaces

## Need Help?

1. Check [AUTHORIZATION.md](AUTHORIZATION.md) for auth issues
2. Check [SETUP.md](SETUP.md) for detailed setup
3. View logs: `docker compose logs -f`
4. API docs: http://localhost:8000/docs

## Your Next Steps

1. ✓ Authorize (run the script above)
2. ✓ Refresh channels in dashboard
3. ✓ Create your first clone job
4. ✓ Enable auto-sync for real-time cloning

That's it! You're ready to automate Telegram channels. 🎉
