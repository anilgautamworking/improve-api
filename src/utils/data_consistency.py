"""
Data consistency utilities for checking and maintaining consistency
between daily_questions and questions tables
"""

import logging
from typing import Dict, List, Optional
from sqlalchemy import text
from src.database.db import SessionLocal, get_db_session

logger = logging.getLogger(__name__)


def check_data_consistency(session=None) -> Dict:
    """
    Check consistency between daily_questions and questions tables
    
    Args:
        session: Optional database session
        
    Returns:
        Dictionary with consistency check results
    """
    should_close = False
    if session is None:
        session = SessionLocal()
        should_close = True
    
    try:
        result = {
            'consistent': True,
            'issues': [],
            'daily_questions_count': 0,
            'questions_count': 0,
            'batches_without_questions': [],
            'total_questions_in_batches': 0,
            'total_questions_in_table': 0,
        }
        
        # Count batches in daily_questions
        dq_result = session.execute(text("SELECT COUNT(*) FROM daily_questions"))
        result['daily_questions_count'] = dq_result.scalar() or 0
        
        # Count questions in questions table
        q_result = session.execute(text("SELECT COUNT(*) FROM questions"))
        result['questions_count'] = q_result.scalar() or 0
        
        # Get all batches with their question counts
        batches_result = session.execute(text("""
            SELECT id, source, category, date, total_questions, created_at
            FROM daily_questions
            ORDER BY created_at DESC
        """))
        
        batches = batches_result.fetchall()
        result['total_questions_in_batches'] = sum(batch[4] for batch in batches)
        result['total_questions_in_table'] = result['questions_count']
        
        # Check for batches that might not have corresponding questions
        # This is a heuristic check - we can't perfectly match without parsing JSON
        if result['total_questions_in_batches'] > 0 and result['questions_count'] == 0:
            result['consistent'] = False
            result['issues'].append(
                f"Found {result['daily_questions_count']} batches with "
                f"{result['total_questions_in_batches']} total questions, "
                f"but questions table is empty. Migration may be needed."
            )
        
        # Check if there are batches but no questions (potential migration needed)
        if result['daily_questions_count'] > 0 and result['questions_count'] == 0:
            result['consistent'] = False
            result['issues'].append(
                "Questions table is empty but daily_questions has batches. "
                "Run migration: python scripts/migrate_questions_to_frontend_schema.py"
            )
        
        # Check if questions exist but no batches (unusual but not necessarily wrong)
        if result['questions_count'] > 0 and result['daily_questions_count'] == 0:
            result['issues'].append(
                "Questions table has data but daily_questions is empty. "
                "This is unusual but not necessarily an error."
            )
        
        return result
        
    finally:
        if should_close:
            session.close()


def find_missing_questions(session=None) -> List[Dict]:
    """
    Find batches in daily_questions that might not have corresponding questions
    This is a heuristic check based on dates and sources
    
    Args:
        session: Optional database session
        
    Returns:
        List of batches that might need migration
    """
    should_close = False
    if session is None:
        session = SessionLocal()
        should_close = True
    
    try:
        # Get batches from daily_questions
        batches_result = session.execute(text("""
            SELECT id, source, category, date, total_questions, created_at
            FROM daily_questions
            ORDER BY created_at DESC
        """))
        
        batches = batches_result.fetchall()
        missing_batches = []
        
        for batch in batches:
            batch_id, source, category, date, total_questions, created_at = batch
            
            # Check if any questions exist for this date/source combination
            check_result = session.execute(text("""
                SELECT COUNT(*) FROM questions
                WHERE source = :source AND source_date = :date
            """), {'source': source, 'date': date})
            
            question_count = check_result.scalar() or 0
            
            # If we have fewer questions than expected, mark as potentially missing
            if question_count < total_questions:
                missing_batches.append({
                    'batch_id': batch_id,
                    'source': source,
                    'category': category,
                    'date': date,
                    'expected_questions': total_questions,
                    'found_questions': question_count,
                    'missing_count': total_questions - question_count
                })
        
        return missing_batches
        
    finally:
        if should_close:
            session.close()


def get_consistency_status(session=None) -> Dict:
    """
    Get comprehensive consistency status
    
    Args:
        session: Optional database session
        
    Returns:
        Dictionary with consistency status
    """
    consistency = check_data_consistency(session)
    missing = find_missing_questions(session)
    
    return {
        'consistent': consistency['consistent'] and len(missing) == 0,
        'daily_questions_count': consistency['daily_questions_count'],
        'questions_count': consistency['questions_count'],
        'total_expected_questions': consistency['total_questions_in_batches'],
        'issues': consistency['issues'],
        'missing_batches': missing,
        'status': 'consistent' if (consistency['consistent'] and len(missing) == 0) else 'inconsistent',
        'message': 'Data is consistent' if (consistency['consistent'] and len(missing) == 0) else 'Data inconsistencies detected'
    }

