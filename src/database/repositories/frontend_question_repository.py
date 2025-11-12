"""
Repository for frontend questions table

Handles inserting questions into the frontend-compatible questions table
alongside the existing daily_questions table.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.database.db import SessionLocal

logger = logging.getLogger(__name__)

# Category mapping from automation backend to frontend categories
CATEGORY_MAPPING = {
    'Business': 'Economy',
    'Economy': 'Economy',
    'Banking': 'Economy',
    'Trade': 'Economy',
    'Current Affairs': 'Current Affairs',
    'Polity': 'India GK',
    'History': 'History',
    'Geography': 'India GK',
    'Science & Technology': 'India GK',
    'Environment': 'India GK',
    'International Relations': 'Current Affairs',
    'General Knowledge': 'India GK',
    'Explained': 'Current Affairs',
}


class FrontendQuestionRepository:
    """Repository for frontend questions table operations"""

    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize repository
        
        Args:
            db_session: Database session (creates new if None)
        """
        self.db_session = db_session
        self._category_cache = None

    def _get_categories(self, session: Session) -> Dict[str, str]:
        """
        Get category name to UUID mapping
        
        Args:
            session: Database session
            
        Returns:
            Dictionary mapping category name to UUID
        """
        if not self._category_cache:
            result = session.execute(text("SELECT id, name FROM categories"))
            self._category_cache = {row[1]: str(row[0]) for row in result}
        
        return self._category_cache

    def _get_difficulty_from_content(self, question_text: str, explanation: str, source: str) -> str:
        """
        Determine difficulty level based on content length and complexity
        
        Args:
            question_text: Question text
            explanation: Explanation text
            source: Article source
            
        Returns:
            'easy', 'medium', or 'hard'
        """
        total_length = len(question_text) + len(explanation)
        
        # Sources like "The Hindu" tend to have more complex questions
        if source in ['The Hindu', 'Indian Express']:
            if total_length > 400:
                return 'hard'
            elif total_length > 250:
                return 'medium'
            else:
                return 'easy'
        else:
            if total_length > 350:
                return 'medium'
            else:
                return 'easy'

    def _get_points_from_difficulty(self, difficulty: str) -> int:
        """
        Get points based on difficulty
        
        Args:
            difficulty: 'easy', 'medium', or 'hard'
            
        Returns:
            10, 15, or 20 points
        """
        points_map = {
            'easy': 10,
            'medium': 15,
            'hard': 20
        }
        return points_map.get(difficulty, 10)

    def save_questions_to_frontend_table(
        self,
        questions_data: Dict,
        check_duplicates: bool = True
    ) -> Dict[str, any]:
        """
        Save questions to frontend questions table
        
        Args:
            questions_data: Question data dictionary with source, category, date, questions
            check_duplicates: If True, skip questions that already exist
            
        Returns:
            Dictionary with statistics
        """
        stats = {
            'inserted': 0,
            'skipped': 0,
            'errors': []
        }
        
        try:
            if self.db_session:
                session = self.db_session
                should_close = False
            else:
                session = SessionLocal()
                should_close = True
            
            try:
                # Get category mapping
                categories = self._get_categories(session)
                
                # Map automation category to frontend category
                automation_category = questions_data.get('category', 'Current Affairs')
                frontend_category = CATEGORY_MAPPING.get(automation_category, 'Current Affairs')
                category_id = categories.get(frontend_category)
                
                if not category_id:
                    error_msg = f"Category not found: {frontend_category}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
                    return stats
                
                source = questions_data.get('source', 'Unknown')
                date = questions_data.get('date', datetime.now().strftime('%Y-%m-%d'))
                questions_list = questions_data.get('questions', [])
                
                for q in questions_list:
                    try:
                        question_text = q.get('question', '').strip()
                        options = q.get('options', [])
                        answer = q.get('answer', '').upper().strip()
                        explanation = q.get('explanation', '').strip()
                        
                        # Validate question
                        if not question_text or len(options) != 4 or answer not in ['A', 'B', 'C', 'D']:
                            logger.warning(f"Invalid question format: {question_text[:50]}...")
                            stats['skipped'] += 1
                            continue
                        
                        # Check for duplicates
                        if check_duplicates:
                            duplicate_check = session.execute(text("""
                                SELECT id FROM questions 
                                WHERE question_text = :question_text
                                LIMIT 1
                            """), {'question_text': question_text})
                            
                            if duplicate_check.fetchone():
                                logger.debug(f"Duplicate question skipped: {question_text[:50]}...")
                                stats['skipped'] += 1
                                continue
                        
                        # Determine difficulty and points
                        difficulty = self._get_difficulty_from_content(question_text, explanation, source)
                        points = self._get_points_from_difficulty(difficulty)
                        
                        # Normalize answer to lowercase
                        correct_answer = answer.lower()
                        
                        # Insert question
                        session.execute(text("""
                            INSERT INTO questions (
                                category_id, question_format, question_text,
                                option_a, option_b, option_c, option_d,
                                correct_answer, explanation, difficulty, points,
                                source, source_date
                            ) VALUES (
                                :category_id, :question_format, :question_text,
                                :option_a, :option_b, :option_c, :option_d,
                                :correct_answer, :explanation, :difficulty, :points,
                                :source, :source_date
                            )
                        """), {
                            'category_id': category_id,
                            'question_format': 'multiple_choice',
                            'question_text': question_text,
                            'option_a': options[0],
                            'option_b': options[1],
                            'option_c': options[2],
                            'option_d': options[3],
                            'correct_answer': correct_answer,
                            'explanation': explanation,
                            'difficulty': difficulty,
                            'points': points,
                            'source': source,
                            'source_date': date
                        })
                        
                        stats['inserted'] += 1
                        
                    except Exception as e:
                        error_msg = f"Error inserting question: {str(e)}"
                        logger.error(error_msg)
                        stats['errors'].append(error_msg)
                        stats['skipped'] += 1
                
                # Only commit if we created our own session (not when using provided session in transaction)
                if should_close:
                    session.commit()
                else:
                    # Flush changes without committing (for transaction context)
                    session.flush()
                    
                logger.info(f"Saved {stats['inserted']} questions to frontend table (skipped: {stats['skipped']})")
                
            finally:
                if should_close:
                    session.close()
                    
        except Exception as e:
            logger.error(f"Error saving questions to frontend table: {str(e)}")
            stats['errors'].append(str(e))
            
        return stats

    def get_recent_questions(self, category_name: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        Get recent questions from frontend table
        
        Args:
            category_name: Optional category name to filter by
            limit: Maximum number of questions to return
            
        Returns:
            List of question dictionaries
        """
        try:
            if self.db_session:
                session = self.db_session
                should_close = False
            else:
                session = SessionLocal()
                should_close = True
            
            try:
                if category_name:
                    query = text("""
                        SELECT q.id, q.question_text, q.difficulty, q.source, q.source_date, c.name as category
                        FROM questions q
                        JOIN categories c ON q.category_id = c.id
                        WHERE c.name = :category_name
                        ORDER BY q.created_at DESC
                        LIMIT :limit
                    """)
                    result = session.execute(query, {'category_name': category_name, 'limit': limit})
                else:
                    query = text("""
                        SELECT q.id, q.question_text, q.difficulty, q.source, q.source_date, c.name as category
                        FROM questions q
                        JOIN categories c ON q.category_id = c.id
                        ORDER BY q.created_at DESC
                        LIMIT :limit
                    """)
                    result = session.execute(query, {'limit': limit})
                
                questions = []
                for row in result:
                    questions.append({
                        'id': str(row[0]),
                        'question_text': row[1],
                        'difficulty': row[2],
                        'source': row[3],
                        'source_date': row[4],
                        'category': row[5]
                    })
                
                return questions
                
            finally:
                if should_close:
                    session.close()
                    
        except Exception as e:
            logger.error(f"Error fetching recent questions: {str(e)}")
            return []

    def get_question_count(self) -> int:
        """Get total count of questions in frontend table"""
        try:
            if self.db_session:
                session = self.db_session
                should_close = False
            else:
                session = SessionLocal()
                should_close = True
            
            try:
                result = session.execute(text("SELECT COUNT(*) FROM questions"))
                return result.scalar()
            finally:
                if should_close:
                    session.close()
                    
        except Exception as e:
            logger.error(f"Error counting questions: {str(e)}")
            return 0

