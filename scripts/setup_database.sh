#!/bin/bash
# Script to setup database and run migrations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Database Setup and Migration Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    if [ -f env.example ]; then
        cp env.example .env
        echo -e "${GREEN}✓ Created .env file from env.example${NC}"
        echo -e "${YELLOW}⚠️  Please update DATABASE_URL and other settings in .env file${NC}"
    else
        echo -e "${RED}❌ env.example not found. Please create .env file manually.${NC}"
        exit 1
    fi
fi

# Load environment variables
export $(grep -v '^#' .env | grep -v '^$' | xargs) 2>/dev/null || true

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}❌ DATABASE_URL not set in .env file${NC}"
    echo -e "${YELLOW}Please set: DATABASE_URL=postgresql://improve-user:improve123@localhost:5442/improve-db${NC}"
    exit 1
fi

echo -e "${BLUE}Database URL: ${DATABASE_URL}${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Check if postgres container is running
if ! docker ps | grep -q "improve_db"; then
    echo -e "${YELLOW}⚠️  PostgreSQL container not running. Starting it...${NC}"
    docker-compose up -d postgres
    echo -e "${BLUE}Waiting for PostgreSQL to be ready...${NC}"
    sleep 5
    
    # Wait for postgres to be ready
    max_attempts=30
    attempt=0
    until docker exec improve_db pg_isready -U improve-user -d improve-db > /dev/null 2>&1; do
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            echo -e "${RED}❌ PostgreSQL did not become ready in time${NC}"
            exit 1
        fi
        sleep 1
    done
    echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
else
    echo -e "${GREEN}✓ PostgreSQL container is running${NC}"
fi

# Check if database has existing data
echo ""
echo -e "${BLUE}Checking database state...${NC}"
TABLES_COUNT=$(docker exec improve_db psql -U improve-user -d improve-db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ' || echo "0")

if [ "$TABLES_COUNT" -gt "0" ]; then
    echo -e "${GREEN}✓ Found $TABLES_COUNT tables in database${NC}"
    
    # Check if alembic_version table exists
    ALEMBIC_EXISTS=$(docker exec improve_db psql -U improve-user -d improve-db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'alembic_version';" 2>/dev/null | tr -d ' ' || echo "0")
    
    if [ "$ALEMBIC_EXISTS" -eq "1" ]; then
        CURRENT_REVISION=$(docker exec improve_db psql -U improve-user -d improve-db -t -c "SELECT version_num FROM alembic_version;" 2>/dev/null | tr -d ' ' || echo "")
        echo -e "${GREEN}✓ Alembic version table exists. Current revision: ${CURRENT_REVISION:-'none'}${NC}"
    else
        echo -e "${YELLOW}⚠️  Alembic version table not found. This might be an old database.${NC}"
    fi
    
    # Count records in main tables
    echo ""
    echo -e "${BLUE}Checking existing data...${NC}"
    QUESTIONS_COUNT=$(docker exec improve_db psql -U improve-user -d improve-db -t -c "SELECT COUNT(*) FROM daily_questions;" 2>/dev/null | tr -d ' ' || echo "0")
    ARTICLES_COUNT=$(docker exec improve_db psql -U improve-user -d improve-db -t -c "SELECT COUNT(*) FROM article_logs;" 2>/dev/null | tr -d ' ' || echo "0")
    
    echo -e "${GREEN}✓ Found $QUESTIONS_COUNT questions and $ARTICLES_COUNT articles${NC}"
else
    echo -e "${YELLOW}⚠️  No tables found. Database appears to be empty.${NC}"
fi

echo ""
echo -e "${BLUE}Running database migrations...${NC}"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run migrations
if command -v alembic &> /dev/null; then
    alembic upgrade head
elif python -m alembic &> /dev/null; then
    python -m alembic upgrade head
else
    echo -e "${RED}❌ Alembic not found. Please install dependencies: pip install -r requirements.txt${NC}"
    exit 1
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Migrations completed successfully${NC}"
else
    echo -e "${RED}❌ Migration failed!${NC}"
    exit 1
fi

# Verify final state
echo ""
echo -e "${BLUE}Verifying database state...${NC}"
FINAL_TABLES=$(docker exec improve_db psql -U improve-user -d improve-db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ' || echo "0")
FINAL_REVISION=$(docker exec improve_db psql -U improve-user -d improve-db -t -c "SELECT version_num FROM alembic_version;" 2>/dev/null | tr -d ' ' || echo "")

echo -e "${GREEN}✓ Database setup complete!${NC}"
echo -e "${BLUE}  - Total tables: $FINAL_TABLES${NC}"
echo -e "${BLUE}  - Current Alembic revision: ${FINAL_REVISION:-'none'}${NC}"
echo ""
echo -e "${GREEN}✅ Database is ready to use!${NC}"

