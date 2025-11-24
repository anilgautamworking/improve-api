"""Repository for PdfSource."""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from src.database.models import PdfSource


class PdfSourceRepository:
    """CRUD helpers for PdfSource."""

    def __init__(self, db: Session):
        self.db = db

    def get(self, source_id: int) -> Optional[PdfSource]:
        return self.db.query(PdfSource).get(source_id)

    def get_by_local_path(self, local_path: str) -> Optional[PdfSource]:
        return self.db.query(PdfSource).filter(PdfSource.local_path == local_path).first()

    def upsert_local_source(
        self,
        *,
        local_path: str,
        file_name: str,
        zip_name: Optional[str],
        etag_hash: Optional[str],
        subject: Optional[str],
        grade: Optional[str],
        book_title: Optional[str],
        total_pages: Optional[int],
        ocr_used: bool = False,
        status: str = "pending",
        source_type: str = "local_zip",
    ) -> PdfSource:
        """
        Idempotently create/update a local PDF source keyed by local_path.
        """
        pdf = self.get_by_local_path(local_path)
        if pdf:
            pdf.file_name = file_name
            pdf.zip_name = zip_name
            pdf.etag_hash = etag_hash
            pdf.subject = subject
            pdf.grade = grade
            pdf.book_title = book_title
            pdf.total_pages = total_pages
            pdf.ocr_used = ocr_used
            pdf.status = status or pdf.status
            pdf.source_type = source_type or pdf.source_type
        else:
            pdf = PdfSource(
                local_path=local_path,
                file_name=file_name,
                zip_name=zip_name,
                etag_hash=etag_hash,
                subject=subject,
                grade=grade,
                book_title=book_title,
                total_pages=total_pages,
                ocr_used=ocr_used,
                status=status,
                source_type=source_type,
            )
            self.db.add(pdf)

        self.db.commit()
        self.db.refresh(pdf)
        return pdf

    def list_pending(self, limit: int = 100) -> List[PdfSource]:
        return (
            self.db.query(PdfSource)
            .filter(PdfSource.status == "pending")
            .order_by(PdfSource.id.asc())
            .limit(limit)
            .all()
        )

    def update_status(self, source_id: int, status: str, error_reason: Optional[str] = None):
        pdf = self.get(source_id)
        if not pdf:
            return None
        pdf.status = status
        pdf.error_reason = error_reason
        self.db.commit()
        self.db.refresh(pdf)
        return pdf
