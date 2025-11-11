"""
Check and repair data consistency between daily_questions and questions tables
"""

import sys
import os
import argparse
import logging

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils.logger import setup_logging
from src.utils.data_consistency import check_data_consistency, find_missing_questions, get_consistency_status
from src.database.db import SessionLocal
from scripts.migrate_questions_to_frontend_schema import migrate_questions

setup_logging()
logger = logging.getLogger('check_consistency')


def main():
    """Main consistency check function"""
    parser = argparse.ArgumentParser(description='Check data consistency between daily_questions and questions tables')
    parser.add_argument('--repair', action='store_true', help='Attempt to repair inconsistencies by running migration')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (don\'t make changes)')
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Data Consistency Check")
    logger.info("=" * 80)
    
    session = SessionLocal()
    
    try:
        # Check consistency
        consistency = check_data_consistency(session)
        missing = find_missing_questions(session)
        status = get_consistency_status(session)
        
        logger.info(f"Daily Questions Batches: {consistency['daily_questions_count']}")
        logger.info(f"Questions in Frontend Table: {consistency['questions_count']}")
        logger.info(f"Total Questions in Batches: {consistency['total_questions_in_batches']}")
        logger.info("")
        
        if status['consistent']:
            logger.info("✓ Data is consistent!")
        else:
            logger.warning("⚠ Data inconsistencies detected:")
            for issue in status['issues']:
                logger.warning(f"  - {issue}")
            
            if missing:
                logger.warning(f"\nFound {len(missing)} batches with missing questions:")
                for batch in missing[:10]:  # Show first 10
                    logger.warning(
                        f"  - {batch['source']} ({batch['date']}): "
                        f"Expected {batch['expected_questions']}, Found {batch['found_questions']}, "
                        f"Missing {batch['missing_count']}"
                    )
                if len(missing) > 10:
                    logger.warning(f"  ... and {len(missing) - 10} more")
        
        # Repair if requested
        if not status['consistent'] and args.repair:
            logger.info("")
            logger.info("=" * 80)
            logger.info("Attempting to repair inconsistencies...")
            logger.info("=" * 80)
            
            if args.dry_run:
                logger.info("DRY RUN MODE - No changes will be made")
                return 0
            
            # Run migration to fix inconsistencies
            try:
                stats = migrate_questions(session, dry_run=False)
                logger.info("")
                logger.info("Migration Summary:")
                logger.info(f"  Questions inserted: {stats['questions_inserted']}")
                logger.info(f"  Questions skipped: {stats['questions_skipped']}")
                
                if stats['errors']:
                    logger.warning(f"  Errors: {len(stats['errors'])}")
                    for error in stats['errors'][:5]:
                        logger.warning(f"    - {error}")
                
                # Re-check consistency
                logger.info("")
                logger.info("Re-checking consistency...")
                new_status = get_consistency_status(session)
                if new_status['consistent']:
                    logger.info("✓ Data is now consistent!")
                else:
                    logger.warning("⚠ Some inconsistencies remain. Manual intervention may be needed.")
                    
            except Exception as e:
                logger.error(f"Error during repair: {str(e)}")
                return 1
        
        logger.info("=" * 80)
        return 0 if status['consistent'] else 1
        
    except Exception as e:
        logger.error(f"Error checking consistency: {str(e)}", exc_info=True)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())

