"""
Migrate questions from daily_questions JSON format to frontend questions table

This script extracts questions from the automation backend's daily_questions table
(which stores questions as JSON batches) and populates the frontend's questions table
(which stores individual questions).
"""

import sys
import os
from datetime import datetime
import logging

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy import text
from src.database.db import SessionLocal
from src.utils.logger import setup_logging

setup_logging()
logger = logging.getLogger('migrate_questions')

# Category mapping from automation backend to frontend categories
CATEGORY_MAPPING = {
    'Business': 'Economy',
    'Economy': 'Economy',
    'Banking': 'Economy',
    'Trade': 'Economy',
    'Current Affairs': 'Current Affairs',
    'Polity': 'India GK',
    'History': 'History',
    'Geography': 'India GK',
    'Science & Technology': 'India GK',
    'Environment': 'India GK',
    'International Relations': 'Current Affairs',
    'General Knowledge': 'India GK',
    'Explained': 'Current Affairs',
}

def get_difficulty_from_source_or_content(source, question_text, explanation):
    """
    Determine difficulty level based on source and content length/complexity
    
    Args:
        source: Article source (The Hindu, Indian Express, etc.)
        question_text: Question text
        explanation: Explanation text
    
    Returns:
        'easy', 'medium', or 'hard'
    """
    # Calculate content length
    total_length = len(question_text) + len(explanation)
    
    # Sources like "The Hindu" tend to have more complex questions
    if source in ['The Hindu', 'Indian Express']:
        if total_length > 400:
            return 'hard'
        elif total_length > 250:
            return 'medium'
        else:
            return 'easy'
    else:
        if total_length > 350:
            return 'medium'
        else:
            return 'easy'

def get_points_from_difficulty(difficulty):
    """
    Get points based on difficulty
    
    Args:
        difficulty: 'easy', 'medium', or 'hard'
    
    Returns:
        10, 15, or 20 points
    """
    points_map = {
        'easy': 10,
        'medium': 15,
        'hard': 20
    }
    return points_map.get(difficulty, 10)

