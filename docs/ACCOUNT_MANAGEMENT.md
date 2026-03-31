# Account Management via Web Dashboard

You can now manage Telegram accounts directly from the web dashboard!

## 🎯 Features

- ✅ Login accounts via web interface
- ✅ Support for 2FA (Two-Factor Authentication)
- ✅ View all logged-in accounts
- ✅ Logout accounts and remove sessions
- ✅ Multi-account management
- ✅ No command line needed!

## 📱 How to Add an Account

### Step 1: Access Accounts Tab

1. Open the web dashboard: `http://localhost:8000`
2. Click on the **"Accounts"** tab
3. Click **"Add Account"** button

### Step 2: Enter Account Details

You'll need:
- **Phone Number**: Include country code (e.g., `+1234567890`)
- **API ID**: Get from https://my.telegram.org
- **API Hash**: Get from https://my.telegram.org

### Step 3: Verify Code

1. Click **"Send Code"**
2. Check your Telegram app for the verification code
3. Enter the code in the web form
4. Click **"Verify Code"**

### Step 4: 2FA (If Enabled)

If your account has two-factor authentication:
1. You'll be prompted for your 2FA password
2. Enter your password
3. Click **"Verify Password"**

### Step 5: Done!

Your account is now logged in and ready to use!

## 🔐 Two-Factor Authentication (2FA)

The system fully supports accounts with 2FA enabled.

### What is 2FA?

Two-factor authentication adds an extra layer of security to your Telegram account. When enabled, you need both:
1. Verification code (sent to your Telegram app)
2. Password (that you set up)

### How It Works

1. Enter phone, API ID, and API Hash
2. Receive and enter verification code
3. System detects 2FA is enabled
4. Enter your 2FA password
5. Successfully logged in!

### Setting Up 2FA

To enable 2FA on your Telegram account:
1. Open Telegram app
2. Go to Settings → Privacy and Security
3. Enable Two-Step Verification
4. Set a password

## 👥 Managing Multiple Accounts

### View All Accounts

The **Accounts** tab shows:
- Phone number
- Full name
- Username
- User ID
- Logout button

### Switch Between Accounts

The system automatically uses available accounts for:
- Load balancing
- FloodWait handling
- Multi-account uploads

### Account Rotation

When cloning:
- System distributes load across all logged-in accounts
- Automatically switches if one account hits rate limits
- Reduces risk of bans

## 🚪 Logging Out

### How to Logout

1. Go to **Accounts** tab
2. Find the account you want to logout
3. Click **"Logout"** button
4. Confirm the action

### What Happens

When you logout:
- ✅ Account is logged out from Telegram
- ✅ Session file is deleted
- ✅ Account removed from active accounts
- ✅ **Channel list is cleared** (channels were fetched with this account)
- ✅ Can't be used for cloning anymore

### Important Note

⚠️ **Logging out will clear the channel list!**

Since channels are fetched using the logged-in account, when you logout:
- All channels in the "Channels" tab will be removed
- You'll need to login again and refresh channels
- This ensures data consistency

### Re-Login

To use the account again:
1. Click **"Add Account"**
2. Follow the login process
3. Go to "Channels" tab
4. Click "Refresh" to reload channels
5. Account and channels will be available again

## 🔒 Security Notes

### Session Files

- Session files are stored in `sessions/` directory
- Each account has its own session file
- Session files contain authentication tokens
- Keep them secure!

### API Credentials

- API ID and Hash are required for each account
- Get them from https://my.telegram.org
- Each account can use different API credentials
- Or use the same credentials for all accounts

### Best Practices

1. **Use Strong 2FA Passwords**
   - Minimum 8 characters
   - Mix of letters, numbers, symbols
   - Don't reuse passwords

2. **Logout Unused Accounts**
   - Remove accounts you're not using
   - Reduces security risk
   - Frees up resources

3. **Monitor Account Activity**
   - Check for unauthorized access
   - Review Telegram's active sessions
   - Logout suspicious sessions

