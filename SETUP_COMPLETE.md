# Complete Setup Guide for Daily Question Bank Automation

This guide will help you set up and run the automated question bank system from scratch.

## System Overview

This system automatically:
1. Fetches daily news from RSS feeds (The Hindu, Indian Express)
2. Scrapes and cleans article content
3. Generates MCQs using AI (OpenAI GPT or local Ollama)
4. Stores questions in PostgreSQL database
5. Provides a web dashboard for monitoring

## Prerequisites

### Required Software
- **Python 3.9+** (Python 3.13 recommended)
- **PostgreSQL 12+** (database for storing questions)
- **One of the following AI providers:**
  - OpenAI API key (paid, recommended for production)
  - OR Ollama (free, runs locally but requires good hardware)

### System Requirements
- **For OpenAI**: Any system with internet connection
- **For Ollama**: 
  - 8GB+ RAM for 8B models
  - 16GB+ RAM for larger models
  - Modern CPU (Apple Silicon recommended for Mac)

## Step-by-Step Installation

### 1. Clone and Setup Python Environment

```bash
cd /Users/techmarbles/Documents/DailyQuestionBank-automation

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for web scraping)
python3 -m playwright install chromium
```

### 2. Setup PostgreSQL Database

#### Option A: Install PostgreSQL Locally

**macOS (using Homebrew):**
```bash
brew install postgresql@15
brew services start postgresql@15
createdb daily_question_bank
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo -u postgres createdb daily_question_bank
```

**Windows:**
- Download from https://www.postgresql.org/download/windows/
- Install and create database `daily_question_bank`

#### Option B: Use Docker

```bash
docker run -d \
  --name question_bank_db \
  -e POSTGRES_DB=daily_question_bank \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:15
```

### 3. Configure Environment Variables

```bash
# Copy example environment file
cp env.example .env

# Edit .env file with your configuration
nano .env  # or use your preferred editor
```

#### For OpenAI (Recommended for Production):
```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/daily_question_bank

# AI Provider
AI_PROVIDER=openai
OPENAI_API_KEY=your_actual_api_key_here  # Get from https://platform.openai.com/api-keys
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=2000

# Processing
MAX_ARTICLES_PER_RUN=50
QUESTIONS_PER_CATEGORY_PER_DAY=12
QUESTION_COUNT_MIN=3
QUESTION_COUNT_MAX=5
```

#### For Ollama (Free, Local):
```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/daily_question_bank

# AI Provider
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_TEMPERATURE=0.7

# Processing
MAX_ARTICLES_PER_RUN=50
QUESTIONS_PER_CATEGORY_PER_DAY=12
QUESTION_COUNT_MIN=3
QUESTION_COUNT_MAX=5
```

**If using Ollama, install it first:**
```bash
# Install Ollama (https://ollama.ai)
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve &

# Pull the model
ollama pull llama3.1:8b
```

### 4. Initialize Database

```bash
# Run database migrations
alembic upgrade head
```

### 5. Validate Setup

Run the comprehensive validation script:

```bash
python3 scripts/setup_and_validate.py
```

This script will check:
- ✓ Python version
- ✓ Environment configuration
- ✓ Database connection
- ✓ Database schema
- ✓ Playwright installation
- ✓ AI provider connectivity
- ✓ RSS fetching
- ✓ Article scraping

Fix any issues reported by the script before proceeding.

## Usage

### Manual Pipeline Run (Test)

Run the pipeline manually to test everything:

```bash
python3 scripts/run_daily_pipeline.py
```

Expected output:
```
================================================================================
Starting Daily Question Bank Pipeline
Date: 2025-11-05 XX:XX:XX
================================================================================
Settings validated successfully
--- Stage 1: Crawling and Storing Articles ---
Crawling RSS feeds for The Hindu
...
--- Stage 2: Generating Questions from Stored Articles ---
...
================================================================================
Pipeline Summary:
  Feeds Processed: 4
  Articles Fetched: 25
  Articles Processed for QG: 12
  Questions Generated: 48
  Batches Saved: 12
  Processing Time: 245 seconds
================================================================================
```

