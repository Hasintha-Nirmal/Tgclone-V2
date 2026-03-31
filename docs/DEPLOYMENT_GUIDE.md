# Deployment Guide - Post-Fixes

## Quick Start (5 Minutes)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Generate Strong Credentials
```bash
# Generate admin password (copy the output)
python -c "import secrets; print('ADMIN_PASSWORD=' + secrets.token_urlsafe(16))"

# Generate secret key (copy the output)
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
```

### Step 3: Configure Environment
```bash
# Copy example
cp .env.example .env

# Edit .env and paste the generated credentials
nano .env  # or use your preferred editor
```

**Required changes in .env:**
```env
ADMIN_PASSWORD=<paste-generated-password-here>
SECRET_KEY=<paste-generated-secret-key-here>
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

### Step 4: Start the Application
```bash
python main.py
```

### Step 5: Verify It Works
```bash
# Test health check (no auth required)
curl http://localhost:8000/health

# Test detailed health (no auth required)
curl http://localhost:8000/health/detailed

# Test authenticated endpoint
curl -u admin:your-password http://localhost:8000/api/auth/status
```

---

## Production Deployment

### Prerequisites
- Python 3.8+
- PostgreSQL (recommended) or SQLite
- Reverse proxy (nginx/Apache) with HTTPS
- Systemd or Docker for process management

### 1. Server Setup

```bash
# Create application user
sudo useradd -m -s /bin/bash telegram-automation
sudo su - telegram-automation

# Clone repository
git clone <your-repo-url>
cd telegram-automation

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup (PostgreSQL)

```bash
# Create database
sudo -u postgres createdb telegram_automation

# Update .env
DATABASE_URL=postgresql://user:password@localhost/telegram_automation
```

### 3. Security Configuration

```bash
# Generate credentials
python -c "import secrets; print('ADMIN_PASSWORD=' + secrets.token_urlsafe(24))"
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# Edit .env
nano .env
```

**Production .env:**
```env
# Database
DATABASE_URL=postgresql://user:password@localhost/telegram_automation

# Web (bind to localhost, use reverse proxy)
WEB_HOST=127.0.0.1
WEB_PORT=8000

# Security
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<strong-password-24-chars>
SECRET_KEY=<random-secret-key-32-chars>
ALLOWED_ORIGINS=https://yourdomain.com

# Rate limiting (conservative for production)
MAX_MESSAGES_PER_HOUR=50
DELAY_BETWEEN_MESSAGES=2.0
DELAY_BETWEEN_MEDIA=3.0

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/telegram-automation/app.log
```

### 4. File Permissions

```bash
# Secure session files
chmod 700 sessions/
chmod 600 sessions/*.session 2>/dev/null || true

# Secure .env
chmod 600 .env

# Create log directory
sudo mkdir -p /var/log/telegram-automation
sudo chown telegram-automation:telegram-automation /var/log/telegram-automation
```

### 5. Systemd Service

Create `/etc/systemd/system/telegram-automation.service`:

```ini
[Unit]
Description=Telegram Automation System
After=network.target postgresql.service

[Service]
Type=simple
User=telegram-automation
Group=telegram-automation
WorkingDirectory=/home/telegram-automation/telegram-automation
Environment="PATH=/home/telegram-automation/telegram-automation/venv/bin"
ExecStart=/home/telegram-automation/telegram-automation/venv/bin/python main.py
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/telegram-automation/telegram-automation/data
ReadWritePaths=/home/telegram-automation/telegram-automation/sessions
ReadWritePaths=/home/telegram-automation/telegram-automation/downloads
ReadWritePaths=/var/log/telegram-automation

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-automation
sudo systemctl start telegram-automation
sudo systemctl status telegram-automation
```

### 6. Nginx Reverse Proxy

Create `/etc/nginx/sites-available/telegram-automation`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running operations
        proxy_read_timeout 3600s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
    }
}
```

Enable and reload:
```bash
sudo ln -s /etc/nginx/sites-available/telegram-automation /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### 8. Firewall Configuration

```bash
# Allow SSH, HTTP, HTTPS
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 9. Monitoring Setup

```bash
# View logs
sudo journalctl -u telegram-automation -f

# View application logs
tail -f /var/log/telegram-automation/app.log

# Check health
curl https://yourdomain.com/health/detailed
```

---

## Docker Deployment

### Dockerfile (already exists)
The project includes a Dockerfile. Build and run:

```bash
# Build image
docker build -t telegram-automation .

