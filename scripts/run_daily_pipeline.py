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
from src.database.repositories.metadata_repository import MetadataRepository
from src.database.db import get_db

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
        crawler = CrawlerOrchestrator()
        feed_configs = settings.get_rss_feeds_config()
        await crawler.crawl_rss_feeds(feed_configs)
        crawler_stats = crawler.stats
        logger.info(f"Crawler finished. Fetched: {crawler_stats['articles_fetched']}, Stored: {crawler_stats['articles_stored']}")

        # --- Stage 2: Generate Questions from Stored Articles ---
        logger.info("--- Stage 2: Generating Questions from Stored Articles ---")
        orchestrator = PipelineOrchestrator()
        question_batches = orchestrator.process_articles_from_db()

        # Save questions to database
        db_session = next(get_db())
        question_repo = QuestionRepository(db_session)
        saved_count = 0
        for batch in question_batches:
            try:
                result = question_repo.save_questions(batch)
                if result:
                    saved_count += 1
                    logger.info(f"Saved batch: {batch.get('source')} - {batch.get('category')} - {batch.get('total_questions')} questions")
            except Exception as e:
                logger.error(f"Error saving question batch: {str(e)}")

        # Combine stats
        qg_stats = orchestrator.stats
        final_stats = {
            'feeds_processed': crawler_stats['feeds_processed'],
            'articles_fetched': crawler_stats['articles_fetched'],
            'articles_processed': qg_stats['articles_processed'],
            'articles_failed': crawler_stats['errors'] + qg_stats['errors'],
            'articles_skipped': qg_stats['articles_skipped'],
            'questions_generated': qg_stats['questions_generated'],
            'processing_time_seconds': int(time.time() - start_time)
        }

        # Save daily summary
        db_session = next(get_db())
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
        logger.info(f"  Processing Time: {final_stats['processing_time_seconds']} seconds")
        if final_stats['articles_failed']:
            logger.warning(f"  Errors: {len(final_stats['articles_failed'])}")
        logger.info("=" * 80)

        logger.info("Pipeline completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Pipeline failed with error: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main_async())
    sys.exit(exit_code)