### Start Dashboard

View the monitoring dashboard:

```bash
python3 src/dashboard/app.py
```

Then open your browser to: http://localhost:5000

The dashboard shows:
- Today's statistics
- Recent pipeline runs
- Total questions in database
- Questions by category and source

### Setup Automated Daily Runs

#### Option A: Using cron (macOS/Linux)

```bash
# Make setup script executable
chmod +x scripts/setup_cron.sh

# Run setup script
./scripts/setup_cron.sh
```

This will add a cron job to run the pipeline daily at 6:00 AM.

To modify the schedule, edit your crontab:
```bash
crontab -e
```

#### Option B: Manual cron setup

```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 6:00 AM)
0 6 * * * cd /Users/techmarbles/Documents/DailyQuestionBank-automation && ./venv/bin/python3 scripts/run_daily_pipeline.py >> logs/cron.log 2>&1
```

#### Option C: Using systemd timer (Linux)

Create a systemd service and timer:

```bash
# Create service file
sudo nano /etc/systemd/system/question-bank.service

# Create timer file
sudo nano /etc/systemd/system/question-bank.timer

# Enable and start timer
sudo systemctl enable question-bank.timer
sudo systemctl start question-bank.timer
```

## Project Structure

```
DailyQuestionBank-automation/
├── src/
│   ├── ai/                      # AI clients (OpenAI, Ollama)
│   │   ├── openai_client.py
│   │   └── ollama_client.py
│   ├── config/                  # Configuration management
│   │   └── settings.py
│   ├── dashboard/               # Web dashboard
│   │   ├── app.py
│   │   └── templates/
│   ├── database/                # Database models and repositories
│   │   ├── db.py
│   │   ├── models.py
│   │   └── repositories/
│   ├── fetchers/                # RSS, HTML, PDF fetchers
│   │   ├── rss_fetcher.py
│   │   ├── html_scraper.py
│   │   └── pdf_parser.py
│   ├── generators/              # Question generation
│   │   ├── question_generator.py
│   │   └── mcq_prompts.py
│   ├── pipeline/                # Pipeline orchestration
│   │   ├── orchestrator.py
│   │   └── crawler_orchestrator.py
│   └── utils/                   # Utility functions
│       ├── logger.py
│       ├── content_cleaner.py
│       ├── filters.py
│       └── article_scorer.py
├── scripts/                     # Automation scripts
│   ├── run_daily_pipeline.py
│   ├── setup_and_validate.py
│   ├── setup_cron.sh
│   └── start_dashboard.sh
├── alembic/                     # Database migrations
├── logs/                        # Application logs
├── docs/                        # Documentation
├── requirements.txt             # Python dependencies
├── .env                         # Environment configuration
└── README.md                    # Project overview
```

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/daily_question_bank` |
| `AI_PROVIDER` | AI provider (`openai` or `ollama`) | `openai` |
| `OPENAI_API_KEY` | OpenAI API key | Required if using OpenAI |
| `OPENAI_MODEL` | OpenAI model | `gpt-4` |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model name | `llama3.1:8b` |
| `MAX_ARTICLES_PER_RUN` | Max articles to process per run | `50` |
| `QUESTIONS_PER_CATEGORY_PER_DAY` | Target questions per category | `12` |
| `QUESTION_COUNT_MIN` | Min questions per article | `3` |
| `QUESTION_COUNT_MAX` | Max questions per article | `5` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DASHBOARD_HOST` | Dashboard host | `0.0.0.0` |
| `DASHBOARD_PORT` | Dashboard port | `5000` |

### RSS Feed Sources

The system currently fetches from:
- **The Hindu**: Business, Economy
- **Indian Express**: Business, Explained

To add more sources, edit `src/config/settings.py`:

```python
@classmethod
def get_rss_feeds_config(cls) -> list:
    return [
        {
            "source": "The Hindu",
            "category": "Politics",
            "urls": ["https://www.thehindu.com/news/national/feeder/default.rss"]
        },
        # Add more feeds here
    ]
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Error
```
Error: could not connect to server: Connection refused
```
**Solution:** Make sure PostgreSQL is running:
```bash
# macOS
brew services start postgresql@15

