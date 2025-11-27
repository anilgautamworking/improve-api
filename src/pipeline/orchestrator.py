"""Pipeline orchestrator"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy import text
from src.database.repositories.article_repository import ArticleRepository
from src.database.repositories.question_repository import QuestionRepository
from src.database.repositories.frontend_question_repository import FrontendQuestionRepository
from src.database.repositories.pdf_source_repository import PdfSourceRepository
from src.database.repositories.pdf_chunk_repository import PdfChunkRepository
from src.database.repositories.article_log_repository import ArticleLogRepository
from src.database.db import SessionLocal
from src.generators.question_generator import QuestionGenerator
from src.utils.filters import is_relevant_content, classify_category, classify_category_strict
from src.utils.article_scorer import ArticleScorer
from src.fetchers.pdf_parser import PDFParser
from src.pipeline.pdf.chunker import PdfChunker
from src.pipeline.pdf.text_utils import truncate_at_sentence
from src.config.settings import settings
from src.orchestration.cancellation import honor_prefect_signals
from src.utils.transaction_manager import savepoint, safe_commit
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
        self.question_repo = QuestionRepository(self.db_session)
        self.frontend_question_repo = FrontendQuestionRepository(self.db_session)
        self.pdf_source_repo = PdfSourceRepository(self.db_session)
        self.pdf_chunk_repo = PdfChunkRepository(self.db_session)
        self.pdf_parser = PDFParser()
        self.pdf_chunker = PdfChunker(
            chunk_size_pages=settings.PDF_CHUNK_SIZE_PAGES,
            overlap_pages=settings.PDF_CHUNK_OVERLAP_PAGES,
            max_content_chars=settings.PDF_MAX_CONTENT_CHARS,
        )
        
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
        logger.info("Starting article processing from database...")
        all_question_batches: List[Dict] = []
        category_question_counts: Dict[str, int] = {}
        category_article_counts: Dict[str, int] = {}

        today = datetime.now().strftime("%Y-%m-%d")
        question_repo = QuestionRepository(self.db_session)
        logger.info("Getting pending URLs...")

        pending_urls = self.article_log_repo.get_pending_urls()
        logger.info(f"Found {len(pending_urls)} pending URLs")
        if not pending_urls:
            logger.info("No pending articles to process.")
            return all_question_batches

        # Load articles with eager loading to avoid transaction abortion issues
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
            try:
                # Ensure all article attributes are loaded before any potential transaction issues
                combined_text = (article.title or "") + " " + (article.content or "")
                article_payload = {
                    "title": article.title or "",
                    "description": combined_text[:500],
                    "summary": combined_text[:500],
                }
                # Load category attribute eagerly to avoid lazy loading during processing
                category = getattr(article, "category", None)
                score = ArticleScorer.score_article(article_payload, category)
                scored_articles.append((score, article))
            except Exception as e:
                logger.warning(f"Failed to score article {article.url}: {str(e)}")
                # Skip articles that can't be scored due to transaction issues
                continue

        scored_articles.sort(key=lambda item: item[0], reverse=True)

        max_articles = settings.MAX_ARTICLES_PER_RUN or len(scored_articles)
        articles_attempted = 0

        for score, article in scored_articles:
            honor_prefect_signals("Question generation pipeline")
            if articles_attempted >= max_articles:
                break

            try:
                # Use stored category, or classify if missing
                # Use getattr to safely access category and avoid lazy loading issues
                category = getattr(article, "category", None)
                if not category:
                    try:
                        category = classify_category(
                            article.content or "", article.title or ""
                        )
                        article.category = category
                        safe_commit(self.db_session)
                        logger.debug(
                            "Classified article %s as %s", article.url[:80], category
                        )
                    except Exception as classify_error:
                        logger.warning(
                            f"Failed to classify article {article.url}: {str(classify_error)}"
                        )
                        # Skip articles that can't be classified due to transaction issues
                        self.stats["articles_failed"] += 1
                        continue

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

                honor_prefect_signals("Question generation pipeline")

                # Transaction state will be checked implicitly through savepoint usage
                # If transaction is aborted, the savepoint will fail gracefully

                # Use savepoint for each article to allow partial rollback
                try:
                    with savepoint(self.db_session, f"article_{articles_attempted}"):
                        result = self.process_article(
                            content=article.content,
                            url=article.url,
                            title=article.title,
                            source=article.source,
                            category=category,
                        )
                except Exception as savepoint_error:
                    # If savepoint fails (likely due to transaction abortion), log and continue
                    logger.warning(
                        f"Savepoint failed for article {article.url}: {str(savepoint_error)}"
                    )
                    self.stats["articles_failed"] += 1
                    # Don't try to rollback here - savepoint should handle it
                    continue

                if result:
                    questions_count = result.get("total_questions", 0)
                    if (
                        category_question_counts[category] + questions_count
                        > settings.QUESTIONS_PER_CATEGORY_PER_DAY
                    ):
                        remaining_slots = (
                            settings.QUESTIONS_PER_CATEGORY_PER_DAY
                            - category_question_counts[category]
                        )
                        if remaining_slots > 0:
                            result["questions"] = result["questions"][:remaining_slots]
                            result["total_questions"] = remaining_slots
                            questions_count = remaining_slots
                        else:
                            questions_count = 0

                    if questions_count == 0:
                        logger.debug("No remaining question slots for %s", category)
                        continue

                    all_question_batches.append(result)
                    category_question_counts[category] += questions_count
                    self.stats["articles_processed"] += 1
                    self.stats["questions_generated"] += questions_count
                    self.article_log_repo.mark_processed(article.url, questions_count)
                    safe_commit(self.db_session)
                else:
                    self.stats["articles_skipped"] += 1
                    self.article_log_repo.mark_skipped(article.url)
                    safe_commit(self.db_session)
            except Exception as e:
                logger.error(f"Error processing article {article.url}: {str(e)}")
                self.stats['articles_failed'] += 1
                self.stats['errors'].append(str(e))
                # Savepoint will rollback automatically, but we still want to mark as failed
                try:
                    self.article_log_repo.mark_failed(article.url, str(e))
                    safe_commit(self.db_session)
                except Exception as commit_error:
                    logger.error(f"Failed to mark article as failed: {str(commit_error)}")
        
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
        honor_prefect_signals("Question generation article")
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
        honor_prefect_signals("Question generation article")
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
                   category: Optional[str] = None, pdf_source_id: Optional[int] = None) -> Optional[Dict]:
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
            honor_prefect_signals("PDF question generation")
            logger.info(f"Processing PDF: {pdf_path}")

            pages = self.pdf_parser.extract_pages(pdf_path)
            if not pages:
                logger.warning(f"Failed to extract pages from PDF: {pdf_path}")
                if pdf_source_id:
                    self.pdf_source_repo.update_status(pdf_source_id, "failed", error_reason="extract_pages_failed")
                return None

            full_text = "\n\n".join([p.text for p in pages if p.text])
            if not full_text or len(full_text.strip()) < 100:
                logger.warning(f"Insufficient content in PDF: {pdf_path}")
                if pdf_source_id:
                    self.pdf_source_repo.update_status(pdf_source_id, "failed", error_reason="no_content")
                return None

            if not is_relevant_content(full_text):
                message = f"PDF content not relevant for exam prep: {pdf_path}"
                logger.info(message)
                if pdf_source_id:
                    self.pdf_source_repo.update_status(pdf_source_id, "failed", error_reason="not_relevant")
                # Fail fast so we never silently store questions for irrelevant PDFs
                raise ValueError(message)

            if not category:
                category = classify_category_strict(full_text, os.path.basename(pdf_path))
                if not category:
                    message = f"Unable to classify PDF category for {pdf_path}; aborting to avoid mislabeling"
                    if pdf_source_id:
                        self.pdf_source_repo.update_status(pdf_source_id, "failed", error_reason="unclassified")
                    raise ValueError(message)

            chunks = self.pdf_chunker.chunk(pages)
            if not chunks:
                logger.warning(f"No chunks produced for PDF: {pdf_path}")
                if pdf_source_id:
                    self.pdf_source_repo.update_status(pdf_source_id, "failed", error_reason="no_chunks")
                return None

            # Persist chunk records
            persisted_chunks = []
            for chunk in chunks:
                try:
                    rec = self.pdf_chunk_repo.upsert_chunk(
                        pdf_source_id=pdf_source_id or -1,
                        chunk_index=chunk.index,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                        chapter_title=None,
                        heading=chunk.heading,
                        content=chunk.content,
                        token_count=chunk.token_estimate,
                        status="processing",
                    )
                    persisted_chunks.append(rec)
                except Exception as exc:
                    logger.warning(
                        "Failed to upsert chunk %s for %s (pdf_source_id=%s): %s",
                        chunk.index,
                        pdf_path,
                        pdf_source_id,
                        exc,
                    )

            target_max = (
                settings.PDF_TARGET_QUESTIONS_PER_CHUNK
                if settings.PDF_TARGET_QUESTIONS_PER_CHUNK > 0
                else None
            )
            date = datetime.now().strftime('%Y-%m-%d')
            all_questions: List[Dict] = []

            chunk_meta = []
            for chunk in chunks:
                honor_prefect_signals("PDF chunk generation")
                if not chunk.content or len(chunk.content.strip()) < 100:
                    logger.debug(
                        "Skipping chunk %s (%s-%s) due to low content",
                        chunk.index,
                        chunk.page_start,
                        chunk.page_end,
                    )
                    continue

                q_data = self.question_generator.generate_questions(
                    source=source,
                    category=category,
                    content=chunk.content,
                    date=date,
                    target_min_questions=0,
                    target_max_questions=target_max,
                    max_content_length_override=settings.PDF_MAX_CONTENT_CHARS,
                    prompt_profile="pdf",
                    chunk_heading=chunk.heading,
                    page_range=f"{chunk.page_start}-{chunk.page_end}",
                )

                questions = q_data.get("questions", []) if q_data else []

                # Retry once if we got zero questions
                if not questions:
                    fallback_content = truncate_at_sentence(
                        chunk.content,
                        max(5000, settings.PDF_MAX_CONTENT_CHARS // 2),
                        settings.PDF_MAX_CONTENT_CHARS,
                    )
                    q_data = self.question_generator.generate_questions(
                        source=source,
                        category=category,
                        content=fallback_content,
                        date=date,
                        target_min_questions=0,
                        target_max_questions=1 if target_max else None,
                        max_content_length_override=settings.PDF_MAX_CONTENT_CHARS,
                        prompt_profile="pdf",
                        chunk_heading=chunk.heading,
                        page_range=f"{chunk.page_start}-{chunk.page_end}",
                    )
                    questions = q_data.get("questions", []) if q_data else []

                if not questions:
                    logger.info(
                        "No questions for chunk %s (%s-%s) in %s (pdf_source_id=%s)",
                        chunk.index,
                        chunk.page_start,
                        chunk.page_end,
                        pdf_path,
                        pdf_source_id,
                    )
                    if pdf_source_id:
                        rec = self.pdf_chunk_repo.get_by_source_and_index(pdf_source_id, chunk.index)
                        if rec:
                            self.pdf_chunk_repo.update_status(rec.id, "failed", error_reason="no_questions")
                    continue

                if pdf_source_id:
                    rec = self.pdf_chunk_repo.get_by_source_and_index(pdf_source_id, chunk.index)
                    if rec:
                        self.pdf_chunk_repo.update_status(rec.id, "done", error_reason=None)

                chunk_meta.append({
                    "chunk_index": chunk.index,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                    "heading": chunk.heading,
                    "question_count": len(questions),
                })
                all_questions.extend(questions)

            if not all_questions:
                logger.info(f"No questions generated for PDF: {pdf_path}")
                return None

            result = {
                "source": source,
                "category": category,
                "date": date,
                "questions": all_questions,
                "total_questions": len(all_questions),
                "meta": {
                    "pdf_path": pdf_path,
                    "pdf_source_id": pdf_source_id,
                    "chunks": len(chunks),
                    "chunk_meta": chunk_meta,
                },
            }

            # Persist to daily_questions and frontend questions
            try:
                saved = self.question_repo.save_questions(result)
                if saved and pdf_source_id:
                    self.pdf_source_repo.update_status(pdf_source_id, "done", error_reason=None)
            except Exception as exc:
                logger.warning(
                    "Failed to save PDF questions to daily_questions (pdf_source_id=%s): %s",
                    pdf_source_id,
                    exc,
                )
                if pdf_source_id:
                    self.pdf_source_repo.update_status(pdf_source_id, "failed", error_reason=str(exc))

            try:
                self.frontend_question_repo.save_questions_to_frontend_table(result, check_duplicates=True)
            except Exception as exc:
                logger.warning(
                    "Failed to save PDF questions to frontend table (pdf_source_id=%s): %s",
                    pdf_source_id,
                    exc,
                )

            return result

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
