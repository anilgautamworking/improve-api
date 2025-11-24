"""Utilities for PDF text normalization and sizing."""

import re
from typing import Optional


def truncate_at_sentence(text: str, max_chars: int, hard_cap: Optional[int] = None) -> str:
    """
    Truncate near max_chars but prefer to cut on sentence boundaries.

    Args:
        text: input text to truncate
        max_chars: soft limit to aim for
        hard_cap: absolute limit; if not provided uses max_chars
    """
    if max_chars <= 0:
        return text

    if len(text) <= max_chars:
        return text

    cap = hard_cap or max_chars
    if len(text) > cap:
        text = text[:cap]

    # Find the last sentence boundary before the soft limit.
    window = text[:max_chars]
    matches = list(re.finditer(r"[.!?]\s", window))
    if matches:
        cut = matches[-1].end()
        if cut > max_chars * 0.6:  # avoid tiny fragments
            return text[:cut].strip()

    # Fallback to nearest whitespace before the cap.
    last_space = window.rfind(" ")
    if last_space > max_chars * 0.5:
        return text[:last_space].strip()

    return text[:max_chars].strip()


def guess_heading(text: str) -> Optional[str]:
    """Guess a heading from the top of a page/chunk."""
    if not text:
        return None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    first = lines[0]
    if len(first) > 120:
        return None

    first_words = len(first.split())
    score_upper = sum(1 for ch in first if ch.isupper())
    score_alpha = sum(1 for ch in first if ch.isalpha())
    upper_ratio = score_upper / score_alpha if score_alpha else 0

    if "chapter" in first.lower():
        return first
    if first_words <= 8:
        return first
    if upper_ratio > 0.7:
        return first
    return None


def question_signal_density(text: str) -> float:
    """
    Approximate how question-like a chunk is by looking for patterns (Q., ?, numbering).
    Returns a ratio in [0, 1].
    """
    if not text:
        return 0.0

    question_tokens = re.findall(r"(?:\bq[\.:)\]]|\b\d+\)|\?)", text, flags=re.IGNORECASE)
    sentences = re.split(r"[.!?]+", text)
    sentences_count = max(1, len([s for s in sentences if s.strip()]))
    density = min(1.0, len(question_tokens) / sentences_count)
    return density
