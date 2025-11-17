"""Standalone script for Stage 2 question generation."""

import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils.logger import setup_logging
from src.config.settings import settings
from src.pipeline.orchestrator import PipelineOrchestrator
from src.database.db import get_db_session
from src.database.repositories.question_repository import QuestionRepository
from src.database.repositories.frontend_question_repository import FrontendQuestionRepository


def save_question_batches(question_batches, logger):
    """Persist generated batches to both storage tables."""
    with get_db_session() as db_session:
        question_repo = QuestionRepository(db_session)
        frontend_repo = FrontendQuestionRepository(db_session)
        saved_count = 0
        frontend_saved = 0
        frontend_skipped = 0

        for batch in question_batches:
            try:
                savepoint = db_session.begin_nested()
                try:
                    result = question_repo.save_questions(batch)
                    if not result:
                        raise ValueError(
                            f"Failed to save batch to daily_questions: {batch.get('source')} - {batch.get('category')}"
                        )

                    saved_count += 1
                    logger.info(
                        "Saved batch to daily_questions: %s - %s - %s questions",
                        batch.get('source'),
                        batch.get('category'),
                        batch.get('total_questions'),
                    )

                    frontend_stats = frontend_repo.save_questions_to_frontend_table(batch, check_duplicates=True)

                    if frontend_stats.get('errors'):
                        raise ValueError(f"Errors saving to frontend table: {frontend_stats['errors']}")

                    frontend_saved += frontend_stats['inserted']
                    frontend_skipped += frontend_stats['skipped']

                    if frontend_stats['inserted'] > 0:
                        logger.info(
                            "Saved %s questions to frontend table (skipped %s duplicates)",
                            frontend_stats['inserted'],
                            frontend_stats['skipped'],
                        )

                    savepoint.commit()
                except Exception:
                    savepoint.rollback()
                    raise
            except Exception as exc:
                logger.error("Error saving question batch: %s", exc)

    return {
        'saved_batches': saved_count,
        'frontend_saved': frontend_saved,
        'frontend_skipped': frontend_skipped,
    }


def run_generation(logger=None) -> dict:
    """Process pending articles and generate questions."""
    logger = logger or setup_logging()
    settings.validate()

    with PipelineOrchestrator() as orchestrator:
        question_batches = orchestrator.process_articles_from_db()
        stats = orchestrator.stats.copy()

    if not question_batches:
        logger.info("No question batches generated.")
        return {
            'question_stats': stats,
            'saved_batches': 0,
            'frontend_saved': 0,
            'frontend_skipped': 0,
        }

    save_stats = save_question_batches(question_batches, logger)

    combined = {
        'question_stats': stats,
        **save_stats,
    }

    logger.info(
        "Question generation finished at %s. Processed articles: %s, questions generated: %s",
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        stats.get('articles_processed', 0),
        stats.get('questions_generated', 0),
    )
    return combined


def main():
    logger = setup_logging()
    results = run_generation(logger=logger)
    stats = results.get('question_stats', {})

    logger.info("=" * 60)
    logger.info("Stage 2 Summary (Question Generation)")
    logger.info("Articles processed: %s", stats.get('articles_processed', 0))
    logger.info("Articles skipped: %s", stats.get('articles_skipped', 0))
    logger.info("Articles failed: %s", stats.get('articles_failed', 0))
    logger.info("Questions generated: %s", stats.get('questions_generated', 0))
    logger.info("Batches saved: %s", results.get('saved_batches', 0))
    logger.info(
        "Frontend questions saved: %s (skipped %s duplicates)",
        results.get('frontend_saved', 0),
        results.get('frontend_skipped', 0),
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