## 📊 Account Status

### Logged In

Accounts shown in the Accounts tab are:
- ✅ Authenticated with Telegram
- ✅ Available for cloning
- ✅ Can be used immediately

### Not Logged In

If an account is not shown:
- ❌ Not authenticated
- ❌ Can't be used for cloning
- ➕ Click "Add Account" to login

## 🛠️ Troubleshooting

### "Invalid verification code"

**Problem**: Code is rejected

**Solutions**:
- Make sure you entered the correct code
- Code expires after a few minutes
- Request a new code if needed
- Check for typos

### "Invalid password"

**Problem**: 2FA password is rejected

**Solutions**:
- Double-check your password
- Make sure Caps Lock is off
- Try resetting 2FA in Telegram app
- Contact Telegram support if forgotten

### "Phone number is invalid"

**Problem**: Phone number format is wrong

**Solutions**:
- Include country code (e.g., `+1` for US)
- No spaces or dashes
- Format: `+1234567890`
- Check Telegram's supported countries

### "API ID/Hash is invalid"

**Problem**: Credentials are wrong

**Solutions**:
- Verify at https://my.telegram.org
- Copy-paste to avoid typos
- Make sure you're using the correct app
- Create new API credentials if needed

### Account Not Showing

**Problem**: Logged in but not visible

**Solutions**:
- Refresh the page
- Check browser console for errors
- Restart the container
- Check logs: `docker compose logs`

### Can't Logout

**Problem**: Logout button doesn't work

**Solutions**:
- Check browser console
- Try refreshing the page
- Manually delete session file:
  ```bash
  rm sessions/PHONE_NUMBER.session
  docker compose restart
  ```

## 💡 Tips & Tricks

### Tip 1: Use Multiple Accounts

- Add 2-3 accounts for better performance
- System automatically distributes load
- Reduces risk of rate limits

### Tip 2: Keep One Account for Testing

- Use one account for testing
- Use others for production cloning
- Easier to troubleshoot issues

### Tip 3: Document Your Accounts

Keep track of:
- Which phone numbers you're using
- Which API credentials belong to which account
- 2FA passwords (in a secure password manager)

### Tip 4: Regular Maintenance

- Review logged-in accounts monthly
- Logout unused accounts
- Update 2FA passwords regularly
- Check Telegram's active sessions

## 🎓 Example Workflow

### Adding Your First Account

```
1. Open http://localhost:8000
2. Click "Accounts" tab
3. Click "Add Account"
4. Enter: +1234567890
5. Enter: API ID from my.telegram.org
6. Enter: API Hash from my.telegram.org
7. Click "Send Code"
8. Check Telegram app
9. Enter code: 12345
10. Click "Verify Code"
11. (If 2FA) Enter password
12. Done! Account is ready
```

### Adding a Second Account

```
1. Click "Add Account" again
2. Enter different phone number
3. Follow same process
4. Now you have 2 accounts!
5. System will use both for cloning
```

### Removing an Account

```
1. Go to "Accounts" tab
2. Find the account
3. Click "Logout"
4. Confirm
5. Account removed!
```

## 📈 Benefits

### Before (Command Line)

- ❌ Need to run Python scripts
- ❌ Manual code entry in terminal
- ❌ Complex for non-technical users
- ❌ Can't see logged-in accounts easily

### After (Web Dashboard)

- ✅ User-friendly web interface
- ✅ Visual account management
- ✅ Easy for anyone to use
- ✅ See all accounts at a glance
- ✅ One-click logout
- ✅ Built-in 2FA support

## 🔗 Related Documentation

- [SECURITY.md](SECURITY.md) - Security best practices
- [SETUP.md](SETUP.md) - Initial setup guide
- [AUTHORIZATION.md](AUTHORIZATION.md) - Authorization troubleshooting

---

**Now you can manage all your Telegram accounts from the web dashboard!** 🎉
