"""Repository for the Article model"""

from sqlalchemy.orm import Session
from typing import List, Optional
from src.database.models import Article

class ArticleRepository:
    """Repository for database operations on the Article model."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_url(self, url: str) -> Optional[Article]:
        """Get an article by its URL."""
        return self.db.query(Article).filter(Article.url == url).first()

    def create(self, article_data: dict) -> Article:
        """Create a new article."""
        article = Article(**article_data)
        self.db.add(article)
        self.db.commit()
        self.db.refresh(article)
        return article

    def bulk_create(self, articles_data: List[dict]) -> List[Article]:
        """Create multiple articles in a single transaction."""
        articles = [Article(**data) for data in articles_data]
        self.db.add_all(articles)
        self.db.commit()
        return articles

    def get_articles_for_today(self) -> List[Article]:
        """Get all articles published today."""
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        return self.db.query(Article).filter(Article.published_date == today).all()
