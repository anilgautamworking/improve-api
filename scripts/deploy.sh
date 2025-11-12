#!/bin/bash
# Deployment script for Improve API
# This script handles deployment and PM2 management

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Improve API Deployment${NC}"
echo "=========================================="

# Check if PM2 is installed
if ! command -v pm2 &> /dev/null; then
    echo -e "${RED}❌ PM2 is not installed${NC}"
    echo "Install PM2: npm install -g pm2"
    exit 1
fi

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo -e "${BLUE}Project root: ${PROJECT_ROOT}${NC}"

# Check if virtual environment exists
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3 -m venv "$PROJECT_ROOT/venv"
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source "$PROJECT_ROOT/venv/bin/activate"

# Install/update dependencies
echo -e "${BLUE}Installing dependencies...${NC}"
pip install -q --upgrade pip
pip install -q -r "$PROJECT_ROOT/requirements.txt"

# Check if .env exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo "Please create .env file from env.example"
    exit 1
fi

# Check database connection
echo -e "${BLUE}Checking database connection...${NC}"
python3 -c "
from src.database.db import SessionLocal
try:
    session = SessionLocal()
    session.close()
    print('✓ Database connection successful')
except Exception as e:
    print(f'✗ Database connection failed: {e}')
    exit(1)
" || exit 1

# Ensure Docker database is running (if using Docker)
echo -e "${BLUE}Checking Docker database...${NC}"
if [ -f "$PROJECT_ROOT/docker-compose.yml" ]; then
    cd "$PROJECT_ROOT"
    if ! docker-compose ps | grep -q "postgres.*Up"; then
        echo -e "${YELLOW}⚠️  Docker database not running. Starting...${NC}"
        docker-compose up -d postgres
        echo -e "${BLUE}Waiting for database to be ready...${NC}"
        sleep 5
    else
        echo -e "${GREEN}✓ Docker database is running${NC}"
    fi
fi

# Run migrations
echo -e "${BLUE}Running database migrations...${NC}"
cd "$PROJECT_ROOT"
# Ensure DATABASE_URL is loaded from .env
export $(grep -v '^#' .env | grep DATABASE_URL | xargs) 2>/dev/null || true
alembic upgrade head || {
    echo -e "${RED}❌ Migration failed!${NC}"
    echo "Please check database connection and .env file"
    exit 1
}
echo -e "${GREEN}✓ Migrations completed successfully${NC}"

# Stop existing PM2 process if running
echo -e "${BLUE}Stopping existing PM2 process...${NC}"
pm2 stop improve-api 2>/dev/null || true
pm2 delete improve-api 2>/dev/null || true

# Start with PM2
echo -e "${GREEN}Starting API with PM2...${NC}"
cd "$PROJECT_ROOT"
pm2 start ecosystem.config.js

# Save PM2 configuration
pm2 save

# Show status
echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo -e "${BLUE}PM2 Status:${NC}"
pm2 status improve-api
echo ""
echo -e "${BLUE}View logs:${NC}"
echo "  pm2 logs improve-api"
echo ""
echo -e "${BLUE}Monitor:${NC}"
echo "  pm2 monit"
echo ""

