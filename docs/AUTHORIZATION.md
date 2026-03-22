# Authorization Guide

## The Issue

You're seeing this error:
```
The key is not registered in the system
```

This means your Telegram account needs to be authorized with a verification code.

## Quick Fix (Docker)

### Windows:
```bash
docker-authorize.bat
```

### Linux/Mac:
```bash
chmod +x docker-authorize.sh
./docker-authorize.sh
```

### Manual Method:

1. **Enter the container:**
```bash
docker exec -it telegram-automation bash
```

2. **Run authorization script:**
```bash
python authorize.py
```

3. **Follow the prompts:**
   - Check your Telegram app for the verification code
   - Enter the code when prompted
   - If you have 2FA, enter your password

4. **Exit and restart:**
```bash
exit
docker-compose restart telegram-automation
```

## Quick Fix (Local Installation)

```bash
python authorize.py
```

Follow the prompts to enter your verification code.

## What Happens During Authorization

1. Script connects to Telegram servers
2. Sends verification code to your Telegram app
3. You enter the code
4. Session is saved to `sessions/` directory
5. Future connections use this session (no code needed)

## Verification Code

The code will be sent to your Telegram app as a message from "Telegram". It looks like:
```
12345
```

Just enter the numbers when prompted.

## Two-Factor Authentication (2FA)

If you have 2FA enabled:
1. Enter the verification code first
2. Then enter your 2FA password when prompted

## Troubleshooting

### "Phone number is invalid"
- Check your phone number format in `.env`
- Should include country code: `+1234567890`

### "Code is invalid"
- Make sure you're entering the latest code
- Codes expire after a few minutes
- Request a new code if needed

### "Session file is corrupted"
Delete the session file and try again:
```bash
# Docker
docker exec telegram-automation rm sessions/*.session

# Local
rm sessions/*.session
```

Then run authorization again.

### "API ID/Hash is invalid"
- Verify your credentials at https://my.telegram.org
- Check `.env` file has correct values
- No quotes needed in `.env`

## After Authorization

Once authorized:
1. Container will restart automatically
2. Dashboard will work at http://localhost:8000
3. You can refresh channels and start cloning
4. Session persists across restarts (no need to authorize again)

## Multiple Accounts

To authorize additional accounts:

1. Add credentials to `.env`:
```env
TELEGRAM_API_ID_2=your_api_id
TELEGRAM_API_HASH_2=your_api_hash
TELEGRAM_PHONE_2=+1234567890
```

2. Restart the application
3. Run authorization for the second account

## Security Notes

- Session files are stored in `sessions/` directory
- Keep these files secure (they provide access to your account)
- Never share session files
- Add `sessions/` to `.gitignore` (already done)
- In Docker, sessions are persisted in a volume

## Need Help?

Check the logs:
```bash
# Docker
docker-compose logs -f telegram-automation

# Local
tail -f logs/app.log
```

Look for authorization-related messages.
