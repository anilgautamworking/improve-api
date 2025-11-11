# Daily Automated Competitive Exam Question Bank Generator

An automated Python system that fetches daily news from RSS feeds, scrapes articles, extracts content from PDFs, and uses OpenAI API to generate exam-oriented multiple-choice questions (MCQs) for competitive examinations like UPSC, SSC, Banking, etc.

## Features

- **Automated Daily Processing**: Runs via cron jobs to fetch and process news articles daily
- **Multiple Sources**: Fetches from The Hindu, Indian Express RSS feeds
- **PDF Support**: Extracts content from government PDFs (Economic Survey, Union Budget, RBI Bulletins)
- **AI-Powered**: Uses OpenAI GPT-4/3.5 to generate structured MCQs
- **PostgreSQL Storage**: Stores questions and metadata in PostgreSQL database
- **Admin Dashboard**: Web dashboard for monitoring and statistics

## System Architecture

```
Daily Cron Job → RSS Feed Fetching → HTML/PDF Parsing → Content Filtering → 
AI Question Generation → PostgreSQL Storage → Admin Dashboard
```

## Setup Instructions

### Prerequisites

- Python 3.9 or higher
- PostgreSQL 12 or higher
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd DailyQuestionBank-automation
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Set up PostgreSQL database:
```bash
createdb daily_question_bank
```

6. Run database migrations:
```bash
alembic upgrade head
```

7. Configure cron job (optional):
```bash
chmod +x scripts/setup_cron.sh
./scripts/setup_cron.sh
```

## Configuration

Edit `.env` file with the following variables:

- `DATABASE_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_MODEL`: Model to use (gpt-4 or gpt-3.5-turbo)
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)

## Usage

### Manual Run

Run the daily pipeline manually:
```bash
python scripts/run_daily_pipeline.py
```

### Admin Dashboard

Start the dashboard server:
```bash
python src/dashboard/app.py
```

Access dashboard at: `http://localhost:5000`

### API Server

Start the unified API server (provides both API and admin dashboard):
```bash
python src/api/app.py
# or use the convenience script:
./scripts/start_api.sh
```

Access API at: `http://localhost:3001`

#### Health Check Endpoints

The API includes health check endpoints to monitor migration status:

- **`GET /health`** - Basic health check with migration status
- **`GET /api/health/migration`** - Detailed migration status

Example response:
```json
{
  "status": "healthy",
  "service": "DailyQuestionBank API",
  "migration": {
    "schema_exists": true,
    "questions_migrated": true,
    "question_count": 150,
    "batch_count": 45,
    "categories_count": 6,
    "status": "ready",
    "message": "Frontend schema and questions are ready"
  }
}
```

**Note:** The API automatically checks migration status on startup and logs warnings if the frontend schema is missing or questions need migration.

## Project Structure

```
DailyQuestionBank-automation/
├── src/
│   ├── database/          # Database models and connections
│   ├── fetchers/          # RSS, HTML, PDF fetchers
│   ├── ai/                # OpenAI integration
│   ├── generators/        # Question generation logic
│   ├── pipeline/          # Main pipeline orchestrator
│   ├── utils/             # Utility functions
│   ├── config/            # Configuration management
│   └── dashboard/         # Admin dashboard
├── scripts/               # Cron scripts and utilities
├── tests/                 # Unit tests
├── alembic/               # Database migrations
├── docs/                  # Documentation
└── requirements.txt       # Python dependencies
```

## Development

Run tests:
```bash
pytest tests/
```

Format code:
```bash
black src/ tests/
```

## License

[Add your license here]

