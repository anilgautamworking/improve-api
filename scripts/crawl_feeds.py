"""Standalone script for crawling RSS feeds and storing articles."""

import asyncio
import os
import sys
from datetime import datetime

# Add project root to PYTHONPATH
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils.logger import setup_logging
from src.config.settings import settings
from src.pipeline.crawler_orchestrator import CrawlerOrchestrator


async def run_crawl(logger=None) -> dict:
    """Execute Stage 1 crawling and return statistics."""
    logger = logger or setup_logging()
    settings.validate()

    with CrawlerOrchestrator() as crawler:
        feed_configs = settings.get_rss_feeds_config()
        await crawler.crawl_rss_feeds(feed_configs)
        stats = crawler.stats.copy()

    logger.info(
        "Crawling finished at %s. Feeds processed: %s, fetched: %s, stored: %s",
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        stats.get('feeds_processed', 0),
        stats.get('articles_fetched', 0),
        stats.get('articles_stored', 0),
    )
    return stats


async def main():
    """Script entrypoint."""
    logger = setup_logging()
    stats = await run_crawl(logger=logger)

    logger.info("=" * 60)
    logger.info("Stage 1 Summary (Crawler)")
    logger.info("Feeds processed: %s", stats.get('feeds_processed', 0))
    logger.info("Articles fetched: %s", stats.get('articles_fetched', 0))
    logger.info("Articles stored: %s", stats.get('articles_stored', 0))
    logger.info("Articles skipped: %s", stats.get('articles_skipped', 0))
    logger.info("Articles failed: %s", stats.get('articles_failed', 0))
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
