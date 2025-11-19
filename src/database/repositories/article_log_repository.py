"""Repository for article logs."""

from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.database.models import ArticleLog


class ArticleLogRepository:
    """Handles CRUD operations for ArticleLog entries."""

    def __init__(self, db: Session):
        self.db = db

    def ensure_log(
        self,
        url: str,
        title: Optional[str] = None,
        source: Optional[str] = None,
        category: Optional[str] = None,
    ) -> ArticleLog:
        """Create log entry if missing."""
        log = self.db.query(ArticleLog).filter(ArticleLog.source_url == url).first()
        if log:
            return log

        log = ArticleLog(
            source_url=url,
            title=title or "",
            source=source or "Unknown",
            category=category,
        )
        self.db.add(log)
        self.db.flush()
        return log

    def get_status_map(self, urls: List[str]) -> Dict[str, str]:
        """Return status for each URL."""
        if not urls:
            return {}
        rows = (
            self.db.query(ArticleLog.source_url, ArticleLog.status)
            .filter(ArticleLog.source_url.in_(urls))
            .all()
        )
        return {url: status for url, status in rows}

    def get_pending_urls(self) -> List[str]:
        """Return URLs that still need question generation."""
        rows = (
            self.db.query(ArticleLog.source_url)
            .filter(ArticleLog.status == "pending")
            .order_by(ArticleLog.created_at.asc())
            .all()
        )
        return [row[0] for row in rows]

    def mark_processed(self, url: str, questions_count: int):
        """Mark article as processed."""
        log = self.db.query(ArticleLog).filter(ArticleLog.source_url == url).first()
        if not log:
            return
        log.status = "processed"
        log.processed_at = datetime.utcnow()
        log.questions_generated = questions_count
        log.error_log = None
        self.db.flush()

    def mark_failed(self, url: str, error: str):
        """Mark article as failed."""
        log = self.db.query(ArticleLog).filter(ArticleLog.source_url == url).first()
        if not log:
            return
        log.status = "failed"
        log.processed_at = datetime.utcnow()
        log.error_log = error[:1000]
        self.db.flush()

    def mark_skipped(self, url: str):
        """Mark article as skipped (no questions generated)."""
        log = self.db.query(ArticleLog).filter(ArticleLog.source_url == url).first()
        if not log:
            return
        log.status = "skipped"
        log.processed_at = datetime.utcnow()
        self.db.flush()
