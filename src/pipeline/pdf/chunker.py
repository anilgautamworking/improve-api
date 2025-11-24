"""PDF chunker with deterministic page windows and smart truncation."""

import logging
from dataclasses import dataclass
from typing import List, Optional

from src.pipeline.pdf.text_utils import (
    guess_heading,
    question_signal_density,
    truncate_at_sentence,
)

logger = logging.getLogger(__name__)


@dataclass
class PdfPage:
    page_number: int
    text: str


@dataclass
class PdfChunk:
    index: int
    page_start: int
    page_end: int
    heading: Optional[str]
    content: str
    question_density: float
    token_estimate: int


class PdfChunker:
    """
    Deterministic page-window chunker with soft content caps and heading capture.

    - Uses fixed page windows with configurable overlap.
    - Truncates at sentence boundaries near a soft content ceiling to avoid noisy prompts.
    - Records heading and question-signal density for downstream routing/ordering.
    """

    def __init__(
        self,
        chunk_size_pages: int,
        overlap_pages: int,
        max_content_chars: int,
        hard_cap_extra: float = 1.25,
    ):
        if chunk_size_pages <= 0:
            raise ValueError("chunk_size_pages must be > 0")
        if overlap_pages < 0:
            raise ValueError("overlap_pages cannot be negative")
        if overlap_pages >= chunk_size_pages:
            raise ValueError("overlap_pages must be smaller than chunk_size_pages")
        if max_content_chars <= 0:
            raise ValueError("max_content_chars must be > 0")
        if hard_cap_extra < 1.0:
            raise ValueError("hard_cap_extra must be >= 1.0")

        self.chunk_size_pages = chunk_size_pages
        self.overlap_pages = overlap_pages
        self.max_content_chars = max_content_chars
        self.hard_cap = int(max_content_chars * hard_cap_extra)

    def chunk(self, pages: List[PdfPage]) -> List[PdfChunk]:
        """Chunk pages into deterministic windows with smart truncation."""
        if not pages:
            return []

        chunks: List[PdfChunk] = []
        window_step = max(1, self.chunk_size_pages - self.overlap_pages)
        chunk_index = 0
        i = 0

        while i < len(pages):
            window = pages[i : i + self.chunk_size_pages]
            texts = [page.text.strip() for page in window if page.text and page.text.strip()]
            if not texts:
                i += window_step
                continue

            joined = "\n\n".join(texts)
            heading = guess_heading(window[0].text)
            truncated = truncate_at_sentence(joined, self.max_content_chars, self.hard_cap)
            density = question_signal_density(truncated)
            token_estimate = len(truncated) // 4

            chunk = PdfChunk(
                index=chunk_index,
                page_start=window[0].page_number,
                page_end=window[-1].page_number,
                heading=heading,
                content=truncated,
                question_density=density,
                token_estimate=token_estimate,
            )
            chunks.append(chunk)

            chunk_index += 1
            i += window_step

        logger.info(
            "Created %s chunks from %s pages (size=%s, overlap=%s)",
            len(chunks),
            len(pages),
            self.chunk_size_pages,
            self.overlap_pages,
        )
        return chunks
