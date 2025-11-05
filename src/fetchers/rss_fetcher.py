"""RSS feed fetcher module"""

import feedparser
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import logging
import aiohttp

from src.fetchers.html_scraper import HTMLScraper

logger = logging.getLogger(__name__)


class RSSFetcher:
    """Fetches articles from RSS feeds"""

    def __init__(self, timeout: int = 30, retry_attempts: int = 3, retry_delay: int = 5):
        """
        Initialize RSS fetcher
        
        Args:
            timeout: Request timeout in seconds (converted to milliseconds for Playwright)
            retry_attempts: Number of retry attempts on failure (for RSS feed fetching)
            retry_delay: Delay between retries in seconds (for RSS feed fetching)
        """
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        # Convert timeout from seconds to milliseconds for Playwright
        # Playwright timeout is in milliseconds, default 30000ms (30 seconds)
        playwright_timeout = timeout * 1000 if timeout else 30000
        self.html_scraper = HTMLScraper(timeout=playwright_timeout, headless=True)

    async def close_sessions(self):
        """Close any open sessions."""
        await self.html_scraper.close_session()

    async def fetch_feed(self, session: aiohttp.ClientSession, feed_url: str) -> Optional[str]:
        """
        Fetch RSS feed content asynchronously.
        
        Args:
            session: The aiohttp client session.
            feed_url: URL of the RSS feed.
            
        Returns:
            Feed content as a string or None on failure.
        """
        for attempt in range(self.retry_attempts):
            try:
                logger.info(f"Fetching RSS feed: {feed_url} (attempt {attempt + 1})")
                async with session.get(feed_url, timeout=self.timeout) as response:
                    response.raise_for_status()
                    return await response.text()
            except aiohttp.ClientError as e:
                logger.error(f"Error fetching feed {feed_url} (attempt {attempt + 1}): {str(e)}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    return None
        return None

    async def extract_articles(self, feed_content: str, source: str, feed_url: str) -> List[Dict]:
        """
        Extract article information from parsed feed content.
        
        Args:
            feed_content: The RSS feed content as a string.
            source: Source name (e.g., "The Hindu", "Indian Express").
            feed_url: The URL of the feed for logging.
            
        Returns:
            List of article dictionaries with url, title, published_date, etc.
        """
        feed = feedparser.parse(feed_content)

        if feed.bozo:
            logger.warning(f"Feed parsing warning for {feed_url}: {feed.bozo_exception}")
        
        if not feed.entries:
            logger.warning(f"No entries found in feed: {feed_url}")
            return []

        tasks = []
        for entry in feed.entries:
            article_url = entry.get('link')
            if article_url:
                tasks.append(self._process_entry(entry, source))

        articles = await asyncio.gather(*tasks)
        return [article for article in articles if article]

    async def _process_entry(self, entry: Dict, source: str) -> Optional[Dict]:
        """Process a single feed entry to extract and scrape article content."""
        article_url = entry.get('link')
        try:
            scraped_data = await self.html_scraper.scrape_article(article_url, source)

            if scraped_data and scraped_data.get('content'):
                return {
                    'url': article_url,
                    'title': scraped_data.get('title') or entry.get('title', ''),
                    'published_date': self._parse_date(entry.get('published')),
                    'source': source,
                    'content': scraped_data['content']
                }
            else:
                logger.warning(f"Could not scrape content for: {article_url}")
                return None
        except Exception as e:
            logger.error(f"Error processing entry {article_url}: {str(e)}")
            return None

    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """
        Parse date string to YYYY-MM-DD format
        
        Args:
            date_str: Date string from RSS feed
            
        Returns:
            Date in YYYY-MM-DD format or None
        """
        if not date_str:
            return None
            
        try:
            # feedparser provides parsed date in entry.published_parsed
            # But we'll parse from string for consistency
            from dateutil import parser
            dt = parser.parse(date_str)
            return dt.strftime('%Y-%m-%d')
        except Exception as e:
            logger.warning(f"Error parsing date '{date_str}': {str(e)}")
            return None

    async def fetch_multiple_feeds(self, feed_urls: List[str], source: str) -> List[Dict]:
        """
        Fetch articles from multiple RSS feeds asynchronously.
        
        Args:
            feed_urls: List of RSS feed URLs.
            source: Source name for all feeds.
            
        Returns:
            Combined list of articles from all feeds.
        """
        async with aiohttp.ClientSession() as session:
            tasks = []
            for feed_url in feed_urls:
                tasks.append(self._fetch_and_extract(session, feed_url, source))

            results = await asyncio.gather(*tasks)
            all_articles = [article for articles in results for article in articles]

        logger.info(f"Total articles fetched from {source}: {len(all_articles)}")
        return all_articles

    async def _fetch_and_extract(self, session: aiohttp.ClientSession, feed_url: str, source: str) -> List[Dict]:
        """Fetch a single feed and extract articles."""
        feed_content = await self.fetch_feed(session, feed_url)
        if feed_content:
            return await self.extract_articles(feed_content, source, feed_url)
        return []

    async def get_today_articles(self, feed_urls: List[str], source: str) -> List[Dict]:
        """
        Fetch and filter articles from today asynchronously.
        
        Args:
            feed_urls: List of RSS feed URLs.
            source: Source name.
            
        Returns:
            List of articles published today.
        """
        all_articles = await self.fetch_multiple_feeds(feed_urls, source)
        today = datetime.now().strftime('%Y-%m-%d')
        
        today_articles = [
            article for article in all_articles
            if article and article.get('published_date') == today
        ]
        
        logger.info(f"Articles from today ({today}) for {source}: {len(today_articles)}")
        return today_articles