# Run container
docker run -d \
  --name telegram-automation \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/sessions:/app/sessions \
  -v $(pwd)/downloads:/app/downloads \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/.env:/app/.env \
  --restart unless-stopped \
  telegram-automation
```

### Docker Compose (already exists)
```bash
# Start services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

---

## Post-Deployment Checklist

### Security
- [ ] Strong ADMIN_PASSWORD set (24+ characters)
- [ ] Random SECRET_KEY generated (32+ characters)
- [ ] ALLOWED_ORIGINS restricted to your domain
- [ ] HTTPS enabled with valid certificate
- [ ] Firewall configured
- [ ] Session files have 0600 permissions
- [ ] .env file has 0600 permissions

### Functionality
- [ ] Health check returns "healthy"
- [ ] Can login with admin credentials
- [ ] Can authorize Telegram account
- [ ] Can list channels
- [ ] Can create clone job
- [ ] Auto-sync works
- [ ] Rate limiting enforced

### Monitoring
- [ ] Logs are being written
- [ ] No error messages in logs
- [ ] Health check endpoint accessible
- [ ] Authentication attempts logged
- [ ] Systemd service running

### Performance
- [ ] Database indexes created
- [ ] Connection pool configured
- [ ] No connection leaks
- [ ] Response times acceptable

---

## Troubleshooting

### Issue: "ADMIN_PASSWORD must be at least 12 characters"
**Solution:** Generate a strong password:
```bash
python -c "import secrets; print(secrets.token_urlsafe(16))"
```

### Issue: "No authorized Telegram accounts available"
**Solution:** Login via web dashboard:
1. Go to http://localhost:8000
2. Login with admin credentials
3. Go to "Accounts" tab
4. Click "Add Account"
5. Enter API credentials and phone number

### Issue: "Database connection pool exhausted"
**Solution:** Check for connection leaks:
```bash
# View active connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname='telegram_automation';"

# Restart service
sudo systemctl restart telegram-automation
```

### Issue: "CORS error in browser"
**Solution:** Add your domain to ALLOWED_ORIGINS:
```env
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Issue: "Rate limit reached"
**Solution:** This is working as intended. Wait for the hourly reset or adjust:
```env
MAX_MESSAGES_PER_HOUR=200
```

---

## Backup and Recovery

### Backup
```bash
# Backup database
cp data/app.db data/app.db.backup-$(date +%Y%m%d)

# Backup sessions
tar -czf sessions-backup-$(date +%Y%m%d).tar.gz sessions/

# Backup .env
cp .env .env.backup
```

### Recovery
```bash
# Restore database
cp data/app.db.backup-20260327 data/app.db

# Restore sessions
tar -xzf sessions-backup-20260327.tar.gz

# Restart service
sudo systemctl restart telegram-automation
```

---

## Maintenance

### Update Application
```bash
# Stop service
sudo systemctl stop telegram-automation

# Backup
cp data/app.db data/app.db.backup

# Pull updates
git pull

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Start service
sudo systemctl start telegram-automation
```

### Clean Up Old Files
```bash
# Clean downloads older than 24 hours
find downloads/ -type f -mtime +1 -delete

# Clean logs older than 30 days
find logs/ -name "*.log.*" -mtime +30 -delete
```

### Monitor Disk Usage
```bash
# Check disk usage
df -h

# Check application disk usage
du -sh data/ sessions/ downloads/ logs/
```

---

## Support

### Logs Location
- Application: `/var/log/telegram-automation/app.log`
- Systemd: `sudo journalctl -u telegram-automation`
- Nginx: `/var/log/nginx/access.log` and `/var/log/nginx/error.log`

### Health Check
```bash
curl https://yourdomain.com/health/detailed
```

### Common Commands
```bash
# Restart service
sudo systemctl restart telegram-automation

# View logs
sudo journalctl -u telegram-automation -f

# Check status
sudo systemctl status telegram-automation

# Test configuration
python -c "from config.settings import settings; print('Config OK')"
```

---

## Success Criteria

Your deployment is successful when:

✅ Health check returns "healthy"  
✅ Can login with admin credentials  
✅ Can authorize Telegram accounts  
✅ Can create and run clone jobs  
✅ Auto-sync works correctly  
✅ Rate limiting is enforced  
✅ Logs show no errors  
✅ HTTPS is working  
✅ Authentication attempts are logged  
✅ System survives restart  

**Congratulations! Your Telegram Automation System is now production-ready!** 🎉
