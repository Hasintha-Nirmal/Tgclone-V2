# Security Guide

## 🔒 Web Dashboard Authentication

The web dashboard is now protected with HTTP Basic Authentication.

### Default Credentials

⚠️ **IMPORTANT**: Change these immediately!

```
Username: admin
Password: changeme123
```

### Changing Credentials

Edit your `.env` file:

```env
ADMIN_USERNAME=your_username
ADMIN_PASSWORD=your_strong_password
```

Then restart:
```bash
docker-compose restart telegram-automation
```

### Password Requirements

For production use:
- Minimum 12 characters
- Mix of uppercase, lowercase, numbers, symbols
- Don't use common words or patterns
- Don't reuse passwords from other services

### Example Strong Password

```env
ADMIN_USERNAME=telegram_admin
ADMIN_PASSWORD=Tg!2024$Secure#Pass@789
```

## 🛡️ Security Best Practices

### 1. Change Default Credentials

The first thing you should do after installation:

```bash
# Edit .env file
nano .env

# Change these lines:
ADMIN_USERNAME=your_custom_username
ADMIN_PASSWORD=your_strong_password

# Restart
docker-compose restart telegram-automation
```

### 2. Use HTTPS in Production

For production deployment, use a reverse proxy with SSL:

**Nginx Example:**
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Restrict Network Access

**Docker Network Isolation:**
```yaml
# docker-compose.yml
services:
  telegram-automation:
    ports:
      - "127.0.0.1:8000:8000"  # Only localhost
```

**Firewall Rules:**
```bash
# Allow only from specific IP
sudo ufw allow from 192.168.1.100 to any port 8000

# Or use SSH tunnel
ssh -L 8000:localhost:8000 user@server
```

### 4. Secure Session Files

Session files contain your Telegram authentication:

```bash
# Set proper permissions
chmod 600 sessions/*.session

# In Docker, sessions are in a volume
docker volume inspect playground_telegram-sessions
```

### 5. Environment Variables

Never commit `.env` to version control:

```bash
# Already in .gitignore
echo ".env" >> .gitignore
```

### 6. Regular Updates

Keep the system updated:

```bash
# Pull latest changes
git pull

# Rebuild containers
docker-compose build --no-cache
docker-compose up -d
```

## 🔐 Access Control

### Who Can Access What

| Resource | Authentication | Notes |
|----------|---------------|-------|
| Web Dashboard | ✅ Required | HTTP Basic Auth |
| API Endpoints | ✅ Required | Same credentials |
| Health Check | ❌ Public | `/health` endpoint |
| Telegram Sessions | 🔒 File System | Protected by OS permissions |

### API Authentication

All API endpoints require authentication:

```bash
# Using curl
curl -u admin:password http://localhost:8000/api/channels/list

# Using Python
import requests
from requests.auth import HTTPBasicAuth

response = requests.get(
    'http://localhost:8000/api/channels/list',
    auth=HTTPBasicAuth('admin', 'password')
)
```

### Browser Authentication

When you access the dashboard:
1. Browser will prompt for username/password
2. Credentials are cached for the session
3. Close browser to log out

## 🚨 Security Checklist

Before going to production:

- [ ] Changed default admin username
- [ ] Set strong admin password
- [ ] Configured HTTPS/SSL
- [ ] Restricted network access
- [ ] Set proper file permissions
- [ ] Reviewed firewall rules
- [ ] Enabled logging
- [ ] Set up backups
- [ ] Documented access procedures
- [ ] Tested authentication

## 🔍 Monitoring

### Check Access Logs

```bash
# Docker
docker-compose logs telegram-automation | grep "401\|403"

# Look for failed auth attempts
docker-compose logs telegram-automation | grep "Invalid credentials"
```

### Failed Login Attempts

The system logs all authentication attempts:

```
INFO: 203.189.185.223:1700 - "GET / HTTP/1.1" 401 Unauthorized
```

## 🛠️ Troubleshooting

### "Authentication Required" Loop

**Problem**: Browser keeps asking for credentials

**Solutions**:
1. Clear browser cache and cookies
2. Try incognito/private mode
3. Check credentials in `.env` file
4. Restart the container

### Can't Remember Password

**Solution**: Reset in `.env` file

```bash
# Edit .env
nano .env

# Change password
ADMIN_PASSWORD=new_password

# Restart
docker-compose restart telegram-automation
```

### Locked Out

**Solution**: Access container directly

```bash
# Enter container
docker exec -it telegram-automation bash

# Edit .env
vi .env

# Exit and restart
exit
docker-compose restart telegram-automation
```

## 📝 Additional Security Measures

### 1. Rate Limiting (Future Enhancement)

Consider adding rate limiting for login attempts:
- Max 5 attempts per IP per minute
- Temporary IP ban after 10 failed attempts

### 2. Two-Factor Authentication (Future Enhancement)

For high-security environments:
- TOTP (Time-based One-Time Password)
- Hardware keys (YubiKey)

### 3. Audit Logging

Enable detailed logging:

```env
LOG_LEVEL=DEBUG
```

### 4. Regular Security Audits

- Review access logs weekly
- Check for unauthorized access attempts
- Update dependencies regularly
- Review user permissions

## 🆘 Security Incident Response

If you suspect unauthorized access:

1. **Immediately**:
   - Change admin password
   - Restart the system
   - Check logs for suspicious activity

2. **Investigate**:
   - Review access logs
   - Check for unauthorized jobs
   - Verify Telegram sessions

3. **Secure**:
   - Delete compromised sessions
   - Update all credentials
   - Enable additional security measures

4. **Monitor**:
   - Watch logs for 24-48 hours
   - Look for unusual patterns
   - Document the incident

## 📞 Security Contacts

For security issues:
- Review logs: `docker-compose logs -f`
- Check documentation: This file
- Update system: `git pull && docker-compose up -d --build`

---

**Remember**: Security is not a one-time setup. Regularly review and update your security measures! 🔒
