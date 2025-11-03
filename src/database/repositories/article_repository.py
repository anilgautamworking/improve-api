"""Database repository for article logs"""

import logging
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from src.database.models import ArticleLog
from src.database.db import SessionLocal

logger = logging.getLogger(__name__)


class ArticleRepository:
    """Repository for article log database operations"""

    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize repository
        
        Args:
            db_session: Database session (creates new if None)
        """
        self.db_session = db_session

    def log_article(self, url: str, title: str, source: str, category: Optional[str] = None,
                   status: str = "pending") -> Optional[ArticleLog]:
        """
        Log article processing
        
        Args:
            url: Article URL
            title: Article title
            source: Source name
            category: Article category
            status: Processing status (pending, processed, failed, skipped)
            
        Returns:
            Created ArticleLog object or None on failure
        """
        try:
            if self.db_session:
                session = self.db_session
                should_close = False
            else:
                session = SessionLocal()
                should_close = True
            
            try:
                # Check if article already exists
                existing = session.query(ArticleLog).filter(
                    ArticleLog.source_url == url
                ).first()
                
                if existing:
                    # Update existing record
                    existing.title = title
                    existing.category = category or existing.category
                    existing.status = status
                    if status == "processed":
                        existing.processed_at = datetime.now()
                    session.commit()
                    session.refresh(existing)
                    return existing
                else:
                    # Create new record
                    article_log = ArticleLog(
                        source_url=url,
                        title=title,
                        category=category,
                        source=source,
                        status=status
                    )
                    
                    session.add(article_log)
                    session.commit()
                    session.refresh(article_log)
                    
                    return article_log
                    
            finally:
                if should_close:
                    session.close()
                    
        except Exception as e:
            logger.error(f"Error logging article: {str(e)}")
            if self.db_session:
                self.db_session.rollback()
            return None

    def update_article_status(self, url: str, status: str, error_log: Optional[str] = None,
                            questions_generated: int = 0) -> bool:
        """
        Update article processing status
        
        Args:
            url: Article URL
            status: New status
            error_log: Error message if failed
            questions_generated: Number of questions generated
            
        Returns:
            True if updated successfully
        """
        try:
            if self.db_session:
                session = self.db_session
                should_close = False
            else:
                session = SessionLocal()
                should_close = True
            
            try:
                article = session.query(ArticleLog).filter(
                    ArticleLog.source_url == url
                ).first()
                
                if article:
                    article.status = status
                    article.error_log = error_log
                    article.questions_generated = questions_generated
                    if status == "processed":
                        article.processed_at = datetime.now()
                    session.commit()
                    return True
                else:
                    logger.warning(f"Article not found: {url}")
                    return False
                    
            finally:
                if should_close:
                    session.close()
                    
        except Exception as e:
            logger.error(f"Error updating article status: {str(e)}")
            return False

    def get_articles_by_status(self, status: str, limit: int = 100) -> List[ArticleLog]:
        """
        Get articles by status
        
        Args:
            status: Status to filter by
            limit: Maximum number of results
            
        Returns:
            List of ArticleLog objects
        """
        try:
            if self.db_session:
                session = self.db_session
                should_close = False
            else:
                session = SessionLocal()
                should_close = True
            
            try:
                articles = session.query(ArticleLog).filter(
                    ArticleLog.status == status
                ).order_by(ArticleLog.created_at.desc()).limit(limit).all()
                
                return articles
            finally:
                if should_close:
                    session.close()
                    
        except Exception as e:
            logger.error(f"Error fetching articles by status: {str(e)}")
            return []

    def get_articles_by_source(self, source: str, limit: int = 100) -> List[ArticleLog]:
        """
        Get articles by source
        
        Args:
            source: Source name
            limit: Maximum number of results
            
        Returns:
            List of ArticleLog objects
        """
        try:
            if self.db_session:
                session = self.db_session
                should_close = False
            else:
                session = SessionLocal()
                should_close = True
            
            try:
                articles = session.query(ArticleLog).filter(
                    ArticleLog.source == source
                ).order_by(ArticleLog.created_at.desc()).limit(limit).all()
                
                return articles
            finally:
                if should_close:
                    session.close()
                    
        except Exception as e:
            logger.error(f"Error fetching articles by source: {str(e)}")
            return []

