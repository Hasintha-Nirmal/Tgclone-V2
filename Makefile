.PHONY: help build up down restart logs shell clean dev prod health stats backup restore

# Default target
help:
	@echo "Telegram Automation - Docker Commands"
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start in development mode (hot reload)"
	@echo "  make dev-down     - Stop development environment"
	@echo ""
	@echo "Production:"
	@echo "  make prod         - Start in production mode (with nginx)"
	@echo "  make prod-down    - Stop production environment"
	@echo ""
	@echo "Standard:"
	@echo "  make up           - Start services (standard mode)"
	@echo "  make down         - Stop services"
	@echo "  make restart      - Restart services"
	@echo ""
	@echo "Build:"
	@echo "  make build        - Build Docker images"
	@echo "  make rebuild      - Rebuild without cache"
	@echo ""
	@echo "Monitoring:"
	@echo "  make logs         - View logs (follow)"
	@echo "  make health       - Check service health"
	@echo "  make stats        - View resource usage"
	@echo "  make ps           - List running containers"
	@echo ""
	@echo "Maintenance:"
	@echo "  make shell        - Open shell in container"
	@echo "  make clean        - Remove containers and volumes"
	@echo "  make backup       - Backup data volumes"
	@echo "  make restore      - Restore from backup"
	@echo ""
	@echo "Optional Services:"
	@echo "  make with-redis   - Start with Redis"
	@echo "  make with-postgres - Start with PostgreSQL"
	@echo "  make with-all     - Start with all optional services"

# Development mode
dev:
	docker compose -f docker compose.yml -f docker compose.dev.yml up

dev-down:
	docker compose -f docker compose.yml -f docker compose.dev.yml down

dev-build:
	docker compose -f docker compose.yml -f docker compose.dev.yml build

# Production mode
prod:
	docker compose -f docker compose.yml -f docker compose.prod.yml up -d

prod-down:
	docker compose -f docker compose.yml -f docker compose.prod.yml down

prod-build:
	docker compose -f docker compose.yml -f docker compose.prod.yml build

# Standard operations
up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

# Build operations
build:
	docker compose build

rebuild:
	docker compose build --no-cache

# Monitoring
logs:
	docker compose logs -f

logs-app:
	docker compose logs -f telegram-automation

health:
	@echo "Checking service health..."
	@docker compose ps
	@echo ""
	@echo "Health endpoint:"
	@curl -s http://localhost:8000/api/system/health | python -m json.tool || echo "Service not responding"

stats:
	docker stats telegram-automation

ps:
	docker compose ps

# Maintenance
shell:
	docker compose exec telegram-automation /bin/bash

shell-root:
	docker compose exec -u root telegram-automation /bin/bash

clean:
	docker compose down -v
	docker system prune -f

clean-all:
	docker compose down -v --rmi all
	docker system prune -af

# Backup and restore
backup:
	@echo "Creating backup..."
	@mkdir -p backups
	@tar -czf backups/backup-$$(date +%Y%m%d-%H%M%S).tar.gz sessions/ logs/ data/
	@echo "Backup created in backups/"

restore:
	@echo "Available backups:"
	@ls -lh backups/
	@echo ""
	@read -p "Enter backup filename: " backup; \
	docker compose down; \
	tar -xzf backups/$$backup; \
	sudo chown -R 1000:1000 sessions logs data; \
	docker compose up -d

# Optional services
with-redis:
	docker compose --profile with-redis up -d

with-postgres:
	docker compose --profile with-postgres up -d

with-all:
	docker compose --profile with-redis --profile with-postgres up -d

# Authorization
authorize:
	docker compose exec telegram-automation python authorize.py

# Database operations
db-migrate:
	docker compose exec telegram-automation python migrate_db.py

db-shell:
	docker compose exec telegram-automation python -c "from app.utils.database import engine; import sqlite3; conn = sqlite3.connect('./data/app.db'); conn.row_factory = sqlite3.Row; import code; code.interact(local=locals())"

# Testing
test:
	docker compose exec telegram-automation python -m pytest tests/

# Security scan
scan:
	@echo "Scanning Docker image for vulnerabilities..."
	docker scan telegram-automation:latest || echo "Docker scan not available. Install: https://docs.docker.com/engine/scan/"

# Update dependencies
update-deps:
	docker compose exec telegram-automation pip list --outdated
