#!/bin/bash
# Script to restore database from dump and apply newer migrations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

DUMP_FILE="${1:-improve-full.gz}"

if [ ! -f "$DUMP_FILE" ]; then
    echo -e "${RED}❌ Dump file not found: $DUMP_FILE${NC}"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Database Restore Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env | grep -v '^$' | xargs) 2>/dev/null || true

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}❌ DATABASE_URL not set in .env file${NC}"
    exit 1
fi

echo -e "${BLUE}Database URL: ${DATABASE_URL}${NC}"
echo -e "${BLUE}Dump file: ${DUMP_FILE}${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    exit 1
fi

# Check if postgres container is running
if ! docker ps | grep -q "improve_db"; then
    echo -e "${YELLOW}⚠️  PostgreSQL container not running. Starting it...${NC}"
    docker-compose up -d postgres
    echo -e "${BLUE}Waiting for PostgreSQL to be ready...${NC}"
    sleep 5
    
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
fi

echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
echo ""

# Backup current state (just in case)
echo -e "${BLUE}Creating backup of current state...${NC}"
BACKUP_FILE="backup_before_restore_$(date +%Y%m%d_%H%M%S).sql"
docker exec improve_db pg_dump -U improve-user -d improve-db > "$BACKUP_FILE" 2>/dev/null || true
if [ -f "$BACKUP_FILE" ]; then
    echo -e "${GREEN}✓ Backup saved to: $BACKUP_FILE${NC}"
fi
echo ""

# Check current data counts
echo -e "${BLUE}Current database state:${NC}"
CURRENT_QUESTIONS=$(docker exec improve_db psql -U improve-user -d improve-db -t -c "SELECT COUNT(*) FROM daily_questions;" 2>/dev/null | tr -d ' ' || echo "0")
CURRENT_ARTICLES=$(docker exec improve_db psql -U improve-user -d improve-db -t -c "SELECT COUNT(*) FROM article_logs;" 2>/dev/null | tr -d ' ' || echo "0")
echo -e "  Questions: $CURRENT_QUESTIONS"
echo -e "  Articles: $CURRENT_ARTICLES"
echo ""

# Ask for confirmation
read -p "This will DROP all existing tables and restore from dump. Continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo -e "${YELLOW}Restore cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}Step 1: Dropping all existing tables...${NC}"
docker exec improve_db psql -U improve-user -d improve-db -c "
    DO \$\$ 
    DECLARE 
        r RECORD;
    BEGIN
        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') 
        LOOP
            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
        END LOOP;
    END \$\$;
" 2>&1 | grep -v "NOTICE" || true

echo -e "${GREEN}✓ Tables dropped${NC}"
echo ""

# Step 2: Fix dump file if needed (add CASCADE to DROP statements)
echo -e "${BLUE}Step 2: Preparing dump file...${NC}"
FIXED_DUMP=""
if python3 scripts/fix_dump_for_restore.py "$DUMP_FILE" > /dev/null 2>&1; then
    FIXED_DUMP="${DUMP_FILE%.gz}_fixed.sql.gz"
    if [ -f "$FIXED_DUMP" ]; then
        echo -e "${GREEN}✓ Created fixed dump with CASCADE: $FIXED_DUMP${NC}"
        DUMP_FILE="$FIXED_DUMP"
    else
        echo -e "${YELLOW}⚠️  Could not create fixed dump, using original${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Could not fix dump automatically, using original${NC}"
fi
echo ""

# Step 3: Restore the dump
echo -e "${BLUE}Step 3: Restoring dump file...${NC}"
if [[ "$DUMP_FILE" == *.gz ]]; then
    gunzip -c "$DUMP_FILE" | docker exec -i improve_db psql -U improve-user -d improve-db 2>&1 | grep -v "NOTICE" | grep -v "does not exist" || true
else
    cat "$DUMP_FILE" | docker exec -i improve_db psql -U improve-user -d improve-db 2>&1 | grep -v "NOTICE" | grep -v "does not exist" || true
fi

