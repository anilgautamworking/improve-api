"""Configuration management"""

import os
import logging
from typing import List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Settings:
    """Application settings loaded from environment variables"""

    # Database
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/daily_question_bank"
    )

    # AI Provider Selection
    AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").lower()  # "openai" or "ollama"

    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "1500"))

    # Ollama Configuration
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))

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
    MAX_ARTICLES_PER_CATEGORY = int(
        os.getenv("MAX_ARTICLES_PER_CATEGORY", "5")
    )  # Limit articles per category
    QUESTIONS_PER_CATEGORY_PER_DAY = int(
        os.getenv("QUESTIONS_PER_CATEGORY_PER_DAY", "12")
    )  # Target questions per category
    QUESTION_COUNT_MIN = int(os.getenv("QUESTION_COUNT_MIN", "3"))
    QUESTION_COUNT_MAX = int(
        os.getenv("QUESTION_COUNT_MAX", "5")
    )  # Reduced per article
    RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))
    
    # Browser/Scraping Configuration (CPU Optimization)
    MAX_CONCURRENT_BROWSER_OPERATIONS = int(os.getenv("MAX_CONCURRENT_BROWSER_OPERATIONS", "3"))
    # Limits concurrent Playwright browser operations to reduce CPU usage
    # Lower values (1-3) = less CPU usage, slower processing
    # Higher values (5-10) = faster processing, more CPU usage

    # Dashboard Configuration
    DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5000"))

    # Cron Schedule
    CRON_HOUR = int(os.getenv("CRON_HOUR", "6"))
    CRON_MINUTE = int(os.getenv("CRON_MINUTE", "0"))

    # Category Control
    # Comma-separated list of categories to enable for question generation.
    # Leave empty or set to "*" to allow all categories.
    ENABLED_CATEGORIES = os.getenv(
        "ENABLED_CATEGORIES",
        "Business,Economy,Current Affairs,Polity,History,Geography,Science & Technology,Environment,International Relations,General Knowledge,Banking,Trade,Explained",
    )

    @classmethod
    def get_enabled_categories(cls) -> List[str]:
        """Return normalized list of enabled categories. Empty list => all."""
        value = cls.ENABLED_CATEGORIES
        if not value or value.strip() == "*":
            return []

        categories = [cat.strip() for cat in value.split(",") if cat.strip()]

        seen = set()
        unique_categories = []
        for cat in categories:
            key = cat.lower()
            if key not in seen:
                unique_categories.append(cat)
                seen.add(key)

        return unique_categories

    @classmethod
    def is_category_enabled(cls, category: str) -> bool:
        """Check whether a category is enabled for processing."""
        enabled = cls.get_enabled_categories()
        if not enabled:  # all categories allowed
            return True
        if not category:
            return True

        enabled_lower = {cat.lower() for cat in enabled}
        return category.lower() in enabled_lower

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
        if cls.AI_PROVIDER == "openai":
            if not cls.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is required when AI_PROVIDER=openai")
        elif cls.AI_PROVIDER == "ollama":
            # Ollama doesn't require API key, but we'll check if it's running
            # Note: This is a soft check - actual connection will be verified when client is created
            try:
                import requests

                response = requests.get(f"{cls.OLLAMA_BASE_URL}/api/tags", timeout=2)
                if response.status_code != 200:
                    logger.warning(
                        f"Ollama may not be running at {cls.OLLAMA_BASE_URL}. Start with: ollama serve"
                    )
            except ImportError:
                pass  # requests might not be available during validation
            except Exception as e:
                logger.warning(
                    f"Cannot connect to Ollama at {cls.OLLAMA_BASE_URL}: {str(e)}. Will retry during initialization."
                )
                # Don't fail validation - let the client handle it
        else:
            raise ValueError(
                f"Invalid AI_PROVIDER: {cls.AI_PROVIDER}. Must be 'openai' or 'ollama'"
            )

        if not cls.DATABASE_URL:
            raise ValueError("DATABASE_URL is required")
        return True


def _validate_dashboard_secret():
    """Validate dashboard secret key is set and strong"""
    dashboard_secret = os.getenv("DASHBOARD_SECRET_KEY")
    
    if not dashboard_secret:
        raise ValueError(
            "DASHBOARD_SECRET_KEY environment variable is required. "
            "Please set it in your .env file. "
            "Generate a strong secret: python3 -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    
    # Check for default/weak secrets
    weak_secrets = [
        "dev-secret-key-change-in-production",
        "your-dashboard-secret-key-here-minimum-32-characters",
        "dev-secret",
        "secret",
        "password",
        "123456",
    ]
    
    if dashboard_secret in weak_secrets or len(dashboard_secret) < 32:
        raise ValueError(
            f"DASHBOARD_SECRET_KEY is too weak or too short (minimum 32 characters). "
            f"Current value: '{dashboard_secret[:20]}...' ({len(dashboard_secret)} chars)\n"
            f"Please set a strong secret in your .env file. "
            f"Generate one: python3 -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    
    return dashboard_secret


# Set validated dashboard secret
Settings.DASHBOARD_SECRET_KEY = _validate_dashboard_secret()

# Global settings instance
settings = Settings()

