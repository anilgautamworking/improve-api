"""HTML scraper module using BeautifulSoup"""

import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict
import logging
import time
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

    def fetch_page(self, url: str) -> Optional[requests.Response]:
        """
        Fetch HTML page content
        
        Args:
            url: URL to fetch
            
        Returns:
            Response object or None on failure
        """
        for attempt in range(self.retry_attempts):
            try:
                logger.info(f"Fetching HTML page: {url} (attempt {attempt + 1})")
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching {url} (attempt {attempt + 1}): {str(e)}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
                else:
                    return None
        
        return None

    def scrape_article(self, url: str, source: str = None) -> Optional[Dict]:
        """
        Scrape article content from URL
        
        Args:
            url: Article URL
            source: Source name (The Hindu, Indian Express, etc.)
            
        Returns:
            Dictionary with title, content, and metadata, or None on failure
        """
        response = self.fetch_page(url)
        if not response:
            return None
        
        try:
            soup = BeautifulSoup(response.content, 'lxml')
            
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
            # The Hindu article structure
            title_elem = soup.find('h1', class_='title') or soup.find('h1', itemprop='headline')
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # Find article body
            article_body = soup.find('div', class_='article-body') or soup.find('div', itemprop='articleBody')
            
            if not article_body:
                # Try alternative selectors
                article_body = soup.find('div', class_='article-content') or soup.find('article')
            
            if article_body:
                # Remove script and style elements
                for script in article_body(["script", "style", "aside", "nav", "footer", "header"]):
                    script.decompose()
                
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
            # Indian Express article structure
            title_elem = soup.find('h1', class_='entry-title') or soup.find('h1', itemprop='headline')
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # Find article body
            article_body = soup.find('div', class_='entry-content') or soup.find('div', itemprop='articleBody')
            
            if not article_body:
                article_body = soup.find('div', class_='article-content') or soup.find('article')
            
            if article_body:
                # Remove unwanted elements
                for script in article_body(["script", "style", "aside", "nav", "footer", "header", "div"]):
                    # Only remove divs with specific classes (ads, etc.)
                    if script.get('class') and any('ad' in str(c).lower() for c in script.get('class', [])):
                        script.decompose()
                
                # Get text content
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
            # Try common article selectors
            title_elem = (soup.find('h1') or 
                         soup.find('title') or 
                         soup.find('meta', property='og:title'))
            
            if title_elem:
                if title_elem.name == 'meta':
                    title = title_elem.get('content', '')
                else:
                    title = title_elem.get_text(strip=True)
            else:
                title = ""
            
            # Try to find main content
            article_body = (soup.find('article') or 
                          soup.find('div', class_='article') or
                          soup.find('div', class_='content') or
                          soup.find('main'))
            
            if article_body:
                # Remove unwanted elements
                for script in article_body(["script", "style", "aside", "nav", "footer", "header"]):
                    script.decompose()
                
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

