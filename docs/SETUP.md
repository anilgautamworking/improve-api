# Setup Guide

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Up Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration:
   # - DATABASE_URL: PostgreSQL connection string
   # - OPENAI_API_KEY: Your OpenAI API key
   ```

3. **Set Up Database**
   ```bash
   # Create PostgreSQL database
   createdb daily_question_bank
   
   # Run migrations
   alembic upgrade head
   ```

4. **Test the Pipeline**
   ```bash
   python scripts/run_daily_pipeline.py
   ```

5. **Set Up Cron Job**
   ```bash
   chmod +x scripts/setup_cron.sh
   ./scripts/setup_cron.sh
   ```

6. **Start Dashboard**
   ```bash
   python src/dashboard/app.py
   # Access at http://localhost:5000
   ```

## Project Structure

```
DailyQuestionBank-automation/
├── src/
│   ├── database/
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── db.py              # Database connection
│   │   └── repositories/      # Database repositories
│   ├── fetchers/
│   │   ├── rss_fetcher.py     # RSS feed fetcher
│   │   ├── html_scraper.py   # HTML scraper
│   │   └── pdf_parser.py      # PDF parser
│   ├── ai/
│   │   └── openai_client.py  # OpenAI API client
│   ├── generators/
│   │   ├── question_generator.py  # Question generator
│   │   └── mcq_prompts.py         # Prompt templates
│   ├── pipeline/
│   │   └── orchestrator.py   # Main pipeline
│   ├── utils/
│   │   ├── filters.py         # Content filters
│   │   ├── content_cleaner.py # Text cleaning
│   │   └── logger.py          # Logging setup
│   ├── config/
│   │   └── settings.py       # Configuration
│   └── dashboard/
│       ├── app.py             # Flask dashboard
│       └── templates/         # HTML templates
├── scripts/
│   ├── run_daily_pipeline.py # Main pipeline script
│   └── setup_cron.sh         # Cron setup script
├── alembic/                   # Database migrations
├── requirements.txt           # Python dependencies
└── README.md                  # Project documentation
```

## Configuration

All configuration is done via environment variables in `.env` file. See `.env.example` for available options.

## Troubleshooting

- **Database connection errors**: Check DATABASE_URL in .env
- **OpenAI API errors**: Verify OPENAI_API_KEY is set correctly
- **Import errors**: Make sure you're running from project root and src/ is in Python path
- **Cron not running**: Check logs/cron.log for errors

