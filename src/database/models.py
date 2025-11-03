"""SQLAlchemy database models"""

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database.db import Base


class DailyQuestion(Base):
    """Stores generated MCQ batches"""
    __tablename__ = "daily_questions"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(100), nullable=False, index=True)  # The Hindu, Indian Express, PDF
    category = Column(String(100), nullable=False, index=True)  # Business, Economy, Budget, etc.
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD format
    questions_json = Column(JSON, nullable=False)  # Full question data as JSON
    total_questions = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('idx_source_date', 'source', 'date'),
        Index('idx_category_date', 'category', 'date'),
    )

    def __repr__(self):
        return f"<DailyQuestion(id={self.id}, source={self.source}, date={self.date}, questions={self.total_questions})>"


class ArticleLog(Base):
    """Tracks every article fetched and processed"""
    __tablename__ = "article_logs"

    id = Column(Integer, primary_key=True, index=True)
    source_url = Column(String(500), nullable=False, unique=True, index=True)
    title = Column(String(500), nullable=False)
    category = Column(String(100), nullable=True, index=True)
    source = Column(String(100), nullable=False, index=True)  # The Hindu, Indian Express, PDF
    status = Column(String(50), nullable=False, default="pending", index=True)  # pending, processed, failed, skipped
    processed_at = Column(DateTime(timezone=True), nullable=True)
    error_log = Column(Text, nullable=True)
    questions_generated = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_status_source', 'status', 'source'),
        Index('idx_processed_at', 'processed_at'),
    )

    def __repr__(self):
        return f"<ArticleLog(id={self.id}, url={self.source_url[:50]}..., status={self.status})>"


class MetadataSummary(Base):
    """Daily aggregation stats for admin dashboard"""
    __tablename__ = "metadata_summary"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), nullable=False, unique=True, index=True)  # YYYY-MM-DD format
    feeds_processed = Column(Integer, default=0)
    articles_fetched = Column(Integer, default=0)
    articles_processed = Column(Integer, default=0)
    articles_failed = Column(Integer, default=0)
    articles_skipped = Column(Integer, default=0)
    questions_generated = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    processing_time_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<MetadataSummary(date={self.date}, questions={self.questions_generated}, processed={self.articles_processed})>"

