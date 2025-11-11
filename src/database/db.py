"""Database connection and session management"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import os
from dotenv import load_dotenv

load_dotenv()

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/daily_question_bank")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False  # Set to True for SQL query logging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Get database session (for dependency injection)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """Context manager for database session"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_generator():
    """Generator function for database session (for dependency injection)"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def check_frontend_schema_exists(session=None):
    """
    Check if frontend schema (questions table) exists
    
    Args:
        session: Optional database session (creates new if None)
        
    Returns:
        bool: True if frontend schema exists, False otherwise
    """
    should_close = False
    if session is None:
        session = SessionLocal()
        should_close = True
    
    try:
        from sqlalchemy import text
        result = session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'questions'
            )
        """))
        exists = result.scalar()
        return exists
    finally:
        if should_close:
            session.close()


def check_questions_migrated(session=None):
    """
    Check if questions have been migrated to frontend table
    
    Args:
        session: Optional database session (creates new if None)
        
    Returns:
        dict: Status information with 'migrated', 'question_count', 'batch_count'
    """
    should_close = False
    if session is None:
        session = SessionLocal()
        should_close = True
    
    try:
        from sqlalchemy import text
        
        # Check if questions table exists
        schema_exists = check_frontend_schema_exists(session)
        if not schema_exists:
            return {
                'migrated': False,
                'question_count': 0,
                'batch_count': 0,
                'schema_exists': False
            }
        
        # Count questions in frontend table
        q_result = session.execute(text("SELECT COUNT(*) FROM questions"))
        question_count = q_result.scalar() or 0
        
        # Count batches in daily_questions table
        dq_result = session.execute(text("SELECT COUNT(*) FROM daily_questions"))
        batch_count = dq_result.scalar() or 0
        
        return {
            'migrated': question_count > 0,
            'question_count': question_count,
            'batch_count': batch_count,
            'schema_exists': True
        }
    finally:
        if should_close:
            session.close()


def get_migration_status(session=None):
    """
    Get comprehensive migration status
    
    Args:
        session: Optional database session (creates new if None)
        
    Returns:
        dict: Migration status with details
    """
    should_close = False
    if session is None:
        session = SessionLocal()
        should_close = True
    
    try:
        from sqlalchemy import text
        
        status = {
            'schema_exists': False,
            'questions_migrated': False,
            'question_count': 0,
            'batch_count': 0,
            'categories_count': 0,
            'status': 'unknown',
            'message': ''
        }
        
        # Check schema
        schema_exists = check_frontend_schema_exists(session)
        status['schema_exists'] = schema_exists
        
        if not schema_exists:
            status['status'] = 'schema_missing'
            status['message'] = 'Frontend schema not found. Run: alembic upgrade head'
            return status
        
        # Check questions
        q_result = session.execute(text("SELECT COUNT(*) FROM questions"))
        question_count = q_result.scalar() or 0
        status['question_count'] = question_count
        
        # Check batches
        dq_result = session.execute(text("SELECT COUNT(*) FROM daily_questions"))
        batch_count = dq_result.scalar() or 0
        status['batch_count'] = batch_count
        
        # Check categories
        cat_result = session.execute(text("SELECT COUNT(*) FROM categories"))
        categories_count = cat_result.scalar() or 0
        status['categories_count'] = categories_count
        
        # Determine status
        if question_count > 0:
            status['questions_migrated'] = True
            status['status'] = 'ready'
            status['message'] = 'Frontend schema and questions are ready'
        elif batch_count > 0:
            status['status'] = 'data_migration_needed'
            status['message'] = f'Schema exists but {batch_count} batches need migration. Run: python scripts/migrate_questions_to_frontend_schema.py'
        else:
            status['status'] = 'no_data'
            status['message'] = 'Schema exists but no questions found. Run the daily pipeline to generate questions.'
        
        return status
    finally:
        if should_close:
            session.close()

