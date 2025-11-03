"""RSS feed fetcher module"""

import feedparser
import requests
from typing import List, Dict, Optional
from datetime import datetime
import time
import logging

logger = logging.getLogger(__name__)


class RSSFetcher:
    """Fetches articles from RSS feeds"""

    def __init__(self, timeout: int = 30, retry_attempts: int = 3, retry_delay: int = 5):
        """
        Initialize RSS fetcher
        
        Args:
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts on failure
            retry_delay: Delay between retries in seconds
        """
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

    def fetch_feed(self, feed_url: str) -> Optional[feedparser.FeedParserDict]:
        """
        Fetch and parse RSS feed
        
        Args:
            feed_url: URL of the RSS feed
            
        Returns:
            Parsed feed object or None on failure
        """
        for attempt in range(self.retry_attempts):
            try:
                logger.info(f"Fetching RSS feed: {feed_url} (attempt {attempt + 1})")
                feed = feedparser.parse(feed_url)
                
                if feed.bozo and feed.bozo_exception:
                    logger.warning(f"Feed parsing warning: {feed.bozo_exception}")
                
                if feed.entries:
                    logger.info(f"Successfully fetched {len(feed.entries)} entries from {feed_url}")
                    return feed
                else:
                    logger.warning(f"No entries found in feed: {feed_url}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error fetching feed {feed_url} (attempt {attempt + 1}): {str(e)}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
                else:
                    return None
        
        return None

    def extract_articles(self, feed: feedparser.FeedParserDict, source: str) -> List[Dict]:
        """
        Extract article information from parsed feed
        
        Args:
            feed: Parsed feed object
            source: Source name (e.g., "The Hindu", "Indian Express")
            
        Returns:
            List of article dictionaries with url, title, published_date, etc.
        """
        articles = []
        
        for entry in feed.entries:
            try:
                article = {
                    'url': entry.get('link', ''),
                    'title': entry.get('title', ''),
                    'published_date': self._parse_date(entry.get('published', '')),
                    'source': source,
                    'description': entry.get('description', ''),
                    'summary': entry.get('summary', '')
                }
                
                if article['url']:
                    articles.append(article)
                else:
                    logger.warning(f"Skipping article with no URL: {entry.get('title', 'Unknown')}")
                    
            except Exception as e:
                logger.error(f"Error extracting article from feed: {str(e)}")
                continue
        
        return articles

    def _parse_date(self, date_str: str) -> Optional[str]:
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

    def fetch_multiple_feeds(self, feed_urls: List[str], source: str) -> List[Dict]:
        """
        Fetch articles from multiple RSS feeds
        
        Args:
            feed_urls: List of RSS feed URLs
            source: Source name for all feeds
            
        Returns:
            Combined list of articles from all feeds
        """
        all_articles = []
        
        for feed_url in feed_urls:
            feed = self.fetch_feed(feed_url)
            if feed:
                articles = self.extract_articles(feed, source)
                all_articles.extend(articles)
                # Small delay between feeds to avoid rate limiting
                time.sleep(1)
        
        logger.info(f"Total articles fetched from {source}: {len(all_articles)}")
        return all_articles

    def get_today_articles(self, feed_urls: List[str], source: str) -> List[Dict]:
        """
        Fetch and filter articles from today
        
        Args:
            feed_urls: List of RSS feed URLs
            source: Source name
            
        Returns:
            List of articles published today
        """
        all_articles = self.fetch_multiple_feeds(feed_urls, source)
        today = datetime.now().strftime('%Y-%m-%d')
        
        today_articles = [
            article for article in all_articles
            if article.get('published_date') == today
        ]
        
        logger.info(f"Articles from today ({today}) for {source}: {len(today_articles)}")
        return today_articles

