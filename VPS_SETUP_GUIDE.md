# VPS Setup Guide - Telegram Automation System

## Current Situation

You're on a VPS (Ubuntu Linux) and need to:
1. Resolve git conflicts from local changes
2. Set up and run the Telegram automation system
3. Make it accessible and production-ready

## Step 1: Resolve Git Conflict

You have local changes that conflict with remote updates. Choose one option:

### Option A: Keep Local Changes (Recommended)
Your local changes include the Docker Compose V2 fixes we just made.

```bash
# Save your local changes
git stash

# Pull remote changes
git pull origin main

# Reapply your local changes
git stash pop

# If there are conflicts, resolve them manually
# Then commit:
git add .
git commit -m "Merge remote changes with local Docker Compose V2 fixes"
```

### Option B: Use Remote Version
This discards your local Docker Compose V2 fixes (you'll need to reapply them).

```bash
# Discard local changes
git reset --hard HEAD

# Pull remote changes
git pull origin main

# Reapply Docker Compose V2 fixes if needed
# (The remote might already have docker-compose, not docker compose)
```

### Option C: Create a Backup Branch
Safest option - keeps everything.

```bash
# Create backup of your current state
git branch backup-local-changes

# Reset to remote
git reset --hard origin/main

# Pull latest
git pull origin main

# Later, you can cherry-pick changes from backup-local-changes if needed
```

## Step 2: Configure Environment

### 2.1 Create .env File

```bash
# Copy example configuration
cp .env.example .env

# Edit with your settings
nano .env
```

### 2.2 Required .env Settings

```bash
# Telegram API Credentials (Get from https://my.telegram.org)
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash

# Optional: Phone number (can also login via web interface)
TELEGRAM_PHONE=+1234567890

# Web Dashboard Credentials (CHANGE THESE!)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password_here

# Database (SQLite is fine for VPS)
DATABASE_URL=sqlite+aiosqlite:///./data/app.db

# Server Settings
HOST=0.0.0.0
PORT=8000

# Storage Settings
AUTO_DELETE_FILES=true
MAX_FILE_SIZE_MB=2000

# Rate Limiting (Protect your Telegram account)
MESSAGE_DELAY_SECONDS=2
HOURLY_MESSAGE_LIMIT=100
BREAK_INTERVAL_MINUTES=60
BREAK_DURATION_MINUTES=10

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### 2.3 Get Telegram API Credentials

1. Go to https://my.telegram.org
2. Login with your phone number
3. Go to "API Development Tools"
4. Create an application
5. Copy `api_id` and `api_hash` to your `.env` file

## Step 3: Start the System

### 3.1 Using Docker (Recommended for VPS)

```bash
# Make sure Docker is running
docker ps

# Start the system
docker compose up -d

# Check if it's running
docker compose ps

# View logs
docker compose logs -f telegram-automation
```

### 3.2 Authorize Your Telegram Account

This is REQUIRED on first run:

```bash
# Method 1: Using helper script
chmod +x docker-authorize.sh
./docker-authorize.sh

# Method 2: Using manage.py
python3 manage.py authorize --docker

# Method 3: Direct docker exec
docker exec -it telegram-automation python authorize.py
```

You'll be prompted to:
1. Enter your phone number (if not in .env)
2. Enter the verification code sent to your Telegram app
3. Enter 2FA password (if enabled)

After authorization, restart the container:
```bash
docker compose restart telegram-automation
```

## Step 4: Configure Firewall

Allow access to the web dashboard:

```bash
# UFW (Ubuntu Firewall)
sudo ufw allow 8000/tcp
sudo ufw status

# Or iptables
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
sudo iptables-save
```

## Step 5: Access the Dashboard

### Local Access (from VPS)
```bash
curl http://localhost:8000/api/system/health
```

### Remote Access (from your computer)
```
http://YOUR_VPS_IP:8000
```

Login with credentials from your `.env` file.

## Step 6: Production Setup (Optional but Recommended)

### 6.1 Use Nginx as Reverse Proxy

```bash
# Install Nginx
sudo apt update
sudo apt install nginx

# Create Nginx configuration
sudo nano /etc/nginx/sites-available/telegram-automation
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Or use your VPS IP

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/telegram-automation /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Allow HTTP through firewall
sudo ufw allow 'Nginx Full'
```

### 6.2 Add SSL Certificate (HTTPS)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

Now access via: `https://your-domain.com`

### 6.3 Run as System Service (Auto-start on boot)

Create systemd service:

```bash
sudo nano /etc/systemd/system/telegram-automation.service
```

Add:

```ini
[Unit]
Description=Telegram Automation System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/Tgclone-V2
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

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

## Step 7: Monitoring and Maintenance

### View Logs
```bash
# Real-time logs
docker compose logs -f telegram-automation

# Last 100 lines
docker compose logs --tail=100 telegram-automation

# Application logs
tail -f logs/app.log
```

### Check Status
```bash
# Container status
docker compose ps

# Resource usage
docker stats telegram-automation

# System status
python3 manage.py status
```

### Restart Services
```bash
# Restart container
docker compose restart telegram-automation

# Full restart
docker compose down
docker compose up -d
```

### Backup Data
```bash
# Create backup
tar -czf backup-$(date +%Y%m%d).tar.gz sessions/ logs/ data/ .env

# Copy to safe location
scp backup-*.tar.gz user@backup-server:/backups/
```

### Update System
```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker compose down
docker compose build --no-cache
docker compose up -d
```

## Step 8: Security Checklist

- [ ] Changed default admin password in `.env`
- [ ] Configured firewall (UFW or iptables)
- [ ] Using HTTPS with SSL certificate
- [ ] Nginx reverse proxy configured
- [ ] Regular backups scheduled
- [ ] Rate limiting configured to protect Telegram account
- [ ] Log rotation configured
- [ ] SSH key authentication enabled (disable password auth)
- [ ] Fail2ban installed for SSH protection

### Additional Security

```bash
# Install fail2ban
sudo apt install fail2ban

# Configure SSH (disable password auth)
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
sudo systemctl restart sshd

# Set up automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker compose logs telegram-automation

# Check .env file
cat .env | grep -v "^#" | grep -v "^$"

# Rebuild
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Can't Access Dashboard
```bash
# Check if service is running
docker compose ps
curl http://localhost:8000/api/system/health

# Check firewall
sudo ufw status
sudo netstat -tlnp | grep 8000

# Check Nginx (if using)
sudo nginx -t
sudo systemctl status nginx
```

### Authorization Issues
```bash
# Remove old session
rm sessions/*.session

# Authorize again
./docker-authorize.sh

# Check logs
docker compose logs -f telegram-automation
```

### Out of Disk Space
```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -a

# Clean old downloads
docker exec telegram-automation python -c "from app.utils.storage import storage_manager; storage_manager.cleanup_old_files()"

# Clean logs
truncate -s 0 logs/app.log
```

## Quick Reference Commands

```bash
# Start system
docker compose up -d

# Stop system
docker compose down

# Restart
docker compose restart

# View logs
docker compose logs -f

# Authorize account
./docker-authorize.sh

# Check status
python3 manage.py status

# Access shell
docker exec -it telegram-automation bash

# Backup
tar -czf backup.tar.gz sessions/ logs/ data/ .env

# Update
git pull && docker compose up -d --build
```

## Getting Help

1. Check logs: `docker compose logs -f`
2. Check documentation: `docs/INDEX.md`
3. Check troubleshooting: `docs/TROUBLESHOOTING.md`
4. Check API docs: `http://YOUR_VPS_IP:8000/docs`

## Next Steps

1. ✅ Resolve git conflict
2. ✅ Configure `.env` file
3. ✅ Start Docker containers
4. ✅ Authorize Telegram account
5. ✅ Configure firewall
6. ✅ Access dashboard
7. ⭐ Set up Nginx + SSL (recommended)
8. ⭐ Configure auto-start service
9. ⭐ Set up backups
10. ⭐ Harden security

Your Telegram automation system will be production-ready on your VPS!
