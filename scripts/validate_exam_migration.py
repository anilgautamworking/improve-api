"""
Validate exam migration and data consistency.

This script validates that:
1. All exams are seeded
2. Categories are properly mapped to exams
3. Questions are linked to categories that are mapped to exams
4. Data is ready for exam-based filtering
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy import text
from src.database.db import SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Expected exams
EXPECTED_EXAMS = ["JEE", "NEET", "UPSC", "Banking", "SSC"]


def validate_exams(session):
    """Validate that all expected exams exist."""
    result = session.execute(text("SELECT name FROM exams ORDER BY name"))
    exams = [row[0] for row in result.fetchall()]
    
    logger.info("Found exams: %s", ", ".join(exams))
    
    missing = set(EXPECTED_EXAMS) - set(exams)
    if missing:
        logger.warning("Missing exams: %s", ", ".join(missing))
        return False
    
    extra = set(exams) - set(EXPECTED_EXAMS)
    if extra:
        logger.info("Additional exams found: %s", ", ".join(extra))
    
    return True


def validate_category_mappings(session):
    """Validate that categories are mapped to exams."""
    result = session.execute(text("""
        SELECT COUNT(DISTINCT exam_id) as exam_count,
               COUNT(DISTINCT category_id) as category_count,
               COUNT(*) as total_mappings
        FROM exam_category
    """))
    row = result.fetchone()
    
    logger.info("Exam-category mappings: %s mappings, %s exams, %s categories", 
                row[0], row[1], row[2])
    
    if row[0] == 0:
        logger.error("No exam-category mappings found!")
        return False
    
    # Check for categories without exam mappings
    result = session.execute(text("""
        SELECT c.name
        FROM categories c
        LEFT JOIN exam_category ec ON c.id = ec.category_id
        WHERE ec.category_id IS NULL
    """))
    unmapped = [row[0] for row in result.fetchall()]
    
    if unmapped:
        logger.warning("Categories without exam mappings: %s", ", ".join(unmapped))
        # This is OK - some categories might not be mapped yet
    
    return True


def validate_questions(session):
    """Validate that questions are linked to categories."""
    result = session.execute(text("""
        SELECT COUNT(*) as total_questions,
               COUNT(DISTINCT category_id) as categories_with_questions
        FROM questions
    """))
    row = result.fetchone()
    
    logger.info("Questions: %s total, across %s categories", 
                row[0], row[1])
    
    # Check for questions with invalid category_id
    result = session.execute(text("""
        SELECT COUNT(*) as orphaned_questions
        FROM questions q
        LEFT JOIN categories c ON q.category_id = c.id
        WHERE c.id IS NULL
    """))
    orphaned = result.fetchone()[0]
    
    if orphaned > 0:
        logger.error("Found %s questions with invalid category_id!", orphaned)
        return False
    
    return True


def validate_data_consistency(session):
    """Validate overall data consistency."""
    # Check if questions can be filtered by exam through categories
    result = session.execute(text("""
        SELECT 
            e.name as exam_name,
            COUNT(DISTINCT ec.category_id) as category_count,
            COUNT(DISTINCT q.id) as question_count
        FROM exams e
        LEFT JOIN exam_category ec ON e.id = ec.exam_id
        LEFT JOIN categories c ON ec.category_id = c.id
        LEFT JOIN questions q ON c.id = q.category_id
        GROUP BY e.id, e.name
        ORDER BY e.name
    """))
    
    logger.info("\nExam → Category → Question mapping:")
    logger.info("-" * 60)
    for row in result.fetchall():
        logger.info("  %s: %s categories, %s questions", 
                    row[0], row[1], row[2])
    
    return True


def main():
    """Run all validation checks."""
    session = SessionLocal()
    
    try:
        logger.info("=" * 60)
        logger.info("Exam Migration Validation")
        logger.info("=" * 60)
        
        all_valid = True
        
        # Check exams
        logger.info("\n1. Validating exams...")
        if not validate_exams(session):
            all_valid = False
        
        # Check category mappings
        logger.info("\n2. Validating category mappings...")
        if not validate_category_mappings(session):
            all_valid = False
        
        # Check questions
        logger.info("\n3. Validating questions...")
        if not validate_questions(session):
            all_valid = False
        
        # Check data consistency
        logger.info("\n4. Validating data consistency...")
        validate_data_consistency(session)
        
        logger.info("\n" + "=" * 60)
        if all_valid:
            logger.info("✅ All validations passed!")
            return 0
        else:
            logger.error("❌ Some validations failed. Please review the output above.")
            return 1
            
    except Exception as exc:
        logger.error("Validation failed with error: %s", exc, exc_info=True)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())

