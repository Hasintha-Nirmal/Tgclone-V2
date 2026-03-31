# What To Do Right Now 🎯

Your Docker container is running but needs authorization. Here's exactly what to do:

## Step 1: Authorize Your Account (1 minute)

Run this command:

```bash
python manage.py authorize --docker
```

Or use the helper script:
```bash
# Windows
docker-authorize.bat

# Linux/Mac
chmod +x docker-authorize.sh
./docker-authorize.sh
```

### What Will Happen:

1. Script will connect to Telegram
2. You'll see: "Check your Telegram app for the verification code"
3. Open Telegram on your phone/desktop
4. You'll receive a message with a code (like `12345`)
5. Enter the code in the terminal
6. If you have 2FA, enter your password
7. Done! Container will restart automatically

## Step 2: Verify It Works

Open your browser:
```
http://localhost:8000
```

You should see the dashboard. Click "Channels" → "Refresh" to load your channels.

## Step 3: Create Your First Clone Job

1. **Get Channel IDs:**
   - In the dashboard, go to "Channels" tab
   - Click "Refresh" button
   - You'll see all your channels with their IDs
   - Copy the source channel ID (format: `-1001234567890`)
   - Copy the target channel ID

2. **Create Job:**
   - Go to "Create Job" tab
   - Paste source channel ID
   - Paste target channel ID
   - Optional: Set start message ID (leave empty to clone all)
   - Optional: Enable "Auto-Sync" for real-time cloning
   - Click "Create Job"

3. **Monitor:**
   - Go to "Clone Jobs" tab
   - Watch the progress in real-time
   - Files are automatically deleted after upload

## Common Issues & Solutions

### Issue: "The key is not registered in the system"
**Solution:** This is what you're seeing now. Just run the authorization (Step 1 above).

### Issue: Can't run docker-authorize.bat
**Solution:** Use the Python command instead:
```bash
python manage.py authorize --docker
```

### Issue: "Container not found"
**Solution:** Start the container first:
```bash
docker compose up -d
```

### Issue: Wrong phone number in .env
**Solution:** 
1. Stop container: `docker compose down`
2. Edit `.env` file with correct phone number
3. Delete session: `rm sessions/*.session`
4. Start again: `docker compose up -d`
5. Authorize: `python manage.py authorize --docker`

## Quick Commands Reference

```bash
# Check status
python manage.py status

# View logs
python manage.py logs --docker

# Restart container
docker compose restart

# Stop everything
docker compose down

# Start again
docker compose up -d
```

## What You Can Do After Authorization

### 1. Clone Private Channels
Works with private/restricted channels! Just make sure you're a member.

### 2. Auto-Sync
Enable auto-sync when creating a job. New messages will be cloned automatically every 30 seconds.

### 3. Multi-Account
Add more accounts in `.env` to avoid rate limits:
```env
TELEGRAM_API_ID_2=your_api_id
TELEGRAM_API_HASH_2=your_api_hash
TELEGRAM_PHONE_2=+1234567890
```

### 4. API Access
Full REST API at: http://localhost:8000/docs

## Storage Optimization

Files are automatically deleted after upload. Check disk usage in the dashboard.

Manual cleanup:
```bash
python manage.py cleanup --docker
```

## Need Help?

1. **Check logs:**
   ```bash
   docker compose logs -f telegram-automation
   ```

2. **Check system status:**
   ```bash
   python manage.py status
   ```

3. **Run system checks:**
   ```bash
   python manage.py check
   ```

4. **Read documentation:**
   - [AUTHORIZATION.md](AUTHORIZATION.md) - Auth issues
   - [SETUP.md](SETUP.md) - Detailed setup
   - [FEATURES.md](FEATURES.md) - All features
   - [QUICKSTART.md](QUICKSTART.md) - Quick guide

## Your Exact Next Command

Based on your current situation, run this now:

```bash
python manage.py authorize --docker
```

Then follow the prompts. That's it! 🚀

## After Authorization

Once authorized, you can:
- ✓ View all your channels
- ✓ Clone any channel (public or private)
- ✓ Set up auto-sync
- ✓ Monitor everything via dashboard
- ✓ Use the REST API

The system will remember your session, so you won't need to authorize again unless you delete the session file.

## Pro Tips

1. **Enable Auto-Sync** for real-time cloning
2. **Use multiple accounts** to avoid rate limits
3. **Check disk usage** in the dashboard regularly
4. **Monitor logs** for any issues
5. **Backup sessions/** directory (contains your auth)

## That's It!

You're one command away from having a fully functional Telegram automation system. Just run the authorization and you're good to go! 🎉
