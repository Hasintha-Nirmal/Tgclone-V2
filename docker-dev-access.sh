#!/bin/bash
# Helper script to access development volumes in Docker

set -e

echo "========================================"
echo "Docker Development Volume Access"
echo "========================================"
echo

if [ -z "$1" ]; then
    echo "Usage: ./docker-dev-access.sh [logs|data|shell]"
    echo
    echo "Commands:"
    echo "  logs  - View application logs"
    echo "  data  - Access SQLite database"
    echo "  shell - Open shell in container"
    echo
    exit 1
fi

case "$1" in
    logs)
        echo "Tailing application logs..."
        docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f telegram-automation
        ;;
    data)
        echo "Accessing database volume..."
        echo "To copy database out: docker cp telegram-automation:/app/data/app.db ./app.db"
        echo "To inspect: docker exec -it telegram-automation ls -la /app/data"
        docker exec -it telegram-automation ls -la /app/data
        ;;
    shell)
        echo "Opening shell in container..."
        docker exec -it telegram-automation /bin/bash
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use: ./docker-dev-access.sh [logs|data|shell]"
        exit 1
        ;;
esac
