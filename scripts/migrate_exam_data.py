"""
Complete exam data migration script.

This script:
1. Ensures all exams are seeded (idempotent)
2. Seeds categories and exam-category mappings
3. Validates data consistency
4. Can be run multiple times safely
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy import text
from src.database.db import SessionLocal
from scripts.seed_exam_categories import seed_exam_categories
from scripts.validate_exam_migration import (
    validate_exams,
    validate_category_mappings,
    validate_questions,
    validate_data_consistency
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ensure_exams_seeded(session):
    """Ensure all expected exams are seeded (idempotent)."""
    expected_exams = [
        ("JEE", "Engineering", "Joint Entrance Examination - Engineering"),
        ("NEET", "Medical", "National Eligibility cum Entrance Test - Medical"),
        ("UPSC", "Civil Services", "Union Public Service Commission - Civil Services"),
        ("Banking", "Banking", "Banking and Financial Services"),
        ("SSC", "Government", "Staff Selection Commission - Government Jobs"),
    ]
    
    created = 0
    for name, category, description in expected_exams:
        result = session.execute(
            text("""
                INSERT INTO exams (name, category, description)
                VALUES (:name, :category, :description)
                ON CONFLICT (name) DO NOTHING
                RETURNING id
            """),
            {"name": name, "category": category, "description": description}
        )
        if result.fetchone():
            created += 1
            logger.info("Created exam: %s", name)
    
    if created:
        session.commit()
        logger.info("Created %s new exams", created)
    else:
        logger.info("All exams already exist")
    
    return created


def main():
    """Run complete exam data migration."""
    session = SessionLocal()
    
    try:
        logger.info("=" * 60)
        logger.info("Exam Data Migration")
        logger.info("=" * 60)
        
        # Step 1: Ensure exams are seeded
        logger.info("\nStep 1: Ensuring exams are seeded...")
        ensure_exams_seeded(session)
        
        # Step 2: Seed categories and mappings
        logger.info("\nStep 2: Seeding categories and exam-category mappings...")
        seed_exam_categories()
        
        # Step 3: Validate everything
        logger.info("\nStep 3: Validating migration...")
        session = SessionLocal()  # Refresh session
        
        all_valid = True
        if not validate_exams(session):
            all_valid = False
        if not validate_category_mappings(session):
            all_valid = False
        if not validate_questions(session):
            all_valid = False
        
        validate_data_consistency(session)
        
        logger.info("\n" + "=" * 60)
        if all_valid:
            logger.info("✅ Migration complete and validated!")
            return 0
        else:
            logger.warning("⚠️  Migration completed but some validations failed.")
            logger.warning("   Review the output above for details.")
            return 1
            
    except Exception as exc:
        logger.error("Migration failed: %s", exc, exc_info=True)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())

