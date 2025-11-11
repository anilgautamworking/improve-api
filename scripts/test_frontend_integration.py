"""
Test script for frontend integration

This script validates that the frontend integration is working correctly.
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy import text
from src.database.db import SessionLocal
from src.utils.logger import setup_logging
import json
import logging

setup_logging()
logger = logging.getLogger('test_frontend_integration')

def test_database_connection():
    """Test database connectivity"""
    logger.info("Testing database connection...")
    try:
        session = SessionLocal()
        result = session.execute(text("SELECT version()"))
        version = result.scalar()
        logger.info(f"✓ Connected to PostgreSQL: {version[:50]}...")
        session.close()
        return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {str(e)}")
        return False

def test_frontend_schema():
    """Test that frontend schema exists"""
    logger.info("\nTesting frontend schema...")
    try:
        session = SessionLocal()
        
        required_tables = ['users', 'categories', 'questions', 'user_answers', 'quiz_attempts']
        existing_tables = []
        
        for table in required_tables:
            result = session.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table}'
                )
            """))
            if result.scalar():
                existing_tables.append(table)
        
        if len(existing_tables) == len(required_tables):
            logger.info(f"✓ All frontend tables exist: {', '.join(existing_tables)}")
            session.close()
            return True
        else:
            missing = set(required_tables) - set(existing_tables)
            logger.error(f"✗ Missing tables: {', '.join(missing)}")
            logger.error("  Run: alembic upgrade head")
            session.close()
            return False
            
    except Exception as e:
        logger.error(f"✗ Schema check failed: {str(e)}")
        return False

def test_categories():
    """Test categories table"""
    logger.info("\nTesting categories...")
    try:
        session = SessionLocal()
        
        result = session.execute(text("SELECT id, name FROM categories ORDER BY name"))
        categories = list(result)
        
        if len(categories) >= 6:
            logger.info(f"✓ Found {len(categories)} categories:")
            for cat_id, name in categories:
                logger.info(f"  - {name} ({cat_id})")
            session.close()
            return True
        else:
            logger.error(f"✗ Expected at least 6 categories, found {len(categories)}")
            session.close()
            return False
            
    except Exception as e:
        logger.error(f"✗ Categories check failed: {str(e)}")
        return False

def test_questions():
    """Test questions table"""
    logger.info("\nTesting questions...")
    try:
        session = SessionLocal()
        
        # Check count
        result = session.execute(text("SELECT COUNT(*) FROM questions"))
        count = result.scalar()
        
        if count == 0:
            logger.warning("⚠ No questions found in questions table")
            logger.warning("  Run: python scripts/migrate_questions_to_frontend_schema.py")
            session.close()
            return False
        
        logger.info(f"✓ Found {count} questions")
        
        # Check distribution by category
        result = session.execute(text("""
            SELECT c.name, COUNT(q.id) as count
            FROM categories c
            LEFT JOIN questions q ON c.id = q.category_id
            GROUP BY c.name
            ORDER BY count DESC
        """))
        
        logger.info("  Questions by category:")
        for name, cat_count in result:
            logger.info(f"    {name}: {cat_count}")
        
        # Check distribution by difficulty
        result = session.execute(text("""
            SELECT difficulty, COUNT(*) as count
            FROM questions
            GROUP BY difficulty
            ORDER BY difficulty
        """))
        
        logger.info("  Questions by difficulty:")
        for difficulty, diff_count in result:
            logger.info(f"    {difficulty}: {diff_count}")
        
        # Check sample question
        result = session.execute(text("""
            SELECT question_text, option_a, option_b, option_c, option_d, correct_answer, difficulty
            FROM questions
            LIMIT 1
        """))
        
        sample = result.fetchone()
        if sample:
            logger.info("\n  Sample question:")
            logger.info(f"    Q: {sample[0][:80]}...")
            logger.info(f"    A: {sample[1][:40]}...")
            logger.info(f"    B: {sample[2][:40]}...")
            logger.info(f"    C: {sample[3][:40]}...")
            logger.info(f"    D: {sample[4][:40]}...")
            logger.info(f"    Correct: {sample[5].upper()}")
            logger.info(f"    Difficulty: {sample[6]}")
        
        session.close()
        return True
        
    except Exception as e:
        logger.error(f"✗ Questions check failed: {str(e)}")
        return False

