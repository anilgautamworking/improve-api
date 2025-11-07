#!/bin/bash
# Setup script for local development

set -e

echo "🚀 Setting up Daily Question Bank Automation System..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/daily_question_bank

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=2000

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/daily_question_bank.log

# RSS Feed Sources
RSS_FEEDS_THE_HINDU_BUSINESS=https://www.thehindu.com/business/feeder/default.rss
RSS_FEEDS_THE_HINDU_ECONOMY=https://www.thehindu.com/business/economy/feeder/default.rss
RSS_FEEDS_INDIAN_EXPRESS_BUSINESS=https://indianexpress.com/section/business/feed/
RSS_FEEDS_INDIAN_EXPRESS_EXPLAINED=https://indianexpress.com/section/explained/feed/

# Category Control
ENABLED_CATEGORIES=Business,Economy,Current Affairs,Polity,History,Geography,Science & Technology,Environment,International Relations,General Knowledge,Banking,Trade,Explained

# Processing Configuration
MAX_ARTICLES_PER_RUN=50
QUESTION_COUNT_MIN=5
QUESTION_COUNT_MAX=15
RETRY_ATTEMPTS=3
RETRY_DELAY=5

# Dashboard Configuration
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=5000
DASHBOARD_SECRET_KEY=dev-secret-key-change-in-production

# Cron Schedule
CRON_HOUR=6
CRON_MINUTE=0
EOF
    echo "✅ .env file created. Please add your OpenAI API key!"
else
    echo "✅ .env file already exists"
fi

# Start PostgreSQL database
echo "🐘 Starting PostgreSQL database..."
docker-compose up -d postgres

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 5

MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker exec daily_question_bank_db pg_isready -U postgres > /dev/null 2>&1; then
        echo "✅ Database is ready!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    sleep 1
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ Database failed to start. Please check Docker logs."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create logs directory
mkdir -p logs

# Run database migrations
echo "🗄️  Running database migrations..."
alembic upgrade head

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env file and add your OpenAI API key"
echo "2. To run the pipeline manually: python scripts/run_daily_pipeline.py"
echo "3. To start the dashboard: python src/dashboard/app.py"
echo ""
echo "🐘 Database is running in Docker. To stop: docker-compose down"
echo ""


