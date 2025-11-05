"""HTML scraper module using Playwright and BeautifulSoup"""

from playwright.async_api import async_playwright, Browser, Page
from bs4 import BeautifulSoup
from typing import Optional, Dict
import logging
import asyncio

logger = logging.getLogger(__name__)


class HTMLScraper:
    """Scrapes article content from HTML pages using Playwright for dynamic content"""

    def __init__(self, timeout: int = 45000, headless: bool = True):
        """
        Initialize HTML scraper
        
        Args:
            timeout: Page load timeout in milliseconds (default 45 seconds)
            headless: Run browser in headless mode
        """
        self.timeout = timeout
        self.headless = headless
        self.browser: Optional[Browser] = None
        self._playwright = None

    async def _get_browser(self) -> Browser:
        """Get or create a Playwright browser instance"""
        if self.browser is None:
            self._playwright = await async_playwright().start()
            self.browser = await self._playwright.chromium.launch(headless=self.headless)
        return self.browser

    async def close_session(self):
        """Close the browser and playwright instance"""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch HTML page content using Playwright
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content as string or None on failure
        """
        try:
            browser = await self._get_browser()
            page = await browser.new_page()
            
            try:
                logger.info(f"Fetching HTML page: {url}")
                # Use 'domcontentloaded' instead of 'networkidle' for faster loading
                await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
                
                # Wait a bit for any lazy-loaded content
                await asyncio.sleep(1)
                
                # Get the rendered HTML
                html_content = await page.content()
                return html_content
            finally:
                await page.close()
                
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None

    async def scrape_article(self, url: str, source: str = None) -> Optional[Dict]:
        """
        Scrape article content from URL
        
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
        unwanted_selectors = [
            "[class*='ad']", "[id*='ad']",
            "[class*='social']", "[id*='social']",
            "[class*='comment']", "[id*='comment']",
            "[class*='sidebar']", "[id*='sidebar']",
            "[class*='recommend']", "[id*='recommend']",
            "[class*='related']", "[id*='related']",
            "[class*='newsletter']", "[id*='newsletter']",
            "[class*='subscribe']", "[id*='subscribe']"
        ]
        
        for selector in unwanted_selectors:
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
            # Try multiple title selectors
            title_elem = (soup.find('h1', class_='title') or 
                         soup.find('h1', itemprop='headline') or
                         soup.find('h1') or
                         soup.select_one('h1.title') or
                         soup.find('meta', property='og:title'))
            
            if title_elem:
                if title_elem.name == 'meta':
                    title = title_elem.get('content', '').strip() or "Untitled"
                else:
                    title = title_elem.get_text(strip=True) or "Untitled"
            else:
                title = "Untitled"
            
            # Try multiple body selectors
            article_body = (soup.find('div', class_='article-body') or 
                          soup.find('div', itemprop='articleBody') or
                          soup.find('div', class_='article-content') or
                          soup.find('article') or
                          soup.select_one('div[itemprop="articleBody"]'))
            
            if article_body:
                self._clean_article_body(article_body)
                
                # Get text content from paragraphs
                paragraphs = article_body.find_all('p')
                content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                
                if content and len(content.strip()) > 100:
                    return {
                        'url': url,
                        'title': title,
                        'content': content,
                        'source': 'The Hindu'
                    }
            
            logger.warning(f"Could not find article body for The Hindu article: {url}")
            return None
                
        except Exception as e:
            logger.error(f"Error scraping The Hindu article {url}: {str(e)}")
            return None

    def _scrape_indian_express(self, soup: BeautifulSoup, url: str) -> Optional[Dict]:
        """Scrape Indian Express article with improved selectors"""
        try:
            # Try multiple title selectors
            title_elem = (soup.find('h1', class_='entry-title') or 
                         soup.find('h1', itemprop='headline') or
                         soup.find('h1', class_='native_story_title') or
                         soup.find('h1') or
                         soup.select_one('h1.native_story_title') or
                         soup.select_one('h1.entry-title') or
                         soup.find('meta', property='og:title'))
            
            if title_elem:
                if title_elem.name == 'meta':
                    title = title_elem.get('content', '').strip() or "Untitled"
                else:
                    title = title_elem.get_text(strip=True) or "Untitled"
            else:
                title = "Untitled"
            
            # Try multiple body selectors - Indian Express uses various class names
            article_body = (soup.find('div', class_='native_story_content') or
                          soup.find('div', class_='entry-content') or
                          soup.find('div', itemprop='articleBody') or
                          soup.find('div', class_='article-content') or
                          soup.select_one('div.native_story_content') or
                          soup.select_one('div.entry-content') or
                          soup.find('article') or
                          soup.select_one('article .story_details'))
            
            # If still not found, try finding main content area
            if not article_body:
                # Look for common article containers
                article_body = (soup.find('div', class_='full-details') or
                              soup.find('div', id='article-body') or
                              soup.find('div', class_='story-body') or
                              soup.select_one('div[class*="story"]') or
                              soup.select_one('div[class*="article"]'))
            
            if article_body:
                self._clean_article_body(article_body)
                
                # Get text content from paragraphs
                paragraphs = article_body.find_all('p')
                content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                
                # If paragraphs don't give enough content, try getting all text
                if not content or len(content.strip()) < 100:
                    content = article_body.get_text(separator='\n\n', strip=True)
                
                if content and len(content.strip()) > 100:
                    return {
                        'url': url,
                        'title': title,
                        'content': content,
                        'source': 'Indian Express'
                    }
            
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
                    title = title_elem.get('content', '').strip() or "Untitled"
                else:
                    title = title_elem.get_text(strip=True) or "Untitled"
            else:
                title = "Untitled"
            
            article_body = (soup.find('article') or 
                          soup.find('div', class_='article') or
                          soup.find('div', class_='content') or
                          soup.find('main') or
                          soup.find('div', itemprop='articleBody'))
            
            if article_body:
                self._clean_article_body(article_body)
                
                paragraphs = article_body.find_all('p')
                content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                
                if content and len(content.strip()) > 100:
                    return {
                        'url': url,
                        'title': title,
                        'content': content,
                        'source': source
                    }
            
            logger.warning(f"Could not find article body for generic article: {url}")
            return None
                
        except Exception as e:
            logger.error(f"Error in generic scraping for {url}: {str(e)}")
            return None
