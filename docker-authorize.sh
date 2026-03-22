#!/bin/bash
# Helper script to authorize Telegram account in Docker

echo "=========================================="
echo "Telegram Authorization (Docker)"
echo "=========================================="
echo ""
echo "This will help you authorize your Telegram account"
echo ""

# Check if container is running
if ! docker ps | grep -q telegram-automation; then
    echo "Error: telegram-automation container is not running"
    echo "Start it first with: docker-compose up -d"
    exit 1
fi

echo "Running authorization script in container..."
echo ""

docker exec -it telegram-automation python authorize.py

echo ""
echo "Done! Restarting container..."
docker-compose restart telegram-automation

echo ""
echo "Authorization complete. Access dashboard at: http://localhost:8000"
