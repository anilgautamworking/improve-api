"""SQLAlchemy database models"""

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
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


class Article(Base):
    """Stores scraped and cleaned article content"""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), nullable=False, unique=True, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(100), nullable=False, index=True)
    category = Column(String(100), nullable=True, index=True)
    published_date = Column(String(10), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('idx_source_category_date', 'source', 'category', 'published_date'),
    )

    def __repr__(self):
        return f"<Article(id={self.id}, title={self.title[:50]}...)>"


class Exam(Base):
    """Stores available exams (JEE, NEET, UPSC, etc.)"""
    __tablename__ = "exams"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(Text, nullable=False, unique=True, index=True)
    category = Column(Text, nullable=True)  # "Engineering", "Medical", "Civil Services"
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    categories = relationship(
        "Category",
        secondary="exam_category",
        back_populates="exams"
    )
    users = relationship("User", back_populates="exam")

    def __repr__(self):
        return f"<Exam(id={self.id}, name={self.name}, category={self.category})>"


class ExamCategory(Base):
    """Junction table for many-to-many relationship between exams and categories"""
    __tablename__ = "exam_category"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('exam_id', 'category_id', name='uq_exam_category'),
        Index('idx_exam_category_exam_id', 'exam_id'),
        Index('idx_exam_category_category_id', 'category_id'),
        Index('idx_exam_category_composite', 'exam_id', 'category_id'),
    )

    def __repr__(self):
        return f"<ExamCategory(exam_id={self.exam_id}, category_id={self.category_id})>"


class Category(Base):
    """Frontend quiz category"""
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(Text, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    exams = relationship(
        "Exam",
        secondary="exam_category",
        back_populates="categories"
    )

    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name})>"


class User(Base):
    """Frontend user account"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    email = Column(Text, nullable=False, unique=True, index=True)
    password_hash = Column(Text, nullable=False)
    role = Column(Text, nullable=False, server_default="user", index=True)
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    exam = relationship("Exam", back_populates="users")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


# Note: Question model is defined in the database via migrations but not in SQLAlchemy models.py.
# It can be added here if/when ORM access is needed. For now, the API uses raw SQL queries for questions.
