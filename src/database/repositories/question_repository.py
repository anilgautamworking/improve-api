"""Database repository for questions"""

import json
import logging
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from src.database.models import DailyQuestion
from src.database.db import SessionLocal

logger = logging.getLogger(__name__)


class QuestionRepository:
    """Repository for question database operations"""

    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize repository
        
        Args:
            db_session: Database session (creates new if None)
        """
        self.db_session = db_session

    def save_questions(self, questions_data: Dict) -> Optional[DailyQuestion]:
        """
        Save generated questions to database
        
        Args:
            questions_data: Question data dictionary with source, category, date, questions
            
        Returns:
            Created DailyQuestion object or None on failure
        """
        try:
            if self.db_session:
                session = self.db_session
                should_close = False
            else:
                session = SessionLocal()
                should_close = True
            
            try:
                question_record = DailyQuestion(
                    source=questions_data.get('source', 'Unknown'),
                    category=questions_data.get('category', 'Business'),
                    date=questions_data.get('date', datetime.now().strftime('%Y-%m-%d')),
                    questions_json=questions_data,
                    total_questions=questions_data.get('total_questions', 0)
                )
                
                session.add(question_record)
                session.commit()
                session.refresh(question_record)
                
                logger.info(f"Saved {question_record.total_questions} questions to database")
                return question_record
                
            finally:
                if should_close:
                    session.close()

    def get_questions_by_date(self, date: str) -> List[DailyQuestion]:
        """
        Get questions by date
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            List of DailyQuestion objects
        """
        try:
            if self.db_session:
                session = self.db_session
                should_close = False
            else:
                session = SessionLocal()
                should_close = True
            
            try:
                questions = session.query(DailyQuestion).filter(
                    DailyQuestion.date == date
                ).all()
                
                return questions
            finally:
                if should_close:
                    session.close()
                    
        except Exception as e:
            logger.error(f"Error fetching questions by date: {str(e)}")
            return []

    def get_questions_by_source(self, source: str, limit: int = 100) -> List[DailyQuestion]:
        """
        Get questions by source
        
        Args:
            source: Source name
            limit: Maximum number of results
            
        Returns:
            List of DailyQuestion objects
        """
        try:
            if self.db_session:
                session = self.db_session
                should_close = False
            else:
                session = SessionLocal()
                should_close = True
            
            try:
                questions = session.query(DailyQuestion).filter(
                    DailyQuestion.source == source
                ).order_by(DailyQuestion.created_at.desc()).limit(limit).all()
                
                return questions
            finally:
                if should_close:
                    session.close()
                    
        except Exception as e:
            logger.error(f"Error fetching questions by source: {str(e)}")
            return []

    def get_questions_by_category(self, category: str, limit: int = 100) -> List[DailyQuestion]:
        """
        Get questions by category
        
        Args:
            category: Category name
            limit: Maximum number of results
            
        Returns:
            List of DailyQuestion objects
        """
        try:
            if self.db_session:
                session = self.db_session
                should_close = False
            else:
                session = SessionLocal()
                should_close = True
            
            try:
                questions = session.query(DailyQuestion).filter(
                    DailyQuestion.category == category
                ).order_by(DailyQuestion.created_at.desc()).limit(limit).all()
                
                return questions
            finally:
                if should_close:
                    session.close()
                    
        except Exception as e:
            logger.error(f"Error fetching questions by category: {str(e)}")
            return []

    def get_total_questions_count(self) -> int:
        """Get total count of questions in database"""
        try:
            if self.db_session:
                session = self.db_session
                should_close = False
            else:
                session = SessionLocal()
                should_close = True
            
            try:
                count = session.query(DailyQuestion).count()
                return count
            finally:
                if should_close:
                    session.close()
                    
        except Exception as e:
            logger.error(f"Error counting questions: {str(e)}")
            return 0

    def get_daily_stats(self, date: str) -> Dict:
        """
        Get statistics for a specific date
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            Dictionary with statistics
        """
        try:
            if self.db_session:
                session = self.db_session
                should_close = False
            else:
                session = SessionLocal()
                should_close = True
            
            try:
                questions = session.query(DailyQuestion).filter(
                    DailyQuestion.date == date
                ).all()
                
                total_questions = sum(q.total_questions for q in questions)
                sources = list(set(q.source for q in questions))
                categories = list(set(q.category for q in questions))
                
                return {
                    'date': date,
                    'total_batches': len(questions),
                    'total_questions': total_questions,
                    'sources': sources,
                    'categories': categories
                }
            finally:
                if should_close:
                    session.close()
                    
        except Exception as e:
            logger.error(f"Error getting daily stats: {str(e)}")
            return {}

