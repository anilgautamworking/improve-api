"""Daily pipeline runner script"""

#!/usr/bin/env python3
"""
Daily pipeline runner for Question Bank automation.
This script should be run via cron job daily.
"""

import sys
import os
import asyncio
from datetime import datetime
import time

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logger import setup_logging
from src.config.settings import settings
from src.pipeline.crawler_orchestrator import CrawlerOrchestrator
from src.pipeline.orchestrator import PipelineOrchestrator
from src.database.repositories.question_repository import QuestionRepository
from src.database.repositories.frontend_question_repository import FrontendQuestionRepository
from src.database.repositories.metadata_repository import MetadataRepository
from src.database.db import get_db_session

logger = setup_logging()


async def main_async():
    """Main pipeline execution"""
    start_time = time.time()
    logger.info("=" * 80)
    logger.info("Starting Daily Question Bank Pipeline")
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    try:
        # Validate settings
        settings.validate()
        logger.info("Settings validated successfully")

        # --- Stage 1: Crawl and Store Articles ---
        logger.info("--- Stage 1: Crawling and Storing Articles ---")
        with CrawlerOrchestrator() as crawler:
            feed_configs = settings.get_rss_feeds_config()
            await crawler.crawl_rss_feeds(feed_configs)
            crawler_stats = crawler.stats
            logger.info(f"Crawler finished. Fetched: {crawler_stats['articles_fetched']}, Stored: {crawler_stats['articles_stored']}")

        # --- Stage 2: Generate Questions from Stored Articles ---
        logger.info("--- Stage 2: Generating Questions from Stored Articles ---")
        with PipelineOrchestrator() as orchestrator:
            question_batches = orchestrator.process_articles_from_db()
            qg_stats = orchestrator.stats

        # Save questions to database (both formats) - wrapped in transaction for consistency
        with get_db_session() as db_session:
            question_repo = QuestionRepository(db_session)
            frontend_repo = FrontendQuestionRepository(db_session)
            saved_count = 0
            frontend_saved = 0
            frontend_skipped = 0
            
            for batch in question_batches:
                try:
                    # Use nested transaction to ensure atomicity: both saves succeed or both fail
                    savepoint = db_session.begin_nested()
                    try:
                        # Save to daily_questions table (original format)
                        result = question_repo.save_questions(batch)
                        if not result:
                            raise Exception(
                                f"Failed to save batch to daily_questions: {batch.get('source')} - {batch.get('category')}"
                            )

                        saved_count += 1
                        logger.info(f"Saved batch to daily_questions: {batch.get('source')} - {batch.get('category')} - {batch.get('total_questions')} questions")

                        # Also save to frontend questions table (individual questions)
                        frontend_stats = frontend_repo.save_questions_to_frontend_table(
                            batch, check_duplicates=True
                        )

                        if frontend_stats.get("errors"):
                            # If there are errors, rollback the entire batch
                            raise Exception(
                                f"Errors saving to frontend table: {frontend_stats['errors']}"
                            )

                        frontend_saved += frontend_stats["inserted"]
                        frontend_skipped += frontend_stats["skipped"]

                        if frontend_stats["inserted"] > 0:
                            logger.info(
                                f"Saved {frontend_stats['inserted']} questions to frontend table (skipped {frontend_stats['skipped']} duplicates)"
                            )

                        # Commit the nested transaction (both saves succeeded)
                        savepoint.commit()

                    except Exception as e:
                        # Rollback the nested transaction if either save failed
                        savepoint.rollback()
                        logger.error(
                            f"Error saving question batch (rolled back): {str(e)}"
                        )
                        raise
                    
                except Exception as e:
                    logger.error(f"Error saving question batch: {str(e)}")
                    # Continue with next batch instead of failing entire pipeline

        # Combine stats
        # Count errors instead of storing as list
        errors_count = len(crawler_stats.get('errors', [])) + len(qg_stats.get('errors', []))
        articles_failed_count = crawler_stats.get('articles_failed', 0) + qg_stats.get('articles_failed', 0)
        
        final_stats = {
            'feeds_processed': crawler_stats['feeds_processed'],
            'articles_fetched': crawler_stats['articles_fetched'],
            'articles_processed': qg_stats['articles_processed'],
            'articles_failed': articles_failed_count,
            'articles_skipped': qg_stats['articles_skipped'],
            'questions_generated': qg_stats.get('questions_generated', 0),
            'errors_count': errors_count,
            'processing_time_seconds': int(time.time() - start_time)
        }

        # Save daily summary
        with get_db_session() as db_session:
            metadata_repo = MetadataRepository(db_session)
            today = datetime.now().strftime('%Y-%m-%d')
            metadata_repo.save_daily_summary(today, final_stats)

        # Log summary
        logger.info("=" * 80)
        logger.info("Pipeline Summary:")
        logger.info(f"  Feeds Processed: {final_stats['feeds_processed']}")
        logger.info(f"  Articles Fetched: {final_stats['articles_fetched']}")
        logger.info(f"  Articles Processed for QG: {final_stats['articles_processed']}")
        logger.info(f"  Questions Generated: {final_stats['questions_generated']}")
        logger.info(f"  Batches Saved: {saved_count}")
        logger.info(f"  Frontend Questions Saved: {frontend_saved} (skipped {frontend_skipped} duplicates)")
        logger.info(f"  Processing Time: {final_stats['processing_time_seconds']} seconds")
        if final_stats.get('errors_count', 0) > 0:
            logger.warning(f"  Errors: {final_stats['errors_count']}")
        logger.info("=" * 80)

        logger.info("Pipeline completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Pipeline failed with error: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main_async())
    sys.exit(exit_code)

