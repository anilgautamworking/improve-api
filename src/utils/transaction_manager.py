"""
Database transaction management utilities.

Provides savepoint support for batch operations and proper rollback handling.
"""

import logging
from contextlib import contextmanager
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


@contextmanager
def savepoint(session: Session, name: str = "sp"):
    """
    Create a savepoint context manager for nested transactions.
    
    Usage:
        with savepoint(session, "batch_1"):
            # Do work
            session.commit()  # Commits to savepoint
        # If exception occurs, rolls back to savepoint
    
    Args:
        session: SQLAlchemy session
        name: Savepoint name (must be unique within transaction)
    """
    savepoint_name = f"sp_{name}"
    try:
        session.execute(text(f"SAVEPOINT {savepoint_name}"))
        logger.debug(f"Created savepoint: {savepoint_name}")
        yield
        session.execute(text(f"RELEASE SAVEPOINT {savepoint_name}"))
        logger.debug(f"Released savepoint: {savepoint_name}")
    except Exception as e:
        logger.error(f"Error in savepoint {savepoint_name}, rolling back: {str(e)}")
        session.execute(text(f"ROLLBACK TO SAVEPOINT {savepoint_name}"))
        logger.debug(f"Rolled back to savepoint: {savepoint_name}")
        raise


@contextmanager
def batch_transaction(session: Session, batch_size: int = 10, commit_on_success: bool = True):
    """
    Context manager for batch operations with automatic commit/rollback.
    
    Usage:
        with batch_transaction(session, batch_size=10):
            for item in items:
                session.add(item)
                # Commits every 10 items automatically
        # Final commit on success, rollback on failure
    
    Args:
        session: SQLAlchemy session
        batch_size: Number of operations before auto-commit
        commit_on_success: Whether to commit on successful exit
    """
    count = 0
    try:
        yield
        count += 1
        if count % batch_size == 0:
            session.commit()
            logger.debug(f"Auto-committed batch ({count} operations)")
        
        if commit_on_success:
            session.commit()
            logger.debug("Final commit on successful batch transaction")
    except Exception as e:
        session.rollback()
        logger.error(f"Batch transaction failed, rolled back: {str(e)}")
        raise


def safe_commit(session: Session, max_retries: int = 3):
    """
    Safely commit a transaction with retry logic.
    
    Args:
        session: SQLAlchemy session
        max_retries: Maximum retry attempts
        
    Returns:
        True if commit successful, False otherwise
    """
    for attempt in range(max_retries):
        try:
            session.commit()
            return True
        except Exception as e:
            logger.warning(f"Commit attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                session.rollback()
            else:
                logger.error("Max retries reached, rolling back transaction")
                session.rollback()
                return False
    return False

