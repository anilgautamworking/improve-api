"""Scan local PDF folders and upsert entries into pdf_sources."""

import argparse
import hashlib
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

import pdfplumber

# Ensure project root is on sys.path when run as a script
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config.settings import settings  # noqa: E402
from src.database.db import SessionLocal  # noqa: E402
from src.database.repositories.pdf_source_repository import PdfSourceRepository  # noqa: E402


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def hash_file(path: Path) -> str:
    """Compute sha256 hash for file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_subject_grade_book(base_dir: Path, pdf_path: Path) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Infer subject, grade, book title from path.

    Expected layout: base_dir/<subject>/unzipped/<book_title>/file.pdf
    """
    try:
        rel = pdf_path.relative_to(base_dir)
    except ValueError:
        return None, None, None

    parts = rel.parts
    subject = parts[0] if len(parts) >= 1 else None
    book_title = parts[2] if len(parts) >= 3 else None  # parts[1] should be 'unzipped'
    grade = None
    if book_title:
        lower = book_title.lower()
        if lower.startswith("+1") or lower.startswith("1"):
            grade = "11"
        elif lower.startswith("+2") or lower.startswith("2"):
            grade = "12"
    return subject, grade, book_title


def count_pages(pdf_path: Path) -> Optional[int]:
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            return len(pdf.pages)
    except Exception as exc:
        logger.warning("Failed to count pages for %s: %s", pdf_path, exc)
        return None


def sync_pdfs(base_dir: Path, subject_filter: Optional[str] = None, single_file: Optional[Path] = None, dry_run: bool = False):
    db = SessionLocal()
    repo = PdfSourceRepository(db)

    if single_file:
        pdf_paths = [single_file.resolve()]
    else:
        pattern = "**/unzipped/**/*.pdf"
        pdf_paths = sorted(base_dir.glob(pattern))
        if subject_filter:
            pdf_paths = [p for p in pdf_paths if p.parts and p.parts[0].lower() == subject_filter.lower()]

    logger.info("Found %s PDF files under %s", len(pdf_paths), base_dir)
    created = updated = skipped = 0

    for pdf_path in pdf_paths:
        subject, grade, book_title = detect_subject_grade_book(base_dir, pdf_path)
        file_hash = hash_file(pdf_path)
        total_pages = count_pages(pdf_path)
        zip_name = None  # optional; could be inferred later if needed

        if dry_run:
            logger.info("[dry-run] Would upsert: %s (subject=%s grade=%s book=%s hash=%s pages=%s)",
                        pdf_path, subject, grade, book_title, file_hash[:10], total_pages)
            continue

        existing = repo.get_by_local_path(str(pdf_path))
        if existing and existing.etag_hash == file_hash:
            skipped += 1
            continue

        status = "pending"
        rec = repo.upsert_local_source(
            local_path=str(pdf_path),
            file_name=pdf_path.name,
            zip_name=zip_name,
            etag_hash=file_hash,
            subject=subject,
            grade=grade,
            book_title=book_title,
            total_pages=total_pages,
            ocr_used=False,
            status=status,
            source_type="local_zip",
        )
        if existing:
            updated += 1
            logger.info("Updated pdf_source id=%s for %s", rec.id, pdf_path)
        else:
            created += 1
            logger.info("Created pdf_source id=%s for %s", rec.id, pdf_path)

    logger.info("Sync complete: created=%s updated=%s skipped=%s", created, updated, skipped)
    db.close()


def main():
    parser = argparse.ArgumentParser(description="Sync local PDFs into pdf_sources table.")
    parser.add_argument("--base-dir", default=settings.PDF_BASE_DIR, help="Base directory for PDFs.")
    parser.add_argument("--subject", help="Optional subject filter (folder name).")
    parser.add_argument("--file", help="Optional single PDF file to sync.")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to DB, just log actions.")
    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        raise SystemExit(f"Base directory not found: {base_dir}")

    single_file = Path(args.file).resolve() if args.file else None
    if single_file and not single_file.exists():
        raise SystemExit(f"File not found: {single_file}")

    sync_pdfs(base_dir, subject_filter=args.subject, single_file=single_file, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
