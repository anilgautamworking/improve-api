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
from src.database.repositories.metadata_repository import MetadataRepository
from src.database.db import get_db_session
from scripts import crawl_feeds, generate_questions

logger = setup_logging()


async def main_async():
    """Main pipeline execution"""
    start_time = time.time()
    logger.info("=" * 80)
    logger.info("Starting Daily Question Bank Pipeline")
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    try:
        # --- Stage 1: Crawl and Store Articles ---
        logger.info("--- Stage 1: Crawling and Storing Articles ---")
        crawler_stats = await crawl_feeds.run_crawl(logger=logger)
        logger.info("Crawler finished. Fetched: %s, Stored: %s",
                    crawler_stats.get('articles_fetched', 0),
                    crawler_stats.get('articles_stored', 0))

        # --- Stage 2: Generate Questions from Stored Articles ---
        logger.info("--- Stage 2: Generating Questions from Stored Articles ---")
        generation_results = generate_questions.run_generation(logger=logger)
        qg_stats = generation_results.get('question_stats', {})
        saved_count = generation_results.get('saved_batches', 0)
        frontend_saved = generation_results.get('frontend_saved', 0)
        frontend_skipped = generation_results.get('frontend_skipped', 0)

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
