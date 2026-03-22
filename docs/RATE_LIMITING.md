# Rate Limiting & Account Protection

The system includes multiple layers of protection to prevent your Telegram account from being banned or rate-limited.

## 🛡️ Protection Mechanisms

### 1. Message Delays
- **Text messages**: 1 second delay between each message
- **Media messages**: 2 seconds delay between each message (media is more suspicious)
- **Configurable**: Adjust in `.env` file

### 2. Periodic Breaks
- Takes a 5-second break every 10 messages
- Prevents sustained high-speed activity
- Makes the activity look more natural

### 3. Hourly Rate Limit
- Maximum 200 messages per hour (default)
- Automatically pauses for 1 hour if limit is reached
- Protects against detection algorithms

### 4. FloodWait Handling
- Automatically detects Telegram's FloodWait errors
- Switches to another account if available
- Waits the required time before retrying

### 5. Multi-Account Rotation
- Distributes load across multiple accounts
- Reduces risk per account
- Automatic failover

## ⚙️ Configuration

Edit your `.env` file to customize rate limiting:

```env
# Rate Limiting (Account Protection)
DELAY_BETWEEN_MESSAGES=1.0        # Seconds between text messages
DELAY_BETWEEN_MEDIA=2.0           # Seconds between media messages
BREAK_EVERY_N_MESSAGES=10         # Take break every N messages
BREAK_DURATION=5.0                # Break duration in seconds
MAX_MESSAGES_PER_HOUR=200         # Maximum messages per hour
```

## 📊 Recommended Settings

### Conservative (Safest)
```env
DELAY_BETWEEN_MESSAGES=2.0
DELAY_BETWEEN_MEDIA=4.0
BREAK_EVERY_N_MESSAGES=5
BREAK_DURATION=10.0
MAX_MESSAGES_PER_HOUR=100
```
- Best for: New accounts, important accounts
- Speed: ~50-100 messages/hour
- Risk: Very low

### Balanced (Default)
```env
DELAY_BETWEEN_MESSAGES=1.0
DELAY_BETWEEN_MEDIA=2.0
BREAK_EVERY_N_MESSAGES=10
BREAK_DURATION=5.0
MAX_MESSAGES_PER_HOUR=200
```
- Best for: Most users
- Speed: ~150-200 messages/hour
- Risk: Low

### Aggressive (Faster, Higher Risk)
```env
DELAY_BETWEEN_MESSAGES=0.5
DELAY_BETWEEN_MEDIA=1.0
BREAK_EVERY_N_MESSAGES=20
BREAK_DURATION=3.0
MAX_MESSAGES_PER_HOUR=300
```
- Best for: Established accounts, urgent needs
- Speed: ~250-300 messages/hour
- Risk: Medium

## 🚨 Warning Signs

Watch for these signs that you might be rate-limited:

1. **FloodWait errors** - Telegram is asking you to slow down
2. **Failed uploads** - Messages not sending
3. **Account restrictions** - Can't send messages temporarily

If you see these:
1. Stop all cloning jobs immediately
2. Wait 24 hours
3. Use more conservative settings
4. Consider using multiple accounts

## 💡 Best Practices

### 1. Use Multiple Accounts
- Distribute load across 2-3 accounts
- Each account stays well under limits
- System automatically rotates

### 2. Clone During Off-Peak Hours
- Less likely to trigger detection
- Better performance
- Lower risk

### 3. Start Slow
- Use conservative settings initially
- Gradually increase if no issues
- Monitor for warnings

### 4. Don't Clone Too Much at Once
- Break large jobs into smaller batches
- Take breaks between batches
- Use auto-sync for ongoing cloning

### 5. Vary Your Activity
- Don't clone 24/7
- Mix with normal Telegram usage
- Make activity look natural

## 📈 Performance vs Safety

| Setting | Messages/Hour | Safety | Use Case |
|---------|---------------|--------|----------|
| Conservative | 50-100 | ⭐⭐⭐⭐⭐ | New accounts, VIP accounts |
| Balanced | 150-200 | ⭐⭐⭐⭐ | Daily use, most users |
| Aggressive | 250-300 | ⭐⭐⭐ | Urgent needs, established accounts |
| No Limits | 500+ | ⭐ | Not recommended! |

## 🔍 Monitoring

Check logs for rate limiting activity:

```bash
# Docker
docker-compose logs -f telegram-automation | grep "rate limit"

# Local
tail -f logs/app.log | grep "rate limit"
```

You'll see messages like:
```
Processed 10 messages, taking a 5s break...
Hourly rate limit reached (200 messages/hour). Waiting 3600 seconds...
```

## 🛠️ Troubleshooting

### "FloodWaitError: A wait of X seconds is required"
**Solution**: 
- System automatically handles this
- If using single account, it will wait
- If using multiple accounts, it switches to another

### "Hourly rate limit reached"
**Solution**:
- This is normal and protective
- System will automatically resume after 1 hour
- Consider lowering `MAX_MESSAGES_PER_HOUR`

### "Account temporarily restricted"
**Solution**:
1. Stop all cloning immediately
2. Wait 24-48 hours
3. Use more conservative settings
4. Add more accounts to distribute load

## 📝 Notes

- **Telegram's limits vary** by account age, activity, and other factors
- **These settings are conservative** - most accounts can handle more
- **Start conservative** and increase gradually
- **Monitor your account** for any warnings
- **Use auto-sync** for ongoing cloning (it's slower but safer)

## 🎯 Recommended Strategy

For best results:

1. **Initial Clone**: Use balanced settings to clone existing messages
2. **Auto-Sync**: Enable auto-sync for new messages (checks every 30s)
3. **Multiple Accounts**: Add 2-3 accounts for load distribution
4. **Monitor**: Check logs regularly for issues
5. **Adjust**: Fine-tune settings based on your experience

---

**Remember**: It's better to be slow and safe than fast and banned! 🛡️