def test_automation_tables():
    """Test that automation backend tables still exist"""
    logger.info("\nTesting automation backend tables...")
    try:
        session = SessionLocal()
        
        # Check daily_questions
        result = session.execute(text("SELECT COUNT(*) FROM daily_questions"))
        dq_count = result.scalar()
        logger.info(f"✓ daily_questions: {dq_count} batches")
        
        # Check articles
        result = session.execute(text("SELECT COUNT(*) FROM articles"))
        art_count = result.scalar()
        logger.info(f"✓ articles: {art_count} articles")
        
        # Check article_logs
        result = session.execute(text("SELECT COUNT(*) FROM article_logs"))
        log_count = result.scalar()
        logger.info(f"✓ article_logs: {log_count} logs")
        
        session.close()
        return True
        
    except Exception as e:
        logger.error(f"✗ Automation tables check failed: {str(e)}")
        return False

def test_data_consistency():
    """Test data consistency between daily_questions and questions tables"""
    logger.info("\nTesting data consistency...")
    try:
        session = SessionLocal()
        
        # Get total questions from daily_questions (sum of total_questions)
        result = session.execute(text("SELECT SUM(total_questions) FROM daily_questions"))
        dq_total = result.scalar() or 0
        
        # Get count from questions table
        result = session.execute(text("SELECT COUNT(*) FROM questions"))
        q_total = result.scalar() or 0
        
        logger.info(f"  Daily questions batches contain: {dq_total} total questions")
        logger.info(f"  Questions table contains: {q_total} individual questions")
        
        if q_total == 0 and dq_total > 0:
            logger.warning("⚠ Questions not yet migrated to frontend format")
            logger.warning("  Run: python scripts/migrate_questions_to_frontend_schema.py")
            session.close()
            return False
        elif q_total < dq_total * 0.8:
            logger.warning(f"⚠ Some questions may be missing ({q_total}/{dq_total})")
        else:
            logger.info("✓ Question counts are reasonable")
        
        session.close()
        return True
        
    except Exception as e:
        logger.error(f"✗ Consistency check failed: {str(e)}")
        return False

def test_query_performance():
    """Test query performance for common frontend queries"""
    logger.info("\nTesting query performance...")
    try:
        session = SessionLocal()
        import time
        
        # Test 1: Get questions by category
        start = time.time()
        result = session.execute(text("""
            SELECT q.id, q.question_text, q.difficulty
            FROM questions q
            JOIN categories c ON q.category_id = c.id
            WHERE c.name = 'Current Affairs'
            ORDER BY q.created_at DESC
            LIMIT 10
        """))
        questions = list(result)
        elapsed = time.time() - start
        
        logger.info(f"✓ Query 1 (get 10 questions by category): {elapsed:.3f}s")
        
        # Test 2: Get user stats (simulate)
        start = time.time()
        result = session.execute(text("""
            SELECT COUNT(*) 
            FROM questions
            WHERE difficulty = 'medium'
        """))
        count = result.scalar()
        elapsed = time.time() - start
        
        logger.info(f"✓ Query 2 (count by difficulty): {elapsed:.3f}s ({count} questions)")
        
        session.close()
        
        if elapsed > 1.0:
            logger.warning(f"⚠ Queries are slow (>{elapsed:.1f}s). Consider adding indexes.")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Performance test failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    logger.info("=" * 80)
    logger.info("Frontend Integration Test Suite")
    logger.info("=" * 80)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Frontend Schema", test_frontend_schema),
        ("Categories", test_categories),
        ("Questions", test_questions),
        ("Automation Tables", test_automation_tables),
        ("Data Consistency", test_data_consistency),
        ("Query Performance", test_query_performance),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("Test Summary")
    logger.info("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status:8} - {test_name}")
    
    logger.info("=" * 80)
    logger.info(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("✓ All tests passed! Frontend integration is ready.")
        logger.info("\nNext steps:")
        logger.info("1. Update frontend .env file with new database credentials")
        logger.info("2. Start frontend backend: cd Dailyquestionbank-frontend && npm run server")
        logger.info("3. Start frontend: npm run dev")
        logger.info("4. Test the application at http://localhost:5173")
        return 0
    else:
        logger.error("✗ Some tests failed. Review the logs above.")
        logger.error("\nCommon fixes:")
        logger.error("- Run: alembic upgrade head (if schema is missing)")
        logger.error("- Run: python scripts/migrate_questions_to_frontend_schema.py (if questions are missing)")
        logger.error("- Check: docker-compose ps (ensure database is running)")
        return 1

if __name__ == '__main__':
    sys.exit(main())