# Linux
sudo systemctl start postgresql

# Check status
psql -h localhost -U postgres -d daily_question_bank -c "SELECT 1;"
```

#### 2. OpenAI API Key Error
```
Error code: 401 - Invalid API key
```
**Solution:** 
- Get valid API key from https://platform.openai.com/api-keys
- Update `.env` file with correct key
- Make sure there are no extra spaces

#### 3. Playwright Browser Not Installed
```
Error: Executable doesn't exist at /path/to/chromium
```
**Solution:**
```bash
python3 -m playwright install chromium
```

#### 4. Ollama Not Running
```
Error: Cannot connect to Ollama at http://localhost:11434
```
**Solution:**
```bash
ollama serve &
ollama pull llama3.1:8b
```

#### 5. No Articles Fetched
- Check internet connection
- Verify RSS feed URLs are accessible
- Check logs: `tail -f logs/daily_question_bank.log`

#### 6. Import Errors
```
ModuleNotFoundError: No module named 'xyz'
```
**Solution:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Logs Location

- **Application logs**: `logs/daily_question_bank.log`
- **Cron logs**: `logs/cron.log` (if using cron)

View recent logs:
```bash
tail -f logs/daily_question_bank.log
```

## Performance Optimization

### For OpenAI Users
- Use `gpt-3.5-turbo` for faster, cheaper processing
- Adjust `MAX_ARTICLES_PER_RUN` based on your API limits
- Consider rate limiting for large batches

### For Ollama Users
- Use smaller models (7B-8B) for faster processing
- Consider using quantized models for lower memory usage
- Run Ollama with GPU acceleration if available

### Database Optimization
- Add indexes for frequently queried fields
- Archive old questions to separate table
- Use connection pooling (already configured)

## Monitoring and Maintenance

### Daily Checks
1. Check dashboard for today's statistics
2. Verify question count is within expected range
3. Review any error counts

### Weekly Maintenance
1. Review log files for recurring errors
2. Check database size
3. Verify cron job is running

### Monthly Tasks
1. Review and update RSS feed sources
2. Analyze question quality
3. Backup database:
```bash
pg_dump daily_question_bank > backup_$(date +%Y%m%d).sql
```

## API Endpoints

The dashboard provides REST API endpoints:

### Get Today's Statistics
```
GET /api/stats
```

### Get Questions by Date
```
GET /api/questions/2025-11-05
```

### Get Recent Summaries
```
GET /api/summaries?limit=30
```

## Extending the System

### Add New News Sources
1. Edit `src/config/settings.py`
2. Add RSS feed URL to `get_rss_feeds_config()`
3. Update scraper patterns in `src/fetchers/html_scraper.py` if needed

### Add PDF Support
1. Place government PDFs in a watched directory
2. Use `src/fetchers/pdf_parser.py` to parse
3. Integrate with pipeline orchestrator

### Customize Question Format
1. Edit prompts in `src/generators/mcq_prompts.py`
2. Modify validation logic in `src/generators/question_generator.py`

### Add New Categories
1. Update classification logic in `src/utils/filters.py`
2. Train custom classifier (optional)

## Security Best Practices

1. **Never commit `.env` file** to version control
2. **Rotate API keys** regularly
3. **Use strong database passwords**
4. **Restrict dashboard access** in production:
   - Use reverse proxy (nginx)
   - Add authentication
   - Enable HTTPS
5. **Regular backups** of database
6. **Monitor API costs** (for OpenAI users)

## Support and Documentation

- **Setup Issues**: Run `python3 scripts/setup_and_validate.py`
- **Detailed Docs**: See `docs/` directory
- **Logs**: Check `logs/daily_question_bank.log`
- **Database Schema**: `src/database/models.py`

## License

[Add your license information]

## Contributing

[Add contribution guidelines]

---

**Last Updated**: November 5, 2025
**Version**: 1.0.0

