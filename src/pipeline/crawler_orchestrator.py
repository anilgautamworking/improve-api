"""Crawler orchestrator"""

import logging
from typing import List, Dict
from src.fetchers.rss_fetcher import RSSFetcher
from src.database.repositories.article_repository import ArticleRepository
from src.database.repositories.article_log_repository import ArticleLogRepository
from src.database.db import SessionLocal
from src.config.settings import settings
from src.orchestration.cancellation import honor_prefect_signals_async

logger = logging.getLogger(__name__)


class CrawlerOrchestrator:
    """Orchestrates the crawling and storing of articles."""

    def __init__(self, db_session=None):
        # Use configured max concurrent operations for CPU optimization
        self.rss_fetcher = RSSFetcher(max_concurrent=settings.MAX_CONCURRENT_BROWSER_OPERATIONS)
        self.db_session = db_session or SessionLocal()
        self._owns_session = db_session is None
        self.article_repo = ArticleRepository(self.db_session)
        self.article_log_repo = ArticleLogRepository(self.db_session)
        self.stats = {
            'feeds_processed': 0,
            'articles_fetched': 0,
            'articles_stored': 0,
            'articles_skipped': 0,
            'articles_failed': 0,
            'errors': []
        }
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session if we own it"""
        if self._owns_session:
            self.db_session.close()
        return False

    async def crawl_rss_feeds(self, feed_configs: List[Dict]):
        """Crawl RSS feeds and store the articles."""
        for config in feed_configs:
            await honor_prefect_signals_async("Crawler stage")
            source = config.get('source', 'Unknown')
            category = config.get('category', None)  # Get category from feed config
            feed_urls = config.get('urls', [])

            try:
                logger.info(f"Crawling RSS feeds for {source}" + (f" - {category}" if category else ""))
                self.stats['feeds_processed'] += 1

                articles_data = await self.rss_fetcher.get_today_articles(feed_urls, source)
                self.stats['articles_fetched'] += len(articles_data)

                for article_data in articles_data:
                    await honor_prefect_signals_async("Crawler stage")
                    try:
                        if self.article_repo.get_by_url(article_data['url']):
                            self.stats['articles_skipped'] += 1
                            continue

                        # Assign category from feed config if not already set
                        if category and not article_data.get('category'):
                            article_data['category'] = category

                        self.article_repo.create(article_data)
                        self.article_log_repo.ensure_log(
                            url=article_data['url'],
                            title=article_data.get('title'),
                            source=article_data.get('source', source),
                            category=article_data.get('category', category),
                        )
                        self.db_session.commit()
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
