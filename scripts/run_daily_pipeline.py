"""Daily pipeline runner script"""

#!/usr/bin/env python3
"""
Daily pipeline runner for Question Bank automation.
This script should be run via cron job daily.
"""

import sys
import os
from datetime import datetime
import time

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logger import setup_logging
from src.config.settings import settings
from src.pipeline.orchestrator import PipelineOrchestrator
from src.database.repositories.question_repository import QuestionRepository
from src.database.repositories.article_repository import ArticleRepository
from src.database.repositories.metadata_repository import MetadataRepository

logger = setup_logging()


def main():
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

        # Initialize components
        orchestrator = PipelineOrchestrator()
        question_repo = QuestionRepository()
        article_repo = ArticleRepository()
        metadata_repo = MetadataRepository()

        # Get RSS feed configurations
        feed_configs = settings.get_rss_feeds_config()
        logger.info(f"Processing {len(feed_configs)} RSS feed configurations")

        # Process RSS feeds
        question_batches = orchestrator.process_rss_feeds(feed_configs)

        # Save questions to database
        saved_count = 0
        for batch in question_batches:
            try:
                result = question_repo.save_questions(batch)
                if result:
                    saved_count += 1
                    logger.info(f"Saved batch: {batch.get('source')} - {batch.get('category')} - {batch.get('total_questions')} questions")
            except Exception as e:
                logger.error(f"Error saving question batch: {str(e)}")

        # Get pipeline statistics
        stats = orchestrator.get_stats()
        processing_time = int(time.time() - start_time)
        stats['processing_time_seconds'] = processing_time

        # Save daily summary
        today = datetime.now().strftime('%Y-%m-%d')
        metadata_repo.save_daily_summary(today, stats)

        # Log summary
        logger.info("=" * 80)
        logger.info("Pipeline Summary:")
        logger.info(f"  Feeds Processed: {stats['feeds_processed']}")
        logger.info(f"  Articles Fetched: {stats['articles_fetched']}")
        logger.info(f"  Articles Processed: {stats['articles_processed']}")
        logger.info(f"  Articles Failed: {stats['articles_failed']}")
        logger.info(f"  Articles Skipped: {stats['articles_skipped']}")
        logger.info(f"  Questions Generated: {stats['questions_generated']}")
        logger.info(f"  Batches Saved: {saved_count}")
        logger.info(f"  Processing Time: {processing_time} seconds")
        if stats['errors']:
            logger.warning(f"  Errors: {len(stats['errors'])}")
        logger.info("=" * 80)

        logger.info("Pipeline completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Pipeline failed with error: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

