"""Configuration management"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables"""

    # Database
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/daily_question_bank"
    )

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/daily_question_bank.log")

    # RSS Feeds
    RSS_FEEDS_THE_HINDU_BUSINESS = os.getenv(
        "RSS_FEEDS_THE_HINDU_BUSINESS",
        "https://www.thehindu.com/business/feeder/default.rss"
    )
    RSS_FEEDS_THE_HINDU_ECONOMY = os.getenv(
        "RSS_FEEDS_THE_HINDU_ECONOMY",
        "https://www.thehindu.com/business/economy/feeder/default.rss"
    )
    RSS_FEEDS_INDIAN_EXPRESS_BUSINESS = os.getenv(
        "RSS_FEEDS_INDIAN_EXPRESS_BUSINESS",
        "https://indianexpress.com/section/business/feed/"
    )
    RSS_FEEDS_INDIAN_EXPRESS_EXPLAINED = os.getenv(
        "RSS_FEEDS_INDIAN_EXPRESS_EXPLAINED",
        "https://indianexpress.com/section/explained/feed/"
    )

    # Processing Configuration
    MAX_ARTICLES_PER_RUN = int(os.getenv("MAX_ARTICLES_PER_RUN", "50"))
    QUESTION_COUNT_MIN = int(os.getenv("QUESTION_COUNT_MIN", "5"))
    QUESTION_COUNT_MAX = int(os.getenv("QUESTION_COUNT_MAX", "15"))
    RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))

    # Dashboard Configuration
    DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5000"))
    DASHBOARD_SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "dev-secret-key-change-in-production")

    # Cron Schedule
    CRON_HOUR = int(os.getenv("CRON_HOUR", "6"))
    CRON_MINUTE = int(os.getenv("CRON_MINUTE", "0"))

    @classmethod
    def get_rss_feeds_config(cls) -> list:
        """Get RSS feed configurations"""
        return [
            {
                "source": "The Hindu",
                "category": "Business",
                "urls": [cls.RSS_FEEDS_THE_HINDU_BUSINESS]
            },
            {
                "source": "The Hindu",
                "category": "Economy",
                "urls": [cls.RSS_FEEDS_THE_HINDU_ECONOMY]
            },
            {
                "source": "Indian Express",
                "category": "Business",
                "urls": [cls.RSS_FEEDS_INDIAN_EXPRESS_BUSINESS]
            },
            {
                "source": "Indian Express",
                "category": "Explained",
                "urls": [cls.RSS_FEEDS_INDIAN_EXPRESS_EXPLAINED]
            }
        ]

    @classmethod
    def validate(cls) -> bool:
        """Validate required settings"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")
        if not cls.DATABASE_URL:
            raise ValueError("DATABASE_URL is required")
        return True


# Global settings instance
settings = Settings()

