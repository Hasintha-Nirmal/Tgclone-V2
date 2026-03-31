# Docker Quick Reference

## 🚀 Quick Start

```bash
# Development (hot reload)
make dev

# Production (optimized)
make prod

# Standard (balanced)
make up
```

## 📋 Common Commands

| Command | Description |
|---------|-------------|
| `make dev` | Start development mode |
| `make prod` | Start production mode |
| `make up` | Start standard mode |
| `make down` | Stop all services |
| `make restart` | Restart services |
| `make logs` | View logs (follow) |
| `make health` | Check service health |
| `make stats` | View resource usage |
| `make shell` | Open container shell |
| `make backup` | Backup data volumes |
| `make clean` | Remove containers/volumes |

## 🔧 Configuration Files

| File | Purpose |
|------|---------|
| `docker compose.yml` | Base configuration |
| `docker compose.dev.yml` | Development overrides |
| `docker compose.prod.yml` | Production overrides |
| `Dockerfile` | Multi-stage build |
| `.dockerignore` | Build context exclusions |
| `nginx/nginx.conf` | Reverse proxy config |

## 🏥 Health Checks

```bash
# Docker health status
docker compose ps

# Health endpoint
curl http://localhost:8000/api/system/health

# Detailed health
docker inspect telegram-automation | jq '.[0].State.Health'
```

## 📊 Monitoring

```bash
# Real-time stats
docker stats telegram-automation

# View logs
docker compose logs -f telegram-automation

# Last 100 lines
docker compose logs --tail=100 telegram-automation
```

## 🔐 Security Features

- ✅ Non-root user (UID 1000)
- ✅ Read-only filesystem
- ✅ No new privileges
- ✅ Minimal base image
- ✅ Health checks
- ✅ Resource limits
- ✅ Network isolation

## 🎯 Resource Limits

| Service | CPU Limit | Memory Limit |
|---------|-----------|--------------|
| telegram-automation | 2 cores | 2GB |
| redis | 1 core | 512MB |
| postgres | 2 cores | 1GB |
| nginx | 0.5 core | 256MB |

## 🔄 Deployment Modes

### Development
```bash
docker compose -f docker compose.yml -f docker compose.dev.yml up
```
- Hot reload enabled
- Debug logging
- Source mounted
- No resource limits

### Production
```bash
docker compose -f docker compose.yml -f docker compose.prod.yml up -d
```
- Nginx reverse proxy
- Strict limits
- Log rotation
- SSL/TLS ready

### Standard
```bash
docker compose up -d
```
- Balanced config
- Moderate limits
- General use

## 📦 Optional Services

```bash
# With Redis
make with-redis

# With PostgreSQL
make with-postgres

# With all optional services
make with-all
```

## 🛠️ Troubleshooting

### Container won't start
```bash
docker compose logs telegram-automation
```

### Permission issues
```bash
sudo chown -R 1000:1000 sessions logs data
```

### Health check failing
```bash
docker exec telegram-automation python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/system/health').read())"
```

### Out of memory
Edit `docker compose.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 4G  # Increase
```

## 💾 Backup & Restore

### Backup
```bash
make backup
# Creates: backups/backup-YYYYMMDD-HHMMSS.tar.gz
```

### Restore
```bash
make restore
# Follow prompts to select backup
```

## 🔍 Useful Inspections

```bash
# Container details
docker inspect telegram-automation

# Network info
docker network inspect telegram-automation_telegram-net

# Volume info
docker volume ls
docker volume inspect telegram-automation_telegram-downloads

# Image layers
docker history telegram-automation:latest
```

## 🌐 Ports

| Service | Port | Description |
|---------|------|-------------|
| telegram-automation | 8000 | Main application |
| redis | 6379 | Redis cache |
| postgres | 5432 | PostgreSQL DB |
| nginx | 80/443 | Reverse proxy |

## 📝 Environment Variables

Required in `.env`:
```bash
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
SECRET_KEY=your_secret_key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure_password
```

Optional:
```bash
TELEGRAM_PHONE=+1234567890
DATABASE_URL=sqlite+aiosqlite:///./data/app.db
LOG_LEVEL=INFO
AUTO_DELETE_FILES=true
```

## 🚨 Emergency Commands

```bash
# Stop everything immediately
docker compose down

# Force remove everything
docker compose down -v --rmi all

# Restart from scratch
make clean && make up

# View all container processes
docker compose top
```

## 📚 Documentation

- Full guide: `docs/DOCKER_GUIDE.md`
- Improvements: `DOCKER_IMPROVEMENTS.md`
- Main README: `README.md`

## 🔗 Quick Links

- Health: http://localhost:8000/api/system/health
- Dashboard: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Logs: `./logs/app.log`

## 💡 Tips

1. Always use `make` commands for consistency
2. Check health before debugging
3. Use `make logs` to follow real-time logs
4. Backup before major changes
5. Use dev mode for development
6. Use prod mode for deployment
7. Monitor resources with `make stats`
8. Keep `.env` file secure (never commit)

## 🎓 Learning Resources

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Compose File Reference](https://docs.docker.com/compose/compose-file/)
- [Docker Security](https://docs.docker.com/engine/security/)
