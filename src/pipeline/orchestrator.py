"""Pipeline orchestrator"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
from src.fetchers.rss_fetcher import RSSFetcher
from src.fetchers.html_scraper import HTMLScraper
from src.fetchers.pdf_parser import PDFParser
from src.generators.question_generator import QuestionGenerator
from src.utils.filters import is_relevant_content, classify_category, filter_by_source
from src.utils.content_cleaner import clean_text
import os

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Main pipeline coordinator for processing articles"""

    def __init__(self, question_generator: Optional[QuestionGenerator] = None):
        """
        Initialize pipeline orchestrator
        
        Args:
            question_generator: Question generator instance (creates new if None)
        """
        self.rss_fetcher = RSSFetcher()
        self.html_scraper = HTMLScraper()
        self.pdf_parser = PDFParser()
        self.question_generator = question_generator or QuestionGenerator()
        
        # Statistics
        self.stats = {
            'feeds_processed': 0,
            'articles_fetched': 0,
            'articles_processed': 0,
            'articles_failed': 0,
            'articles_skipped': 0,
            'questions_generated': 0,
            'errors': []
        }

    def process_rss_feeds(self, feed_configs: List[Dict]) -> List[Dict]:
        """
        Process RSS feeds and generate questions
        
        Args:
            feed_configs: List of feed configurations with 'urls', 'source', and optional 'category'
            
        Returns:
            List of generated question batches
        """
        all_question_batches = []
        
        for config in feed_configs:
            source = config.get('source', 'Unknown')
            feed_urls = config.get('urls', [])
            category = config.get('category', 'Business')
            
            if not filter_by_source(source):
                logger.warning(f"Skipping unsupported source: {source}")
                continue
            
            try:
                logger.info(f"Processing RSS feeds for {source}")
                self.stats['feeds_processed'] += 1
                
                # Fetch articles
                articles = self.rss_fetcher.get_today_articles(feed_urls, source)
                self.stats['articles_fetched'] += len(articles)
                
                # Process each article
                for article in articles:
                    try:
                        result = self.process_article(
                            url=article['url'],
                            title=article.get('title', ''),
                            source=source,
                            category=category
                        )
                        
                        if result:
                            all_question_batches.append(result)
                            self.stats['articles_processed'] += 1
                            self.stats['questions_generated'] += result.get('total_questions', 0)
                        else:
                            self.stats['articles_skipped'] += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing article {article.get('url', 'Unknown')}: {str(e)}")
                        self.stats['articles_failed'] += 1
                        self.stats['errors'].append(str(e))
                        
            except Exception as e:
                logger.error(f"Error processing RSS feeds for {source}: {str(e)}")
                self.stats['errors'].append(str(e))
        
        return all_question_batches

    def process_article(self, url: str, title: str = "", source: str = "", 
                       category: Optional[str] = None) -> Optional[Dict]:
        """
        Process a single article and generate questions
        
        Args:
            url: Article URL
            title: Article title
            source: Source name
            category: Article category (auto-detected if None)
            
        Returns:
            Question batch dictionary or None if skipped/failed
        """
        try:
            # Scrape article content
            logger.info(f"Scraping article: {url}")
            article_data = self.html_scraper.scrape_article(url, source)
            
            if not article_data:
                logger.warning(f"Failed to scrape article: {url}")
                return None
            
            content = article_data.get('content', '')
            if not content or len(content.strip()) < 100:
                logger.warning(f"Insufficient content for article: {url}")
                return None
            
            # Check relevance
            if not is_relevant_content(content):
                logger.info(f"Article not relevant for exam prep: {url}")
                return None
            
            # Classify category if not provided
            if not category:
                category = classify_category(content, title or article_data.get('title', ''))
            
            # Generate questions
            date = datetime.now().strftime('%Y-%m-%d')
            questions_data = self.question_generator.generate_questions(
                source=source,
                category=category,
                content=content,
                date=date
            )
            
            if not questions_data or questions_data.get("status") == "No relevant content":
                logger.info(f"No questions generated for article: {url}")
                return None
            
            return questions_data
            
        except Exception as e:
            logger.error(f"Error processing article {url}: {str(e)}")
            return None

    def process_pdf(self, pdf_path: str, source: str = "PDF", 
                   category: Optional[str] = None) -> Optional[Dict]:
        """
        Process PDF document and generate questions
        
        Args:
            pdf_path: Path to PDF file
            source: Source name
            category: Document category (auto-detected if None)
            
        Returns:
            Question batch dictionary or None if skipped/failed
        """
        try:
            logger.info(f"Processing PDF: {pdf_path}")
            
            # Parse PDF
            pdf_data = self.pdf_parser.parse_pdf(pdf_path, source)
            
            if not pdf_data:
                logger.warning(f"Failed to parse PDF: {pdf_path}")
                return None
            
            content = pdf_data.get('content', '')
            if not content or len(content.strip()) < 100:
                logger.warning(f"Insufficient content in PDF: {pdf_path}")
                return None
            
            # Check relevance
            if not is_relevant_content(content):
                logger.info(f"PDF content not relevant for exam prep: {pdf_path}")
                return None
            
            # Classify category if not provided
            if not category:
                category = classify_category(content, pdf_data.get('title', ''))
            
            # Generate questions
            date = datetime.now().strftime('%Y-%m-%d')
            questions_data = self.question_generator.generate_questions(
                source=source,
                category=category,
                content=content,
                date=date
            )
            
            if not questions_data or questions_data.get("status") == "No relevant content":
                logger.info(f"No questions generated for PDF: {pdf_path}")
                return None
            
            return questions_data
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            return None

    def get_stats(self) -> Dict:
        """Get pipeline statistics"""
        return self.stats.copy()

    def reset_stats(self):
        """Reset pipeline statistics"""
        self.stats = {
            'feeds_processed': 0,
            'articles_fetched': 0,
            'articles_processed': 0,
            'articles_failed': 0,
            'articles_skipped': 0,
            'questions_generated': 0,
            'errors': []
        }

