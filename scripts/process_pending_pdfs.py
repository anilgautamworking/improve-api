"""Process pending PDF sources one at a time."""

import logging
import sys
from pathlib import Path

# Ensure project root on path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database.db import SessionLocal
from src.database.repositories.pdf_source_repository import PdfSourceRepository
from src.database.repositories.pdf_chunk_repository import PdfChunkRepository
from src.pipeline.orchestrator import PipelineOrchestrator


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_all():
    db = SessionLocal()
    source_repo = PdfSourceRepository(db)
    chunk_repo = PdfChunkRepository(db)
    orchestrator = PipelineOrchestrator(db_session=db)

    def _set_chunks_status(source_id: int, status: str, reason: str = None):
        chunks = chunk_repo.list_by_source(source_id)
        for ch in chunks:
            chunk_repo.update_status(ch.id, status, error_reason=reason)

    try:
        while True:
            pending = source_repo.list_pending(limit=1)
            if not pending:
                logger.info("No pending pdf_sources.")
                break

            pdf = pending[0]
            logger.info("Processing pdf_source id=%s path=%s", pdf.id, pdf.local_path)

            try:
                source_repo.update_status(pdf.id, "processing", error_reason=None)
                _set_chunks_status(pdf.id, "pending", reason=None)
                result = orchestrator.process_pdf(
                    pdf_path=pdf.local_path,
                    source="PDF",
                    category=pdf.subject or "PDF",
                    pdf_source_id=pdf.id,
                )
                if result:
                    source_repo.update_status(pdf.id, "done", error_reason=None)
                    logger.info(
                        "Completed pdf_source id=%s with %s questions",
                        pdf.id,
                        result.get("total_questions"),
                    )
                else:
                    source_repo.update_status(pdf.id, "failed", error_reason="No questions or processing returned None")
                    logger.warning("Processing returned no result for pdf_source id=%s", pdf.id)
            except KeyboardInterrupt:
                logger.warning("Processing interrupted for pdf_source id=%s; marking pending for retry", pdf.id)
                source_repo.update_status(pdf.id, "pending", error_reason="interrupted")
                _set_chunks_status(pdf.id, "pending", reason="interrupted")
                break
            except Exception as exc:
                source_repo.update_status(pdf.id, "failed", error_reason=str(exc))
                logger.error("Failed processing pdf_source id=%s: %s", pdf.id, exc)
                # continue to next pending
                continue
    finally:
        db.close()


if __name__ == "__main__":
    process_all()
