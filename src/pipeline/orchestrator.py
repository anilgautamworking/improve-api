"""Pipeline orchestrator"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
from src.database.repositories.article_repository import ArticleRepository
from src.database.db import get_db
from src.generators.question_generator import QuestionGenerator
from src.utils.filters import is_relevant_content, classify_category
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
        self.db_session = next(get_db())
        self.article_repo = ArticleRepository(self.db_session)
        self.question_generator = question_generator or QuestionGenerator()
        
        # Statistics
        self.stats = {
            'articles_processed': 0,
            'articles_failed': 0,
            'articles_skipped': 0,
            'questions_generated': 0,
            'errors': []
        }

    def process_articles_from_db(self) -> List[Dict]:
        """
        Process articles from the database and generate questions.
        """
        from src.config.settings import settings
        from src.database.repositories.question_repository import QuestionRepository
        
        all_question_batches = []
        category_question_counts = {}
        
        today = datetime.now().strftime('%Y-%m-%d')
        question_repo = QuestionRepository(self.db_session)
        
        articles = self.article_repo.get_articles_for_today()

        for article in articles:
            try:
                category = article.category or 'Business'
                
                if category not in category_question_counts:
                    category_question_counts[category] = 0
                    existing_questions = question_repo.get_questions_by_category(category, limit=100)
                    today_existing = [q for q in existing_questions if q.date == today]
                    category_question_counts[category] = sum(q.total_questions for q in today_existing)

                if category_question_counts[category] >= settings.QUESTIONS_PER_CATEGORY_PER_DAY:
                    continue
                
                result = self.process_article(
                    content=article.content,
                    url=article.url,
                    title=article.title,
                    source=article.source,
                    category=category
                )
                
                if result:
                    questions_count = result.get('total_questions', 0)
                    if category_question_counts[category] + questions_count > settings.QUESTIONS_PER_CATEGORY_PER_DAY:
                        remaining_slots = settings.QUESTIONS_PER_CATEGORY_PER_DAY - category_question_counts[category]
                        if remaining_slots > 0:
                            result['questions'] = result['questions'][:remaining_slots]
                            result['total_questions'] = remaining_slots
                            questions_count = remaining_slots
                    
                    all_question_batches.append(result)
                    category_question_counts[category] += questions_count
                    self.stats['articles_processed'] += 1
                    self.stats['questions_generated'] += questions_count
                else:
                    self.stats['articles_skipped'] += 1
            except Exception as e:
                logger.error(f"Error processing article {article.url}: {str(e)}")
                self.stats['articles_failed'] += 1
                self.stats['errors'].append(str(e))
        
        return all_question_batches

    def process_article(self, content: str, url: str, title: str = "", source: str = "",
                       category: Optional[str] = None) -> Optional[Dict]:
        """
        Process a single article and generate questions.
        
        Args:
            content: The article content.
            url: Article URL.
            title: Article title.
            source: Source name.
            category: Article category (auto-detected if None).
            
        Returns:
            Question batch dictionary or None if skipped/failed.
        """
        logger.debug(f"Processing article content (length: {len(content.strip())}): {content[:200]}...")
        if not content or len(content.strip()) < 100:
            logger.warning(f"Insufficient content for article: {url}")
            return None

        logger.debug("Content length is sufficient.")
        if not is_relevant_content(content):
            logger.info(f"Article not relevant for exam prep: {url}")
            return None

        if not category:
            category = classify_category(content, title)

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

