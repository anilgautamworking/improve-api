"""Pipeline orchestrator"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
from src.database.repositories.article_repository import ArticleRepository
from src.database.repositories.question_repository import QuestionRepository
from src.database.repositories.article_log_repository import ArticleLogRepository
from src.database.db import SessionLocal
from src.generators.question_generator import QuestionGenerator
from src.utils.filters import is_relevant_content, classify_category
from src.utils.article_scorer import ArticleScorer
from src.fetchers.pdf_parser import PDFParser
from src.config.settings import settings
import os

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Main pipeline coordinator for processing articles"""

    def __init__(self, question_generator: Optional[QuestionGenerator] = None, db_session=None):
        """
        Initialize pipeline orchestrator
        
        Args:
            question_generator: Question generator instance (creates new if None)
            db_session: Database session (creates new if None)
        """
        self.db_session = db_session or SessionLocal()
        self._owns_session = db_session is None
        self.article_repo = ArticleRepository(self.db_session)
        self.article_log_repo = ArticleLogRepository(self.db_session)
        self.question_generator = question_generator or QuestionGenerator()
        self.pdf_parser = PDFParser()
        
        # Statistics
        self.stats = {
            'articles_processed': 0,
            'articles_failed': 0,
            'articles_skipped': 0,
            'questions_generated': 0,
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

    def process_articles_from_db(self) -> List[Dict]:
        """
        Process articles from the database and generate questions.
        """
        all_question_batches: List[Dict] = []
        category_question_counts: Dict[str, int] = {}
        category_article_counts: Dict[str, int] = {}
        
        today = datetime.now().strftime('%Y-%m-%d')
        question_repo = QuestionRepository(self.db_session)
        
        pending_urls = self.article_log_repo.get_pending_urls()
        if not pending_urls:
            logger.info("No pending articles to process.")
            return all_question_batches

        articles = self.article_repo.get_articles_by_urls(pending_urls)
        if not articles:
            logger.info("Pending article URLs not found in database.")
            return all_question_batches

        article_map = {article.url: article for article in articles}
        ordered_articles = [article_map[url] for url in pending_urls if url in article_map]
        if not ordered_articles:
            logger.info("No matching articles for pending URLs.")
            return all_question_batches

        scored_articles = []
        for article in ordered_articles:
            combined_text = (article.title or "") + " " + (article.content or "")
            article_payload = {
                'title': article.title or '',
                'description': combined_text[:500],
                'summary': combined_text[:500]
            }
            score = ArticleScorer.score_article(article_payload, article.category)
            scored_articles.append((score, article))

        scored_articles.sort(key=lambda item: item[0], reverse=True)

        max_articles = settings.MAX_ARTICLES_PER_RUN or len(scored_articles)
        articles_attempted = 0

        for score, article in scored_articles:
            if articles_attempted >= max_articles:
                break

            try:
                # Use stored category, or classify if missing
                category = article.category
                if not category:
                    category = classify_category(article.content or "", article.title or "")
                    article.category = category
                    self.db_session.commit()
                    logger.debug("Classified article %s as %s", article.url[:80], category)

                if settings.is_pdf_only_category(category) and not settings.is_pdf_source(article.source):
                    logger.debug(
                        "Skipping %s because category '%s' is PDF-only but source is '%s'",
                        article.url,
                        category,
                        article.source or "Unknown"
                    )
                    self.stats['articles_skipped'] += 1
                    continue

                if not settings.is_category_enabled(category):
                    logger.debug("Skipping article in disabled category: %s", category)
                    self.stats['articles_skipped'] += 1
                    continue

                # Respect per-category article limits
                max_articles_per_category = settings.MAX_ARTICLES_PER_CATEGORY
                category_article_counts.setdefault(category, 0)
                if max_articles_per_category and max_articles_per_category > 0:
                    if category_article_counts[category] >= max_articles_per_category:
                        logger.debug("Skipping %s - per-category article limit reached", category)
                        self.stats['articles_skipped'] += 1
                        continue

                if category not in category_question_counts:
                    existing_questions = question_repo.get_questions_by_category(category, limit=100)
                    today_existing = [q for q in existing_questions if q.date == today]
                    category_question_counts[category] = sum(q.total_questions for q in today_existing)
                if category_question_counts[category] >= settings.QUESTIONS_PER_CATEGORY_PER_DAY:
                    logger.debug("Skipping %s - daily question cap reached", category)
                    self.stats['articles_skipped'] += 1
                    continue

                category_article_counts[category] += 1
                articles_attempted += 1

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
                        else:
                            questions_count = 0
                    
                    if questions_count == 0:
                        logger.debug("No remaining question slots for %s", category)
                        continue

                    all_question_batches.append(result)
                    category_question_counts[category] += questions_count
                    self.stats['articles_processed'] += 1
                    self.stats['questions_generated'] += questions_count
                    self.article_log_repo.mark_processed(article.url, questions_count)
                    self.db_session.commit()
                else:
                    self.stats['articles_skipped'] += 1
                    self.article_log_repo.mark_skipped(article.url)
                    self.db_session.commit()
            except Exception as e:
                logger.error(f"Error processing article {article.url}: {str(e)}")
                self.stats['articles_failed'] += 1
                self.stats['errors'].append(str(e))
                self.article_log_repo.mark_failed(article.url, str(e))
                self.db_session.commit()
        
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

        filtered_questions = questions_data.get("questions", [])
        questions_data["questions"] = filtered_questions
        questions_data["total_questions"] = len(filtered_questions)

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

            filtered_questions = questions_data.get("questions", [])
            questions_data["questions"] = filtered_questions
            questions_data["total_questions"] = len(filtered_questions)
            
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
