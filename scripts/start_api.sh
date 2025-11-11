#!/bin/bash

# Start the unified Flask API (replaces Express backend)
# This provides both the admin dashboard and user-facing API endpoints

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting DailyQuestionBank Unified API${NC}"
echo "=========================================="

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if database is running
echo "Checking database connection..."
python3 -c "
from src.database.db import SessionLocal
try:
    session = SessionLocal()
    session.close()
    print('✓ Database connection successful')
except Exception as e:
    print(f'✗ Database connection failed: {e}')
    print('Make sure PostgreSQL is running: docker-compose up -d')
    exit(1)
"

if [ $? -ne 0 ]; then
    exit 1
fi

# Start the API server
echo ""
echo -e "${GREEN}Starting API server...${NC}"
echo "  Admin Dashboard: http://localhost:3001"
echo "  API Endpoints: http://localhost:3001/api/*"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Set API port to 3001 (same as old Express server)
export API_PORT=3001
export API_HOST=0.0.0.0

# Run the Flask API
python3 src/api/app.py

