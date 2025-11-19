#!/bin/bash
# Comprehensive server deployment script
# Run this on the server after pulling from GitHub

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🚀 Server Deployment Script${NC}"
echo "=========================================="

# Get project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

echo -e "${BLUE}Project root: ${PROJECT_ROOT}${NC}"
echo ""

# Step 1: Pull latest code from GitHub
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 1: Pulling latest code from GitHub${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ -d ".git" ]; then
    CURRENT_BRANCH=$(git branch --show-current || echo "main")
    echo -e "${BLUE}Current branch: ${CURRENT_BRANCH}${NC}"
    git pull origin "$CURRENT_BRANCH" || {
        echo -e "${YELLOW}⚠️  Git pull failed. Continuing anyway...${NC}"
    }
    echo -e "${GREEN}✓ Code updated${NC}"
else
    echo -e "${YELLOW}⚠️  Not a git repository. Skipping pull...${NC}"
fi
echo ""

# Step 2: Check Python version
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 2: Checking Python version${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python version: ${PYTHON_VERSION}${NC}"
echo ""

# Step 3: Setup/Update virtual environment
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 3: Setting up virtual environment${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
fi

source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Upgrade pip
echo -e "${BLUE}Upgrading pip...${NC}"
pip install --quiet --upgrade pip
echo -e "${GREEN}✓ pip upgraded${NC}"
echo ""

# Step 4: Install dependencies
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 4: Installing dependencies${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ requirements.txt not found!${NC}"
    exit 1
fi

pip install --quiet -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Step 5: Check .env file
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 5: Checking environment configuration${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    if [ -f "env.example" ]; then
        echo -e "${YELLOW}Creating .env from env.example...${NC}"
        cp env.example .env
        echo -e "${YELLOW}⚠️  Please edit .env file with your configuration!${NC}"
        echo "Press Enter to continue after editing .env..."
        read
    else
        echo -e "${RED}❌ env.example also not found!${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi
echo ""

# Step 6: Check Docker/Database
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 6: Checking database connection${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ -f "docker-compose.yml" ]; then
    echo -e "${BLUE}Checking Docker database...${NC}"
    if command -v docker-compose &> /dev/null || command -v docker &> /dev/null; then
        # Check if postgres container is running
        if docker ps | grep -q "improve_db\|postgres"; then
            echo -e "${GREEN}✓ Docker database container is running${NC}"
        else
            echo -e "${YELLOW}⚠️  Docker database not running. Starting...${NC}"
            docker-compose up -d postgres 2>/dev/null || docker compose up -d postgres 2>/dev/null || {
                echo -e "${YELLOW}⚠️  Could not start Docker database. Continuing...${NC}"
            }
            echo -e "${BLUE}Waiting for database to be ready...${NC}"
            sleep 5
        fi
    fi
fi

# Test database connection
echo -e "${BLUE}Testing database connection...${NC}"
python3 -c "
from src.database.db import SessionLocal
try:
    session = SessionLocal()
    session.close()
    print('✓ Database connection successful')
except Exception as e:
    print(f'✗ Database connection failed: {e}')
    exit(1)
" || {
    echo -e "${RED}❌ Database connection failed!${NC}"
    echo "Please check your .env file and database configuration"
    exit 1
}
echo ""

# Step 7: Run database migrations
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 7: Running database migrations${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Current migration status:${NC}"
alembic current 2>/dev/null || echo "No migrations applied yet"

echo -e "${BLUE}Upgrading to latest migration...${NC}"
alembic upgrade head || {
    echo -e "${RED}❌ Migration failed!${NC}"
    echo "Please check database connection and migration files"
    exit 1
}

CURRENT_REVISION=$(alembic current 2>/dev/null | awk '{print $1}' || echo "unknown")
echo -e "${GREEN}✓ Migrations completed. Current revision: ${CURRENT_REVISION}${NC}"
echo ""

# Step 8: Seed exam categories
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 8: Seeding exam categories${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ -f "scripts/seed_exam_categories.py" ]; then
    python3 scripts/seed_exam_categories.py || {
        echo -e "${YELLOW}⚠️  Exam category seeding failed or already exists${NC}"
    }
    echo -e "${GREEN}✓ Exam categories seeded${NC}"
else
    echo -e "${YELLOW}⚠️  seed_exam_categories.py not found. Skipping...${NC}"
fi
echo ""

# Step 9: Seed admin user
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 9: Seeding admin user${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ -f "scripts/seed_admin_user.py" ]; then
    ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}"
    ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"
    
    echo -e "${BLUE}Creating admin user...${NC}"
    echo -e "${BLUE}Email: ${ADMIN_EMAIL}${NC}"
    python3 scripts/seed_admin_user.py --email "$ADMIN_EMAIL" --password "$ADMIN_PASSWORD" || {
        echo -e "${YELLOW}⚠️  Admin user may already exist${NC}"
    }
    echo -e "${GREEN}✓ Admin user ready${NC}"
else
    echo -e "${YELLOW}⚠️  seed_admin_user.py not found. Skipping...${NC}"
fi
echo ""

# Step 10: Setup Prefect (if configured)
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 10: Setting up Prefect${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ -f ".env" ] && grep -q "PREFECT_API_URL" .env; then
    PREFECT_API_URL=$(grep "^PREFECT_API_URL" .env | cut -d '=' -f2 | tr -d '"' | tr -d "'" | xargs)
    if [ -n "$PREFECT_API_URL" ] && [ "$PREFECT_API_URL" != "" ]; then
        export PREFECT_API_URL
        echo -e "${BLUE}Prefect API URL: ${PREFECT_API_URL}${NC}"
        
        # Check if work pool exists, create if not
        echo -e "${BLUE}Checking Prefect work pool...${NC}"
        prefect work-pool ls 2>/dev/null | grep -q "improve-api" || {
            echo -e "${YELLOW}Creating Prefect work pool...${NC}"
            prefect work-pool create improve-api --type process || {
                echo -e "${YELLOW}⚠️  Work pool may already exist${NC}"
            }
        }
        
        # Deploy Prefect flow
        if [ -f "prefect.yaml" ]; then
            echo -e "${BLUE}Deploying Prefect flow...${NC}"
            prefect deploy --all || {
                echo -e "${YELLOW}⚠️  Prefect deployment failed or already exists${NC}"
            }
            echo -e "${GREEN}✓ Prefect flow deployed${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Prefect not configured. Skipping...${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Prefect not configured. Skipping...${NC}"
fi
echo ""

# Step 11: Setup PM2
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 11: Setting up PM2${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if ! command -v pm2 &> /dev/null; then
    echo -e "${YELLOW}⚠️  PM2 is not installed${NC}"
    echo -e "${BLUE}Installing PM2...${NC}"
    npm install -g pm2 || {
        echo -e "${RED}❌ PM2 installation failed!${NC}"
        echo "Please install PM2 manually: npm install -g pm2"
        exit 1
    }
    echo -e "${GREEN}✓ PM2 installed${NC}"
else
    echo -e "${GREEN}✓ PM2 is installed${NC}"
fi

# Check for ecosystem.config.js
if [ -f "ecosystem.config.js" ]; then
    echo -e "${GREEN}✓ PM2 ecosystem config found${NC}"
    
    # Stop existing processes
    echo -e "${BLUE}Stopping existing PM2 processes...${NC}"
    pm2 stop all 2>/dev/null || true
    pm2 delete all 2>/dev/null || true
    
    # Start API server
    echo -e "${BLUE}Starting API server with PM2...${NC}"
    pm2 start ecosystem.config.js || {
        echo -e "${RED}❌ PM2 start failed!${NC}"
        exit 1
    }
    
    # Start Prefect worker if configured
    if [ -n "$PREFECT_API_URL" ] && [ "$PREFECT_API_URL" != "" ]; then
        echo -e "${BLUE}Starting Prefect worker with PM2...${NC}"
        # Check if worker process exists in ecosystem.config.js
        if grep -q "prefect-worker" ecosystem.config.js 2>/dev/null; then
            # Export Prefect API URL for worker
            export PREFECT_API_URL
            pm2 start ecosystem.config.js --only prefect-worker || {
                echo -e "${YELLOW}⚠️  Prefect worker start failed. Check PREFECT_API_URL in .env${NC}"
            }
        else
            echo -e "${YELLOW}⚠️  Prefect worker not in ecosystem.config.js${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Prefect not configured (PREFECT_API_URL not set). Skipping worker...${NC}"
    fi
    
    # Save PM2 configuration
    pm2 save
    echo -e "${GREEN}✓ PM2 processes started${NC}"
else
    echo -e "${YELLOW}⚠️  ecosystem.config.js not found. Creating default...${NC}"
    # We'll create it below
fi
echo ""

# Step 12: Verify deployment
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 12: Verifying deployment${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}PM2 Status:${NC}"
pm2 status
echo ""

# Check API health
echo -e "${BLUE}Checking API health...${NC}"
sleep 2
API_PORT=$(grep -E "^API_PORT|PORT" .env 2>/dev/null | cut -d '=' -f2 | tr -d ' ' || echo "3001")
if curl -s "http://localhost:${API_PORT}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API is responding${NC}"
else
    echo -e "${YELLOW}⚠️  API health check failed (may need a moment to start)${NC}"
fi
echo ""

# Final summary
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "  pm2 status              - Check PM2 process status"
echo "  pm2 logs improve-api   - View API logs"
echo "  pm2 logs prefect-worker - View Prefect worker logs (if running)"
echo "  pm2 monit               - Monitor processes"
echo "  pm2 restart all        - Restart all processes"
echo ""
echo -e "${BLUE}Admin Login:${NC}"
echo "  Email: ${ADMIN_EMAIL:-admin@example.com}"
echo "  Password: ${ADMIN_PASSWORD:-admin123}"
echo ""