# Check if restore was successful
RESTORE_ERROR=$(docker exec improve_db psql -U improve-user -d improve-db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ' || echo "0")

if [ "$RESTORE_ERROR" = "0" ]; then
    echo -e "${RED}❌ Restore failed - no tables found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Dump restored${NC}"

# Clean up fixed dump if we created it
if [ -n "$FIXED_DUMP" ] && [ -f "$FIXED_DUMP" ]; then
    rm -f "$FIXED_DUMP"
    echo -e "${BLUE}  Cleaned up temporary fixed dump file${NC}"
fi
echo ""

# Step 4: Check restored data
echo -e "${BLUE}Step 4: Verifying restored data...${NC}"
RESTORED_QUESTIONS=$(docker exec improve_db psql -U improve-user -d improve-db -t -c "SELECT COUNT(*) FROM daily_questions;" 2>/dev/null | tr -d ' ' || echo "0")
RESTORED_ARTICLES=$(docker exec improve_db psql -U improve-user -d improve-db -t -c "SELECT COUNT(*) FROM article_logs;" 2>/dev/null | tr -d ' ' || echo "0")
RESTORED_CATEGORIES=$(docker exec improve_db psql -U improve-user -d improve-db -t -c "SELECT COUNT(*) FROM categories;" 2>/dev/null | tr -d ' ' || echo "0")

echo -e "${GREEN}✓ Restored data:${NC}"
echo -e "  Questions: $RESTORED_QUESTIONS"
echo -e "  Articles: $RESTORED_ARTICLES"
echo -e "  Categories: $RESTORED_CATEGORIES"
echo ""

# Step 5: Check current Alembic version
echo -e "${BLUE}Step 5: Checking Alembic version...${NC}"
CURRENT_REVISION=$(docker exec improve_db psql -U improve-user -d improve-db -t -c "SELECT version_num FROM alembic_version LIMIT 1;" 2>/dev/null | tr -d ' ' || echo "")
echo -e "  Current revision: ${CURRENT_REVISION:-'none'}"
echo ""

# Step 6: Check what migrations need to be run
echo -e "${BLUE}Step 6: Determining which migrations to run...${NC}"
if [ -n "$CURRENT_REVISION" ]; then
    echo -e "  Dump has revision: $CURRENT_REVISION"
    if [ "$CURRENT_REVISION" = "003_add_frontend_schema" ]; then
        echo -e "${GREEN}✓ Dump is at revision 003. Only need to run migration 004 (exam system)${NC}"
    elif [ "$CURRENT_REVISION" = "004_add_exam_system" ]; then
        echo -e "${GREEN}✓ Dump is already at latest revision${NC}"
    else
        echo -e "${YELLOW}⚠️  Dump has revision $CURRENT_REVISION. Will run migrations to head${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Could not determine revision. Will run all migrations${NC}"
fi
echo ""

# Step 7: Run newer migrations
echo -e "${BLUE}Step 7: Running newer migrations...${NC}"
if [ "$CURRENT_REVISION" = "003_add_frontend_schema" ]; then
    echo -e "${YELLOW}This will add: exams and exam_category tables${NC}"
else
    echo -e "${YELLOW}This will add missing tables and update schema to latest version${NC}"
fi
echo ""

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
    echo -e "${YELLOW}Trying to restore from backup...${NC}"
    if [ -f "$BACKUP_FILE" ]; then
        echo -e "${BLUE}You can restore from: $BACKUP_FILE${NC}"
    fi
    exit 1
fi

# Step 7.5: Seed exam-category mappings if needed
echo -e "${BLUE}Step 7.5: Seeding exam-category mappings...${NC}"
if [ -d "venv" ]; then
    source venv/bin/activate
fi

if python3 scripts/seed_exam_categories.py > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Exam-category mappings seeded${NC}"
else
    echo -e "${YELLOW}⚠️  Could not seed exam-category mappings automatically${NC}"
    echo -e "${BLUE}  You may need to run manually: python3 scripts/seed_exam_categories.py${NC}"
fi
echo ""

# Step 8: Final verification
echo ""
echo -e "${BLUE}Step 8: Final verification...${NC}"
FINAL_REVISION=$(docker exec improve_db psql -U improve-user -d improve-db -t -c "SELECT version_num FROM alembic_version LIMIT 1;" 2>/dev/null | tr -d ' ' || echo "")
FINAL_TABLES=$(docker exec improve_db psql -U improve-user -d improve-db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ' || echo "0")
FINAL_QUESTIONS=$(docker exec improve_db psql -U improve-user -d improve-db -t -c "SELECT COUNT(*) FROM daily_questions;" 2>/dev/null | tr -d ' ' || echo "0")

echo -e "${GREEN}✓ Restore complete!${NC}"
echo -e "${BLUE}  - Alembic revision: $FINAL_REVISION${NC}"
echo -e "${BLUE}  - Total tables: $FINAL_TABLES${NC}"
echo -e "${BLUE}  - Questions preserved: $FINAL_QUESTIONS${NC}"
echo ""
echo -e "${GREEN}✅ Database restore successful!${NC}"

