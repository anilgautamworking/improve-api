"""Repository for PdfChunk."""

from typing import List, Optional
from sqlalchemy.orm import Session
from src.database.models import PdfChunk


class PdfChunkRepository:
    """CRUD helpers for PdfChunk."""

    def __init__(self, db: Session):
        self.db = db

    def get(self, chunk_id: int) -> Optional[PdfChunk]:
        return self.db.query(PdfChunk).get(chunk_id)

    def get_by_source_and_index(self, source_id: int, chunk_index: int) -> Optional[PdfChunk]:
        return (
            self.db.query(PdfChunk)
            .filter(PdfChunk.pdf_source_id == source_id, PdfChunk.chunk_index == chunk_index)
            .first()
        )

    def bulk_insert(self, chunks: List[PdfChunk]) -> List[PdfChunk]:
        if not chunks:
            return []
        self.db.add_all(chunks)
        self.db.commit()
        return chunks

    def upsert_chunk(
        self,
        *,
        pdf_source_id: int,
        chunk_index: int,
        page_start: int,
        page_end: int,
        chapter_title: Optional[str],
        heading: Optional[str],
        content: str,
        token_count: Optional[int] = None,
        status: str = "pending",
        error_reason: Optional[str] = None,
    ) -> PdfChunk:
        chunk = self.get_by_source_and_index(pdf_source_id, chunk_index)
        if chunk:
            chunk.page_start = page_start
            chunk.page_end = page_end
            chunk.chapter_title = chapter_title
            chunk.heading = heading
            chunk.content = content
            chunk.token_count = token_count
            chunk.status = status
            chunk.error_reason = error_reason
        else:
            chunk = PdfChunk(
                pdf_source_id=pdf_source_id,
                chunk_index=chunk_index,
                page_start=page_start,
                page_end=page_end,
                chapter_title=chapter_title,
                heading=heading,
                content=content,
                token_count=token_count,
                status=status,
                error_reason=error_reason,
            )
            self.db.add(chunk)

        self.db.commit()
        self.db.refresh(chunk)
        return chunk

    def list_by_source(self, source_id: int) -> List[PdfChunk]:
        return (
            self.db.query(PdfChunk)
            .filter(PdfChunk.pdf_source_id == source_id)
            .order_by(PdfChunk.chunk_index.asc())
            .all()
        )

    def update_status(self, chunk_id: int, status: str, error_reason: Optional[str] = None):
        chunk = self.get(chunk_id)
        if not chunk:
            return None
        chunk.status = status
        chunk.error_reason = error_reason
        self.db.commit()
        self.db.refresh(chunk)
        return chunk
