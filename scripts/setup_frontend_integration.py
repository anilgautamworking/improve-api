"""
Setup script for frontend integration

This script:
1. Runs the database migration to add frontend schema
2. Migrates existing questions to frontend format
3. Validates the setup
"""

import sys
import os
import subprocess

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils.logger import setup_logging
from sqlalchemy import text
from src.database.db import SessionLocal
import logging

setup_logging()
logger = logging.getLogger('frontend_integration')

def run_command(cmd, description):
    """Run a shell command and log output"""
    logger.info(f"Running: {description}")
    logger.info(f"Command: {cmd}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        if result.stdout:
            logger.info(result.stdout)
        if result.stderr:
            logger.warning(result.stderr)
        
        logger.info(f"✓ {description} completed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ {description} failed")
        logger.error(f"Error: {e}")
        if e.stdout:
            logger.error(f"STDOUT: {e.stdout}")
        if e.stderr:
            logger.error(f"STDERR: {e.stderr}")
        return False

def check_database_connection():
    """Check if database is accessible"""
    logger.info("Checking database connection...")
    
    try:
        session = SessionLocal()
        result = session.execute(text("SELECT version()"))
        version = result.scalar()
        logger.info(f"✓ Connected to PostgreSQL: {version}")
        session.close()
        return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {str(e)}")
        logger.error("Make sure PostgreSQL is running:")
        logger.error("  docker-compose up -d")
        return False

def check_current_schema():
    """Check current database schema"""
    logger.info("Checking current schema...")
    
    try:
        session = SessionLocal()
        
        # Check existing tables
        result = session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        
        tables = [row[0] for row in result]
        logger.info(f"Existing tables: {', '.join(tables)}")
        
        # Check if frontend tables exist
        frontend_tables = ['users', 'categories', 'questions', 'user_answers', 'quiz_attempts']
        existing_frontend_tables = [t for t in frontend_tables if t in tables]
        
        if existing_frontend_tables:
            logger.info(f"Frontend tables already exist: {', '.join(existing_frontend_tables)}")
        else:
            logger.info("No frontend tables found - migration needed")
        
        # Check daily_questions count
        result = session.execute(text("SELECT COUNT(*) FROM daily_questions"))
        count = result.scalar()
        logger.info(f"Current daily_questions count: {count}")
        
        session.close()
        return {
            'all_tables': tables,
            'frontend_exists': len(existing_frontend_tables) > 0,
            'question_batches': count
        }
        
    except Exception as e:
        logger.error(f"Error checking schema: {str(e)}")
        return None

def run_migration():
    """Run Alembic migration"""
    logger.info("=" * 80)
    logger.info("Running database migration")
    logger.info("=" * 80)
    
    return run_command(
        "alembic upgrade head",
        "Database migration (adding frontend schema)"
    )

def migrate_questions(dry_run=False):
    """Run question migration script"""
    logger.info("=" * 80)
    logger.info("Migrating questions to frontend format")
    logger.info("=" * 80)
    
    cmd = f"python scripts/migrate_questions_to_frontend_schema.py"
    if dry_run:
        cmd += " --dry-run"
    
    return run_command(
        cmd,
        "Question migration"
    )

def validate_migration():
    """Validate the migration was successful"""
    logger.info("=" * 80)
    logger.info("Validating migration")
    logger.info("=" * 80)
    
    try:
        session = SessionLocal()
        
        # Check categories
        result = session.execute(text("SELECT COUNT(*) FROM categories"))
        categories_count = result.scalar()
        logger.info(f"Categories: {categories_count}")
        
        # Check questions
        result = session.execute(text("SELECT COUNT(*) FROM questions"))
        questions_count = result.scalar()
        logger.info(f"Questions: {questions_count}")
        
        # Check questions by category
        result = session.execute(text("""
            SELECT c.name, COUNT(q.id) as count
            FROM categories c
            LEFT JOIN questions q ON c.id = q.category_id
            GROUP BY c.name
            ORDER BY count DESC
        """))
        
        logger.info("\nQuestions by category:")
        for row in result:
            logger.info(f"  {row[0]}: {row[1]}")
        
        # Check questions by difficulty
        result = session.execute(text("""
            SELECT difficulty, COUNT(*) as count
            FROM questions
            GROUP BY difficulty
            ORDER BY difficulty
        """))
        
        logger.info("\nQuestions by difficulty:")
        for row in result:
            logger.info(f"  {row[0]}: {row[1]}")
        
        # Check recent questions
        result = session.execute(text("""
            SELECT question_text, source, source_date
            FROM questions
            ORDER BY created_at DESC
            LIMIT 5
        """))
        
        logger.info("\nRecent questions (sample):")
        for row in result:
            logger.info(f"  [{row[1]} - {row[2]}] {row[0][:80]}...")
        
        session.close()
        
        if questions_count == 0:
            logger.warning("⚠ No questions found - migration may have failed")
            return False
        
        logger.info(f"\n✓ Migration validation passed ({questions_count} questions migrated)")
        return True
        
    except Exception as e:
        logger.error(f"✗ Validation failed: {str(e)}")
        return False

def main():
    """Main setup function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup frontend integration')
    parser.add_argument('--dry-run', action='store_true', help='Run migration in dry-run mode')
    parser.add_argument('--skip-migration', action='store_true', help='Skip Alembic migration')
    parser.add_argument('--skip-data-migration', action='store_true', help='Skip question data migration')
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Frontend Integration Setup")
    logger.info("=" * 80)
    
    # Step 1: Check database connection
    if not check_database_connection():
        logger.error("Setup failed: Cannot connect to database")
        return 1
    
    # Step 2: Check current schema
    schema_info = check_current_schema()
    if not schema_info:
        logger.error("Setup failed: Cannot check schema")
        return 1
    
    # Step 3: Run migration if needed
    if not args.skip_migration:
        if schema_info['frontend_exists']:
            logger.info("Frontend schema already exists, skipping migration")
        else:
            if not run_migration():
                logger.error("Setup failed: Migration failed")
                return 1
    else:
        logger.info("Skipping database migration (--skip-migration)")
    
    # Step 4: Migrate questions
    if not args.skip_data_migration:
        if schema_info['question_batches'] == 0:
            logger.warning("No question batches found in daily_questions table")
            logger.info("Run the daily pipeline first to generate questions:")
            logger.info("  python scripts/run_daily_pipeline.py")
        else:
            if not migrate_questions(dry_run=args.dry_run):
                logger.error("Setup failed: Question migration failed")
                return 1
    else:
        logger.info("Skipping question migration (--skip-data-migration)")
    
    # Step 5: Validate
    if not args.dry_run and not args.skip_data_migration:
        if not validate_migration():
            logger.error("Setup failed: Validation failed")
            return 1
    
    # Done!
    logger.info("=" * 80)
    logger.info("Setup completed successfully!")
    logger.info("=" * 80)
    
    if args.dry_run:
        logger.info("\nThis was a DRY RUN. No changes were committed.")
        logger.info("Run without --dry-run to apply changes.")
    else:
        logger.info("\nNext steps:")
        logger.info("1. Update frontend database configuration to point to this database")
        logger.info("   - Update Dailyquestionbank-frontend/.env:")
        logger.info("     DB_HOST=localhost")
        logger.info("     DB_PORT=5432")
        logger.info("     DB_NAME=daily_question_bank")
        logger.info("     DB_USER=postgres")
        logger.info("     DB_PASSWORD=postgres")
        logger.info("")
        logger.info("2. Test the frontend with the new database")
        logger.info("   - Start backend: cd Dailyquestionbank-frontend && npm run server")
        logger.info("   - Start frontend: npm run dev")
        logger.info("")
        logger.info("3. Questions will continue to be generated by automation backend cron jobs")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

