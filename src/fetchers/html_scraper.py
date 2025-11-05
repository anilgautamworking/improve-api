"""HTML scraper module using BeautifulSoup"""

import aiohttp
from bs4 import BeautifulSoup
from typing import Optional, Dict
import logging
import asyncio
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class HTMLScraper:
    """Scrapes article content from HTML pages"""

    def __init__(self, timeout: int = 30, retry_attempts: int = 3, retry_delay: int = 5):
        """
        Initialize HTML scraper
        
        Args:
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts on failure
            retry_delay: Delay between retries in seconds
        """
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp ClientSession"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)
        return self.session

    async def close_session(self):
        """Close the aiohttp ClientSession"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch HTML page content asynchronously
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content as string or None on failure
        """
        session = await self._get_session()
        for attempt in range(self.retry_attempts):
            try:
                logger.info(f"Fetching HTML page: {url} (attempt {attempt + 1})")
                async with session.get(url, timeout=self.timeout) as response:
                    response.raise_for_status()
                    return await response.text()
            except aiohttp.ClientError as e:
                logger.error(f"Error fetching {url} (attempt {attempt + 1}): {str(e)}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    return None
        return None

    async def scrape_article(self, url: str, source: str = None) -> Optional[Dict]:
        """
        Scrape article content from URL asynchronously
        
        Args:
            url: Article URL
            source: Source name (The Hindu, Indian Express, etc.)
            
        Returns:
            Dictionary with title, content, and metadata, or None on failure
        """
        html_content = await self.fetch_page(url)
        if not html_content:
            return None
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Determine source if not provided
            if not source:
                source = self._detect_source(url, soup)
            
            # Extract content based on source
            if source == "The Hindu":
                return self._scrape_the_hindu(soup, url)
            elif source == "Indian Express":
                return self._scrape_indian_express(soup, url)
            else:
                # Generic scraping as fallback
                return self._scrape_generic(soup, url, source)
                
        except Exception as e:
            logger.error(f"Error parsing HTML from {url}: {str(e)}")
            return None

    def _clean_article_body(self, article_body: BeautifulSoup):
        """Clean article body by removing common irrelevant elements."""
        if not article_body:
            return

        # Remove common unwanted tags
        for tag in article_body.find_all(['script', 'style', 'aside', 'nav', 'footer', 'header', 'form', 'iframe']):
            tag.decompose()

        # Remove elements by class or ID (ads, social buttons, etc.)
        for selector in [
            "[class*='ad']", "[id*='ad']",
            "[class*='social']", "[id*='social']",
            "[class*='comment']", "[id*='comment']",
            "[class*='sidebar']", "[id*='sidebar']",
            "[class*='recommend']", "[id*='recommend']",
            "[class*='related']", "[id*='related']"
        ]:
            for element in article_body.select(selector):
                element.decompose()

    def _detect_source(self, url: str, soup: BeautifulSoup) -> str:
        """Detect source from URL or page content"""
        if 'thehindu.com' in url.lower():
            return "The Hindu"
        elif 'indianexpress.com' in url.lower():
            return "Indian Express"
        else:
            return "Unknown"

    def _scrape_the_hindu(self, soup: BeautifulSoup, url: str) -> Optional[Dict]:
        """Scrape The Hindu article"""
        try:
            title_elem = soup.find('h1', class_='title') or soup.find('h1', itemprop='headline')
            title = title_elem.get_text(strip=True) if title_elem else "Untitled"
            
            article_body = soup.find('div', class_='article-body') or soup.find('div', itemprop='articleBody')
            if not article_body:
                article_body = soup.find('div', class_='article-content') or soup.find('article')
            
            if article_body:
                self._clean_article_body(article_body)
                
                # Get text content
                paragraphs = article_body.find_all('p')
                content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                
                return {
                    'url': url,
                    'title': title,
                    'content': content,
                    'source': 'The Hindu'
                }
            else:
                logger.warning(f"Could not find article body for The Hindu article: {url}")
                return None
                
        except Exception as e:
            logger.error(f"Error scraping The Hindu article {url}: {str(e)}")
            return None

    def _scrape_indian_express(self, soup: BeautifulSoup, url: str) -> Optional[Dict]:
        """Scrape Indian Express article"""
        try:
            title_elem = soup.find('h1', class_='entry-title') or soup.find('h1', itemprop='headline')
            title = title_elem.get_text(strip=True) if title_elem else "Untitled"
            
            article_body = soup.find('div', class_='entry-content') or soup.find('div', itemprop='articleBody')
            if not article_body:
                article_body = soup.find('div', class_='article-content') or soup.find('article')
            
            if article_body:
                self._clean_article_body(article_body)
                
                paragraphs = article_body.find_all('p')
                content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                
                return {
                    'url': url,
                    'title': title,
                    'content': content,
                    'source': 'Indian Express'
                }
            else:
                logger.warning(f"Could not find article body for Indian Express article: {url}")
                return None
                
        except Exception as e:
            logger.error(f"Error scraping Indian Express article {url}: {str(e)}")
            return None

    def _scrape_generic(self, soup: BeautifulSoup, url: str, source: str) -> Optional[Dict]:
        """Generic article scraping fallback"""
        try:
            title_elem = (soup.find('h1') or 
                         soup.find('title') or 
                         soup.find('meta', property='og:title'))
            
            if title_elem:
                if title_elem.name == 'meta':
                    title = title_elem.get('content', '') or "Untitled"
                else:
                    title = title_elem.get_text(strip=True) or "Untitled"
            else:
                title = "Untitled"
            
            article_body = (soup.find('article') or 
                          soup.find('div', class_='article') or
                          soup.find('div', class_='content') or
                          soup.find('main'))
            
            if article_body:
                self._clean_article_body(article_body)
                
                paragraphs = article_body.find_all('p')
                content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                
                return {
                    'url': url,
                    'title': title,
                    'content': content,
                    'source': source
                }
            else:
                logger.warning(f"Could not find article body for generic article: {url}")
                return None
                
        except Exception as e:
            logger.error(f"Error in generic scraping for {url}: {str(e)}")
            return None

