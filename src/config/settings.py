"""Configuration management"""

import os
import logging
from typing import List, Optional, Dict
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
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "myaniu/qwen2.5-1m:14b")
    OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/daily_question_bank.log")

    # RSS Feeds - The Hindu
    RSS_FEEDS_THE_HINDU_MAIN = os.getenv(
        "RSS_FEEDS_THE_HINDU_MAIN",
        "https://www.thehindu.com/feeder/default.rss"
    )
    RSS_FEEDS_THE_HINDU_INDIA = os.getenv(
        "RSS_FEEDS_THE_HINDU_INDIA",
        "https://www.thehindu.com/news/national/feeder/default.rss"
    )
    RSS_FEEDS_THE_HINDU_WORLD = os.getenv(
        "RSS_FEEDS_THE_HINDU_WORLD",
        "https://www.thehindu.com/news/international/feeder/default.rss"
    )
    RSS_FEEDS_THE_HINDU_OPINION = os.getenv(
        "RSS_FEEDS_THE_HINDU_OPINION",
        "https://www.thehindu.com/opinion/feeder/default.rss"
    )
    RSS_FEEDS_THE_HINDU_SPORTS = os.getenv(
        "RSS_FEEDS_THE_HINDU_SPORTS",
        "https://www.thehindu.com/sport/feeder/default.rss"
    )
    RSS_FEEDS_THE_HINDU_BUSINESS = os.getenv(
        "RSS_FEEDS_THE_HINDU_BUSINESS",
        "https://www.thehindu.com/business/feeder/default.rss"
    )
    RSS_FEEDS_THE_HINDU_ECONOMY = os.getenv(
        "RSS_FEEDS_THE_HINDU_ECONOMY",
        "https://www.thehindu.com/business/economy/feeder/default.rss"
    )
    RSS_FEEDS_THE_HINDU_MARKETS = os.getenv(
        "RSS_FEEDS_THE_HINDU_MARKETS",
        "https://www.thehindu.com/business/markets/feeder/default.rss"
    )
    RSS_FEEDS_THE_HINDU_SCIENCE = os.getenv(
        "RSS_FEEDS_THE_HINDU_SCIENCE",
        "https://www.thehindu.com/sci-tech/science/feeder/default.rss"
    )

    # RSS Feeds - The Hindu BusinessLine
    RSS_FEEDS_BUSINESSLINE_MAIN = os.getenv(
        "RSS_FEEDS_BUSINESSLINE_MAIN",
        "https://www.thehindubusinessline.com/news/feeder/default.rss"
    )
    RSS_FEEDS_BUSINESSLINE_BUSINESS = os.getenv(
        "RSS_FEEDS_BUSINESSLINE_BUSINESS",
        "https://www.thehindubusinessline.com/business/feeder/default.rss"
    )
    RSS_FEEDS_BUSINESSLINE_ECONOMY = os.getenv(
        "RSS_FEEDS_BUSINESSLINE_ECONOMY",
        "https://www.thehindubusinessline.com/economy/feeder/default.rss"
    )
    RSS_FEEDS_BUSINESSLINE_MACRO = os.getenv(
        "RSS_FEEDS_BUSINESSLINE_MACRO",
        "https://www.thehindubusinessline.com/economy/macro-economy/feeder/default.rss"
    )
    RSS_FEEDS_BUSINESSLINE_AGRI = os.getenv(
        "RSS_FEEDS_BUSINESSLINE_AGRI",
        "https://www.thehindubusinessline.com/economy/agri-business/feeder/default.rss"
    )
    RSS_FEEDS_BUSINESSLINE_MONEY = os.getenv(
        "RSS_FEEDS_BUSINESSLINE_MONEY",
        "https://www.thehindubusinessline.com/money-and-banking/feeder/default.rss"
    )
    RSS_FEEDS_BUSINESSLINE_SPORTS = os.getenv(
        "RSS_FEEDS_BUSINESSLINE_SPORTS",
        "https://www.thehindubusinessline.com/sport/feeder/default.rss"
    )

    # RSS Feeds - Indian Express
    RSS_FEEDS_INDIAN_EXPRESS_MAIN = os.getenv(
        "RSS_FEEDS_INDIAN_EXPRESS_MAIN",
        "https://indianexpress.com/feed"
    )
    RSS_FEEDS_INDIAN_EXPRESS_INDIA = os.getenv(
        "RSS_FEEDS_INDIAN_EXPRESS_INDIA",
        "https://indianexpress.com/section/india/feed"
    )
    RSS_FEEDS_INDIAN_EXPRESS_WORLD = os.getenv(
        "RSS_FEEDS_INDIAN_EXPRESS_WORLD",
        "https://indianexpress.com/section/world/feed"
    )
    RSS_FEEDS_INDIAN_EXPRESS_BUSINESS = os.getenv(
        "RSS_FEEDS_INDIAN_EXPRESS_BUSINESS",
        "https://indianexpress.com/section/business/feed/"
    )
    RSS_FEEDS_INDIAN_EXPRESS_ECONOMICS = os.getenv(
        "RSS_FEEDS_INDIAN_EXPRESS_ECONOMICS",
        "https://indianexpress.com/section/economics/feed/"
    )
    RSS_FEEDS_INDIAN_EXPRESS_SPORTS = os.getenv(
        "RSS_FEEDS_INDIAN_EXPRESS_SPORTS",
        "https://indianexpress.com/section/sports/feed/"
    )
    RSS_FEEDS_INDIAN_EXPRESS_ENTERTAINMENT = os.getenv(
        "RSS_FEEDS_INDIAN_EXPRESS_ENTERTAINMENT",
        "https://indianexpress.com/section/entertainment/feed/"
    )
    RSS_FEEDS_INDIAN_EXPRESS_LIFESTYLE = os.getenv(
        "RSS_FEEDS_INDIAN_EXPRESS_LIFESTYLE",
        "https://indianexpress.com/section/lifestyle/feed/"
    )
    RSS_FEEDS_INDIAN_EXPRESS_TECHNOLOGY = os.getenv(
        "RSS_FEEDS_INDIAN_EXPRESS_TECHNOLOGY",
        "https://indianexpress.com/section/technology/feed/"
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
        os.getenv("QUESTION_COUNT_MAX", "4")
    )
    ARTICLE_CONTEXT_MAX_CHARS = int(
        os.getenv("ARTICLE_CONTEXT_MAX_CHARS", "2500")
    )  # Keep prompts within LLM timeout budget
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
        (
            "Current Affairs,India,World,Opinion,Sports,Business,Economy,Markets,"
            "Science & Technology,Banking,Macro Economy,Agri Business,Money & Banking,"
            "Lifestyle,Entertainment,Technology,General Knowledge,Explained,Trade,Polity,History,Geography"
        ),
    )

    MIN_ARTICLE_SCORE = float(os.getenv("MIN_ARTICLE_SCORE", "45"))
    QUESTION_QUALITY_MIN_SCORE = float(os.getenv("QUESTION_QUALITY_MIN_SCORE", "65"))
    PDF_ONLY_CATEGORIES = os.getenv(
        "PDF_ONLY_CATEGORIES",
        "Physics,Chemistry,Mathematics,Biology"
    )
    PDF_SOURCE_NAMES = os.getenv(
        "PDF_SOURCE_NAMES",
        "PDF,Academic PDF,NCERT,HC Verma,Study Material"
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
    def get_pdf_only_categories(cls) -> List[str]:
        """Categories that should only be served by PDF ingestion"""
        return cls._parse_feed_urls(cls.PDF_ONLY_CATEGORIES)

    @classmethod
    def is_pdf_only_category(cls, category: Optional[str]) -> bool:
        """Check whether a category must come from PDF sources"""
        if not category:
            return False
        pdf_only = {cat.lower() for cat in cls.get_pdf_only_categories()}
        return category.lower() in pdf_only

    @classmethod
    def get_pdf_sources(cls) -> List[str]:
        """List of source labels treated as PDF/academic imports"""
        return cls._parse_feed_urls(cls.PDF_SOURCE_NAMES)

    @classmethod
    def is_pdf_source(cls, source: Optional[str]) -> bool:
        """Check whether the given source name counts as PDF/academic"""
        if not source:
            return False
        valid_sources = {name.lower() for name in cls.get_pdf_sources()}
        return source.lower() in valid_sources

    @staticmethod
    def _parse_feed_urls(value: str) -> List[str]:
        """Parse comma or newline separated feed URLs into a list"""
        if not value:
            return []
        normalized = value.replace("\n", ",")
        return [url.strip() for url in normalized.split(",") if url.strip()]

    @classmethod
    def _build_feed_config(cls, source: str, category: str, urls_value: str) -> Optional[Dict]:
        """Helper to build feed config entry"""
        urls = cls._parse_feed_urls(urls_value)
        if not urls:
            return None
        return {
            "source": source,
            "category": category,
            "urls": urls
        }

    @classmethod
    def get_rss_feeds_config(cls) -> list:
        """Get RSS feed configurations"""
        feed_definitions = [
            # The Hindu
            ("The Hindu", "Current Affairs", cls.RSS_FEEDS_THE_HINDU_MAIN),
            ("The Hindu", "India", cls.RSS_FEEDS_THE_HINDU_INDIA),
            ("The Hindu", "World", cls.RSS_FEEDS_THE_HINDU_WORLD),
            ("The Hindu", "Opinion", cls.RSS_FEEDS_THE_HINDU_OPINION),
            ("The Hindu", "Sports", cls.RSS_FEEDS_THE_HINDU_SPORTS),
            ("The Hindu", "Business", cls.RSS_FEEDS_THE_HINDU_BUSINESS),
            ("The Hindu", "Economy", cls.RSS_FEEDS_THE_HINDU_ECONOMY),
            ("The Hindu", "Markets", cls.RSS_FEEDS_THE_HINDU_MARKETS),
            ("The Hindu", "Science & Technology", cls.RSS_FEEDS_THE_HINDU_SCIENCE),

            # The Hindu BusinessLine
            ("The Hindu BusinessLine", "Current Affairs", cls.RSS_FEEDS_BUSINESSLINE_MAIN),
            ("The Hindu BusinessLine", "Business", cls.RSS_FEEDS_BUSINESSLINE_BUSINESS),
            ("The Hindu BusinessLine", "Economy", cls.RSS_FEEDS_BUSINESSLINE_ECONOMY),
            ("The Hindu BusinessLine", "Macro Economy", cls.RSS_FEEDS_BUSINESSLINE_MACRO),
            ("The Hindu BusinessLine", "Agri Business", cls.RSS_FEEDS_BUSINESSLINE_AGRI),
            ("The Hindu BusinessLine", "Money & Banking", cls.RSS_FEEDS_BUSINESSLINE_MONEY),
            ("The Hindu BusinessLine", "Sports", cls.RSS_FEEDS_BUSINESSLINE_SPORTS),

            # Indian Express
            ("Indian Express", "Current Affairs", cls.RSS_FEEDS_INDIAN_EXPRESS_MAIN),
            ("Indian Express", "India", cls.RSS_FEEDS_INDIAN_EXPRESS_INDIA),
            ("Indian Express", "World", cls.RSS_FEEDS_INDIAN_EXPRESS_WORLD),
            ("Indian Express", "Business", cls.RSS_FEEDS_INDIAN_EXPRESS_BUSINESS),
            ("Indian Express", "Economy", cls.RSS_FEEDS_INDIAN_EXPRESS_ECONOMICS),
            ("Indian Express", "Sports", cls.RSS_FEEDS_INDIAN_EXPRESS_SPORTS),
            ("Indian Express", "Entertainment", cls.RSS_FEEDS_INDIAN_EXPRESS_ENTERTAINMENT),
            ("Indian Express", "Lifestyle", cls.RSS_FEEDS_INDIAN_EXPRESS_LIFESTYLE),
            ("Indian Express", "Technology", cls.RSS_FEEDS_INDIAN_EXPRESS_TECHNOLOGY),
            ("Indian Express", "Explained", cls.RSS_FEEDS_INDIAN_EXPRESS_EXPLAINED),
        ]

        feeds = []
        for source, category, urls_value in feed_definitions:
            config = cls._build_feed_config(source, category, urls_value)
            if config:
                feeds.append(config)

        return feeds

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
