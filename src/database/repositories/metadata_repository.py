"""Database repository for metadata summary"""

import logging
from typing import Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from src.database.models import MetadataSummary
from src.database.db import SessionLocal

logger = logging.getLogger(__name__)


class MetadataRepository:
    """Repository for metadata summary database operations"""

    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize repository
        
        Args:
            db_session: Database session (creates new if None)
        """
        self.db_session = db_session

    def save_daily_summary(self, date: str, stats: Dict) -> Optional[MetadataSummary]:
        """
        Save or update daily summary statistics
        
        Args:
            date: Date in YYYY-MM-DD format
            stats: Statistics dictionary
            
        Returns:
            Created/Updated MetadataSummary object or None on failure
        """
        try:
            if self.db_session:
                session = self.db_session
                should_close = False
            else:
                session = SessionLocal()
                should_close = True
            
            try:
                # Check if summary exists
                existing = session.query(MetadataSummary).filter(
                    MetadataSummary.date == date
                ).first()
                
                if existing:
                    # Update existing
                    existing.feeds_processed = stats.get('feeds_processed', 0)
                    existing.articles_fetched = stats.get('articles_fetched', 0)
                    existing.articles_processed = stats.get('articles_processed', 0)
                    existing.articles_failed = stats.get('articles_failed', 0)
                    existing.articles_skipped = stats.get('articles_skipped', 0)
                    existing.questions_generated = stats.get('questions_generated', 0)
                    existing.errors_count = stats.get('errors_count', 0)
                    existing.processing_time_seconds = stats.get('processing_time_seconds')
                    existing.updated_at = datetime.now()
                    
                    session.commit()
                    session.refresh(existing)
                    return existing
                else:
                    # Create new
                    summary = MetadataSummary(
                        date=date,
                        feeds_processed=stats.get('feeds_processed', 0),
                        articles_fetched=stats.get('articles_fetched', 0),
                        articles_processed=stats.get('articles_processed', 0),
                        articles_failed=stats.get('articles_failed', 0),
                        articles_skipped=stats.get('articles_skipped', 0),
                        questions_generated=stats.get('questions_generated', 0),
                        errors_count=stats.get('errors_count', 0),
                        processing_time_seconds=stats.get('processing_time_seconds')
                    )
                    
                    session.add(summary)
                    session.commit()
                    session.refresh(summary)
                    
                    return summary
                    
            finally:
                if should_close:
                    session.close()
                    
        except Exception as e:
            logger.error(f"Error saving daily summary: {str(e)}")
            if self.db_session:
                self.db_session.rollback()
            return None

    def get_summary_by_date(self, date: str) -> Optional[MetadataSummary]:
        """
        Get summary for a specific date
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            MetadataSummary object or None
        """
        try:
            if self.db_session:
                session = self.db_session
                should_close = False
            else:
                session = SessionLocal()
                should_close = True
            
            try:
                summary = session.query(MetadataSummary).filter(
                    MetadataSummary.date == date
                ).first()
                
                return summary
            finally:
                if should_close:
                    session.close()
                    
        except Exception as e:
            logger.error(f"Error fetching summary by date: {str(e)}")
            return None

    def get_recent_summaries(self, limit: int = 30) -> list:
        """
        Get recent summaries
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of MetadataSummary objects
        """
        try:
            if self.db_session:
                session = self.db_session
                should_close = False
            else:
                session = SessionLocal()
                should_close = True
            
            try:
                summaries = session.query(MetadataSummary).order_by(
                    MetadataSummary.date.desc()
                ).limit(limit).all()
                
                return summaries
            finally:
                if should_close:
                    session.close()
                    
        except Exception as e:
            logger.error(f"Error fetching recent summaries: {str(e)}")
            return []

