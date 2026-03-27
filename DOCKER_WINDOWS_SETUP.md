# Docker Setup on Windows

## Permission Issues on Windows

When running Docker on Windows, you may encounter permission issues with mounted volumes. This is because Windows file permissions don't map directly to Linux container permissions.

## Development Mode Solution

The `docker-compose.dev.yml` configuration uses **named volumes** instead of bind mounts for `logs` and `data` directories to avoid permission issues:

```yaml
volumes:
  - dev-logs:/app/logs      # Named volume (no permission issues)
  - dev-data:/app/data      # Named volume (no permission issues)
  - ./sessions:/app/sessions # Bind mount (read/write by container)
```

### Benefits of Named Volumes

- No permission conflicts between Windows and Linux
- Better performance on Windows
- Automatic management by Docker
- Data persists between container restarts

### Accessing Data in Named Volumes

Use the provided helper scripts:

**Windows:**
```bash
# View logs
docker-dev-access.bat logs

# Access database
docker-dev-access.bat data

# Open shell in container
docker-dev-access.bat shell
```

**Linux/Mac:**
```bash
chmod +x docker-dev-access.sh

# View logs
./docker-dev-access.sh logs

# Access database
./docker-dev-access.sh data

# Open shell in container
./docker-dev-access.sh shell
```

### Copying Files from Named Volumes

To copy the database file to your host:
```bash
docker cp telegram-automation:/app/data/app.db ./app.db
```

To copy log files:
```bash
docker cp telegram-automation:/app/logs/app.log ./app.log
```

### Inspecting Named Volumes

List all volumes:
```bash
docker volume ls
```

Inspect a specific volume:
```bash
docker volume inspect tgcloner-v2_dev-data
docker volume inspect tgcloner-v2_dev-logs
```

Find volume location on host:
```bash
docker volume inspect tgcloner-v2_dev-data --format '{{ .Mountpoint }}'
```

## Production Mode

For production deployment, you can use bind mounts with proper permissions:

1. **On Linux/Mac:**
   ```bash
   # Fix permissions
   chmod -R 755 logs data sessions
   chown -R 1000:1000 logs data sessions
   ```

2. **On Windows:**
   Use named volumes (recommended) or WSL2 with proper permissions.

## Starting the Application

**Development mode (with hot-reload):**
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

**Production mode:**
```bash
docker-compose up -d
```

## Troubleshooting

### "Permission denied" errors

If you see permission errors:
1. Stop containers: `docker-compose down`
2. Remove volumes: `docker volume rm tgcloner-v2_dev-data tgcloner-v2_dev-logs`
3. Restart: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up`

### "Database is locked" errors

SQLite on Windows bind mounts can have locking issues. Solution:
- Use named volumes (already configured in dev mode)
- Or switch to PostgreSQL for production

### Viewing real-time logs

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f
```

### Accessing container shell

```bash
docker exec -it telegram-automation /bin/bash
```

## Environment Variables

Make sure to set required environment variables in `.env`:

```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
SECRET_KEY=your_secret_key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_password
```

## Next Steps

1. Start the application in dev mode
2. Access the web interface at http://localhost:8000
3. Authorize your Telegram account
4. Start cloning channels

For more information, see:
- [DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md)
- [QUICKSTART.md](docs/QUICKSTART.md)
- [AUTHORIZATION.md](docs/AUTHORIZATION.md)
