"""Crawler orchestrator"""

import logging
from typing import List, Dict
from src.fetchers.rss_fetcher import RSSFetcher
from src.database.repositories.article_repository import ArticleRepository
from src.database.db import get_db
from src.config.settings import settings

logger = logging.getLogger(__name__)


class CrawlerOrchestrator:
    """Orchestrates the crawling and storing of articles."""

    def __init__(self):
        # Use configured max concurrent operations for CPU optimization
        self.rss_fetcher = RSSFetcher(max_concurrent=settings.MAX_CONCURRENT_BROWSER_OPERATIONS)
        self.db_session = next(get_db())
        self.article_repo = ArticleRepository(self.db_session)
        self.stats = {
            'feeds_processed': 0,
            'articles_fetched': 0,
            'articles_stored': 0,
            'articles_skipped': 0,
            'articles_failed': 0,
            'errors': []
        }

    async def crawl_rss_feeds(self, feed_configs: List[Dict]):
        """Crawl RSS feeds and store the articles."""
        for config in feed_configs:
            source = config.get('source', 'Unknown')
            feed_urls = config.get('urls', [])

            try:
                logger.info(f"Crawling RSS feeds for {source}")
                self.stats['feeds_processed'] += 1

                articles_data = await self.rss_fetcher.get_today_articles(feed_urls, source)
                self.stats['articles_fetched'] += len(articles_data)

                for article_data in articles_data:
                    try:
                        if self.article_repo.get_by_url(article_data['url']):
                            self.stats['articles_skipped'] += 1
                            continue

                        self.article_repo.create(article_data)
                        self.stats['articles_stored'] += 1
                    except Exception as e:
                        logger.error(f"Error storing article {article_data.get('url', 'Unknown')}: {str(e)}")
                        self.stats['articles_failed'] += 1
                        self.stats['errors'].append(str(e))

            except Exception as e:
                logger.error(f"Error crawling RSS feeds for {source}: {str(e)}")
                self.stats['errors'].append(str(e))

        await self.rss_fetcher.close_sessions()
        logger.info(f"Crawling complete. Stored {self.stats['articles_stored']} new articles.")
