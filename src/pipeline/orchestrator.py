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
from src.utils.article_scorer import ArticleScorer
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
        Process RSS feeds and generate questions with daily limits per category
        
        Args:
            feed_configs: List of feed configurations with 'urls', 'source', and optional 'category'
            
        Returns:
            List of curated question batches (limited per category)
        """
        from src.config.settings import settings
        from src.database.repositories.question_repository import QuestionRepository
        from datetime import datetime
        
        all_question_batches = []
        category_question_counts = {}  # Track questions per category
        category_articles_processed = {}  # Track articles processed per category
        
        # Get today's date
        today = datetime.now().strftime('%Y-%m-%d')
        question_repo = QuestionRepository()
        
        for config in feed_configs:
            source = config.get('source', 'Unknown')
            feed_urls = config.get('urls', [])
            category = config.get('category', 'Business')
            
            if not filter_by_source(source):
                logger.warning(f"Skipping unsupported source: {source}")
                continue
            
            # Initialize category tracking
            if category not in category_question_counts:
                category_question_counts[category] = 0
                category_articles_processed[category] = 0
                
                # Check existing questions for this category today
                existing_questions = question_repo.get_questions_by_category(category, limit=100)
                today_existing = [q for q in existing_questions if q.date == today]
                category_question_counts[category] = sum(q.total_questions for q in today_existing)
                logger.info(f"Category '{category}' already has {category_question_counts[category]} questions today")
            
            # Check if we've reached the daily limit for this category
            if category_question_counts[category] >= settings.QUESTIONS_PER_CATEGORY_PER_DAY:
                logger.info(f"Category '{category}' has reached daily limit ({settings.QUESTIONS_PER_CATEGORY_PER_DAY} questions). Skipping.")
                continue
            
            try:
                logger.info(f"Processing RSS feeds for {source} - Category: {category}")
                self.stats['feeds_processed'] += 1
                
                # Fetch ALL articles from today
                articles = self.rss_fetcher.get_today_articles(feed_urls, source)
                self.stats['articles_fetched'] += len(articles)
                
                logger.info(f"Evaluating {len(articles)} articles for category '{category}'...")
                
                # Score and rank ALL articles to find the best ones
                ranked_articles = ArticleScorer.rank_articles(
                    articles, 
                    target_category=category,
                    top_n=settings.MAX_ARTICLES_PER_CATEGORY
                )
                
                articles_to_process = ranked_articles
                score_list = [f"{a['score']:.1f}" for a in articles_to_process]
                logger.info(f"Selected top {len(articles_to_process)} articles for category '{category}' "
                           f"(scores: {score_list})")
                
                # Process articles until we reach daily limit
                for article in articles_to_process:
                    # Check if we've reached daily limit
                    if category_question_counts[category] >= settings.QUESTIONS_PER_CATEGORY_PER_DAY:
                        logger.info(f"Reached daily limit for category '{category}'. Stopping article processing.")
                        break
                    
                    # Check article limit
                    if category_articles_processed[category] >= settings.MAX_ARTICLES_PER_CATEGORY:
                        logger.info(f"Reached article limit for category '{category}'. Stopping.")
                        break
                    
                    try:
                        # Remove score from article dict before processing
                        article_for_processing = {k: v for k, v in article.items() if k != 'score'}
                        
                        result = self.process_article(
                            url=article_for_processing['url'],
                            title=article_for_processing.get('title', ''),
                            source=source,
                            category=category
                        )
                        
                        if result:
                            questions_count = result.get('total_questions', 0)
                            
                            # Check if adding these questions would exceed limit
                            if category_question_counts[category] + questions_count > settings.QUESTIONS_PER_CATEGORY_PER_DAY:
                                # Trim questions to fit limit
                                remaining_slots = settings.QUESTIONS_PER_CATEGORY_PER_DAY - category_question_counts[category]
                                if remaining_slots > 0:
                                    result['questions'] = result['questions'][:remaining_slots]
                                    result['total_questions'] = remaining_slots
                                    questions_count = remaining_slots
                                    logger.info(f"Trimmed questions to fit daily limit for '{category}'")
                                else:
                                    logger.info(f"Daily limit reached for '{category}'. Skipping remaining questions.")
                                    break
                            
                            all_question_batches.append(result)
                            category_question_counts[category] += questions_count
                            category_articles_processed[category] += 1
                            self.stats['articles_processed'] += 1
                            self.stats['questions_generated'] += questions_count
                            
                            logger.info(f"Category '{category}': {category_question_counts[category]}/{settings.QUESTIONS_PER_CATEGORY_PER_DAY} questions")
                        else:
                            self.stats['articles_skipped'] += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing article {article.get('url', 'Unknown')}: {str(e)}")
                        self.stats['articles_failed'] += 1
                        self.stats['errors'].append(str(e))
                        
            except Exception as e:
                logger.error(f"Error processing RSS feeds for {source}: {str(e)}")
                self.stats['errors'].append(str(e))
        
        # Log summary per category
        logger.info("=" * 80)
        logger.info("Questions Generated by Category:")
        for category, count in category_question_counts.items():
            logger.info(f"  {category}: {count} questions")
        logger.info("=" * 80)
        
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

