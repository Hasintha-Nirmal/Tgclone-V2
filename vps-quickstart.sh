#!/bin/bash
# Quick Start Script for VPS Setup

set -e

echo "=========================================="
echo "Telegram Automation - VPS Quick Start"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${YELLOW}Warning: Running as root. Consider using a non-root user.${NC}"
    echo ""
fi

# Step 1: Resolve Git Conflicts
echo "Step 1: Checking for git conflicts..."
if git status | grep -q "Your local changes"; then
    echo -e "${YELLOW}Git conflicts detected!${NC}"
    echo ""
    echo "Choose an option:"
    echo "  1) Keep local changes (stash remote)"
    echo "  2) Use remote version (discard local)"
    echo "  3) Skip (resolve manually later)"
    read -p "Enter choice [1-3]: " git_choice
    
    case $git_choice in
        1)
            echo "Stashing local changes..."
            git stash
            git pull origin main
            git stash pop
            echo -e "${GREEN}✓ Local changes preserved${NC}"
            ;;
        2)
            echo "Discarding local changes..."
            git reset --hard HEAD
            git pull origin main
            echo -e "${GREEN}✓ Using remote version${NC}"
            ;;
        3)
            echo "Skipping git resolution..."
            ;;
        *)
            echo "Invalid choice. Skipping..."
            ;;
    esac
else
    echo -e "${GREEN}✓ No git conflicts${NC}"
fi
echo ""

# Step 2: Check Docker
echo "Step 2: Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found${NC}"
    echo "Install Docker first: https://docs.docker.com/engine/install/"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo -e "${RED}✗ Docker Compose not found${NC}"
    echo "Install Docker Compose: sudo apt install docker-compose-plugin"
    exit 1
fi

echo -e "${GREEN}✓ Docker installed: $(docker --version)${NC}"
echo -e "${GREEN}✓ Docker Compose installed: $(docker compose version)${NC}"
echo ""

# Step 3: Check .env file
echo "Step 3: Checking configuration..."
if [ ! -f .env ]; then
    echo -e "${YELLOW}! .env file not found${NC}"
    echo "Creating from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}! IMPORTANT: Edit .env file with your credentials${NC}"
    echo "  - Get API credentials from: https://my.telegram.org"
    echo "  - Change admin password"
    echo ""
    read -p "Press Enter to edit .env now, or Ctrl+C to exit and edit manually..."
    ${EDITOR:-nano} .env
else
    echo -e "${GREEN}✓ .env file exists${NC}"
    
    # Check if API credentials are set
    if grep -q "your_api_id_here" .env || grep -q "your_api_hash_here" .env; then
        echo -e "${YELLOW}! Warning: Default API credentials detected${NC}"
        echo "  You need to set TELEGRAM_API_ID and TELEGRAM_API_HASH"
        read -p "Edit .env now? [y/N]: " edit_env
        if [[ $edit_env =~ ^[Yy]$ ]]; then
            ${EDITOR:-nano} .env
        fi
    fi
fi
echo ""

# Step 4: Create required directories
echo "Step 4: Creating directories..."
mkdir -p logs sessions data downloads
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Step 5: Start Docker containers
echo "Step 5: Starting Docker containers..."
echo "Running: docker compose up -d"
docker compose up -d

echo ""
echo "Waiting for container to start..."
sleep 5

if docker compose ps | grep -q "Up"; then
    echo -e "${GREEN}✓ Container started successfully${NC}"
else
    echo -e "${RED}✗ Container failed to start${NC}"
    echo "Check logs: docker compose logs telegram-automation"
    exit 1
fi
echo ""

# Step 6: Check if authorization is needed
echo "Step 6: Checking authorization status..."
if [ ! -f sessions/*.session ]; then
    echo -e "${YELLOW}! No session file found - authorization required${NC}"
    echo ""
    echo "You need to authorize your Telegram account."
    echo "This will prompt for:"
    echo "  1. Phone number (if not in .env)"
    echo "  2. Verification code (sent to Telegram app)"
    echo "  3. 2FA password (if enabled)"
    echo ""
    read -p "Authorize now? [Y/n]: " auth_now
    
    if [[ ! $auth_now =~ ^[Nn]$ ]]; then
        echo ""
        echo "Starting authorization..."
        docker exec -it telegram-automation python authorize.py
        
        echo ""
        echo "Restarting container..."
        docker compose restart telegram-automation
        echo -e "${GREEN}✓ Authorization complete${NC}"
    else
        echo "Run authorization later with: ./docker-authorize.sh"
    fi
else
    echo -e "${GREEN}✓ Session file exists${NC}"
fi
echo ""

# Step 7: Configure firewall
echo "Step 7: Checking firewall..."
if command -v ufw &> /dev/null; then
    if ufw status | grep -q "8000.*ALLOW"; then
        echo -e "${GREEN}✓ Port 8000 already allowed${NC}"
    else
        echo -e "${YELLOW}! Port 8000 not open in firewall${NC}"
        read -p "Open port 8000? [Y/n]: " open_port
        if [[ ! $open_port =~ ^[Nn]$ ]]; then
            sudo ufw allow 8000/tcp
            echo -e "${GREEN}✓ Port 8000 opened${NC}"
        fi
    fi
else
    echo -e "${YELLOW}! UFW not found - configure firewall manually${NC}"
fi
echo ""

# Step 8: Get VPS IP
echo "Step 8: Getting access information..."
VPS_IP=$(curl -s ifconfig.me || echo "YOUR_VPS_IP")
echo ""
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Access your dashboard:"
echo "  Local:  http://localhost:8000"
echo "  Remote: http://$VPS_IP:8000"
echo ""
echo "Default credentials (CHANGE THESE!):"
echo "  Username: admin"
echo "  Password: changeme123"
echo ""
echo "Useful commands:"
echo "  View logs:    docker compose logs -f"
echo "  Restart:      docker compose restart"
echo "  Stop:         docker compose down"
echo "  Authorize:    ./docker-authorize.sh"
echo "  Status:       python3 manage.py status"
echo ""
echo "Next steps:"
echo "  1. Access dashboard and login"
echo "  2. Change admin password in .env"
echo "  3. Add Telegram accounts via web interface"
echo "  4. Create clone jobs"
echo ""
echo "Documentation:"
echo "  Full guide:   VPS_SETUP_GUIDE.md"
echo "  Docs index:   docs/INDEX.md"
echo "  API docs:     http://$VPS_IP:8000/docs"
echo ""
echo "=========================================="