def migrate_questions(session, dry_run=False):
    """
    Migrate questions from daily_questions to questions table
    
    Args:
        session: Database session
        dry_run: If True, don't commit changes (just log what would happen)
    
    Returns:
        Dictionary with migration statistics
    """
    stats = {
        'total_batches': 0,
        'total_questions_extracted': 0,
        'questions_inserted': 0,
        'questions_skipped': 0,
        'categories_mapped': {},
        'errors': []
    }
    
    try:
        # Get category mapping (frontend category names to UUIDs)
        logger.info("Fetching categories from database...")
        category_result = session.execute(text("SELECT id, name FROM categories"))
        categories = {row[1]: row[0] for row in category_result}
        logger.info(f"Found {len(categories)} categories: {list(categories.keys())}")
        
        # Get all daily_questions records
        logger.info("Fetching daily_questions records...")
        daily_questions_result = session.execute(text("""
            SELECT id, source, category, date, questions_json, total_questions, created_at
            FROM daily_questions
            ORDER BY created_at DESC
        """))
        
        daily_questions = daily_questions_result.fetchall()
        stats['total_batches'] = len(daily_questions)
        logger.info(f"Found {stats['total_batches']} question batches to process")
        
        # Process each batch
        for batch in daily_questions:
            batch_id, source, category, date, questions_json, total_questions, created_at = batch
            
            logger.info(f"Processing batch {batch_id}: {source} - {category} ({total_questions} questions)")
            
            # Map category to frontend category
            frontend_category = CATEGORY_MAPPING.get(category, 'Current Affairs')
            category_id = categories.get(frontend_category)
            
            if not category_id:
                logger.warning(f"Category not found for '{frontend_category}', skipping batch {batch_id}")
                stats['questions_skipped'] += total_questions
                continue
            
            # Track category usage
            if frontend_category not in stats['categories_mapped']:
                stats['categories_mapped'][frontend_category] = 0
            
            # Extract questions from JSON
            questions_list = questions_json.get('questions', [])
            
            for q in questions_list:
                try:
                    question_text = q.get('question', '').strip()
                    options = q.get('options', [])
                    answer = q.get('answer', '').upper().strip()
                    explanation = q.get('explanation', '').strip()
                    
                    # Validate question
                    if not question_text or len(options) != 4 or answer not in ['A', 'B', 'C', 'D']:
                        logger.warning(f"Invalid question in batch {batch_id}: {question_text[:50]}...")
                        stats['questions_skipped'] += 1
                        continue
                    
                    # Determine difficulty
                    difficulty = get_difficulty_from_source_or_content(source, question_text, explanation)
                    points = get_points_from_difficulty(difficulty)
                    
                    # Normalize answer to lowercase
                    correct_answer = answer.lower()
                    
                    # Check for duplicate questions
                    duplicate_check = session.execute(text("""
                        SELECT id FROM questions 
                        WHERE question_text = :question_text
                        LIMIT 1
                    """), {'question_text': question_text})
                    
                    if duplicate_check.fetchone():
                        logger.debug(f"Duplicate question skipped: {question_text[:50]}...")
                        stats['questions_skipped'] += 1
                        continue
                    
                    if not dry_run:
                        # Insert question
                        session.execute(text("""
                            INSERT INTO questions (
                                category_id, question_format, question_text,
                                option_a, option_b, option_c, option_d,
                                correct_answer, explanation, difficulty, points,
                                source, source_date, created_at
                            ) VALUES (
                                :category_id, :question_format, :question_text,
                                :option_a, :option_b, :option_c, :option_d,
                                :correct_answer, :explanation, :difficulty, :points,
                                :source, :source_date, :created_at
                            )
                        """), {
                            'category_id': category_id,
                            'question_format': 'multiple_choice',
                            'question_text': question_text,
                            'option_a': options[0],
                            'option_b': options[1],
                            'option_c': options[2],
                            'option_d': options[3],
                            'correct_answer': correct_answer,
                            'explanation': explanation,
                            'difficulty': difficulty,
                            'points': points,
                            'source': source,
                            'source_date': date,
                            'created_at': created_at
                        })
                        
                        stats['questions_inserted'] += 1
                        stats['categories_mapped'][frontend_category] += 1
                    else:
                        stats['questions_inserted'] += 1
                        stats['categories_mapped'][frontend_category] += 1
                        logger.debug(f"[DRY RUN] Would insert: {question_text[:50]}...")
                    
                    stats['total_questions_extracted'] += 1
                    
                except Exception as e:
                    error_msg = f"Error processing question in batch {batch_id}: {str(e)}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
                    stats['questions_skipped'] += 1
        
        if not dry_run:
            session.commit()
            logger.info("Migration committed successfully!")
        else:
            logger.info("[DRY RUN] No changes committed")
        
    except Exception as e:
        session.rollback()
        error_msg = f"Migration failed: {str(e)}"
        logger.error(error_msg)
        stats['errors'].append(error_msg)
        raise
    
    return stats

def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate questions from daily_questions to questions table')
    parser.add_argument('--dry-run', action='store_true', help='Run without committing changes')
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Starting question migration")
    logger.info(f"Dry run mode: {args.dry_run}")
    logger.info("=" * 80)
    
    session = SessionLocal()
    
    try:
        # Check if frontend schema exists
        logger.info("Checking if frontend schema exists...")
        result = session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'questions'
            )
        """))
        
        if not result.scalar():
            logger.error("Frontend schema not found! Please run migration first:")
            logger.error("  alembic upgrade head")
            return 1
        
        logger.info("Frontend schema found, proceeding with migration...")
        
        # Run migration
        stats = migrate_questions(session, dry_run=args.dry_run)
        
        # Print summary
        logger.info("=" * 80)
        logger.info("Migration Summary")
        logger.info("=" * 80)
        logger.info(f"Total batches processed: {stats['total_batches']}")
        logger.info(f"Total questions extracted: {stats['total_questions_extracted']}")
        logger.info(f"Questions inserted: {stats['questions_inserted']}")
        logger.info(f"Questions skipped: {stats['questions_skipped']}")
        logger.info("")
        logger.info("Questions by category:")
        for category, count in sorted(stats['categories_mapped'].items()):
            logger.info(f"  {category}: {count}")
        
        if stats['errors']:
            logger.warning(f"\nErrors encountered: {len(stats['errors'])}")
            for error in stats['errors'][:10]:  # Show first 10 errors
                logger.warning(f"  - {error}")
        
        logger.info("=" * 80)
        
        if args.dry_run:
            logger.info("\nThis was a DRY RUN. No changes were committed.")
            logger.info("Run without --dry-run to apply changes.")
        else:
            logger.info("\nMigration completed successfully!")
        
        return 0
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    finally:
        session.close()

if __name__ == '__main__':
    sys.exit(main())

