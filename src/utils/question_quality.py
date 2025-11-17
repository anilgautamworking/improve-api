"""Heuristics to evaluate and filter generated questions."""

import logging
import re
from typing import Dict, List, Optional

from src.config.settings import settings
from src.utils.filters import CATEGORIES, RELEVANT_KEYWORDS

logger = logging.getLogger(__name__)


class QuestionQualityEvaluator:
    """Scores questions and filters out low quality entries."""

    MIN_QUESTION_WORDS = 8
    MAX_QUESTION_WORDS = 55
    MIN_EXPLANATION_CHARS = 40

    @staticmethod
    def _content_overlap(question_text: str, article_content: str) -> int:
        """Return count of informative tokens shared between question and article."""
        if not question_text or not article_content:
            return 0

        question_tokens = {
            token for token in re.findall(r'\b[a-zA-Z]{4,}\b', question_text.lower())
        }
        article_tokens = {
            token for token in re.findall(r'\b[a-zA-Z]{4,}\b', article_content.lower())
        }
        return len(question_tokens & article_tokens)

    @staticmethod
    def score_question(
        question: Dict,
        category: Optional[str] = None,
        article_content: Optional[str] = None
    ) -> float:
        """Compute a heuristic quality score between 0 and 100."""
        text = str(question.get("question", "")).strip()
        explanation = str(question.get("explanation", "")).strip()
        options = question.get("options", [])
        score = 0.0

        # Question structure
        word_count = len(re.findall(r'\b\w+\b', text))
        if word_count >= QuestionQualityEvaluator.MIN_QUESTION_WORDS:
            score += 20
            if word_count <= QuestionQualityEvaluator.MAX_QUESTION_WORDS:
                score += 10
            else:
                score -= 5
        else:
            score -= 20

        if text.endswith("?"):
            score += 10
        else:
            score -= 5

        # Options sanity
        if isinstance(options, list) and len(options) == 4:
            cleaned_options = [
                str(opt).strip().lower() for opt in options if isinstance(opt, str)
            ]
            if len(cleaned_options) == 4 and all(len(opt) >= 3 for opt in cleaned_options):
                unique_count = len(set(cleaned_options))
                if unique_count == 4:
                    score += 20
                elif unique_count == 3:
                    score += 10
                else:
                    score -= 10
            else:
                score -= 15
        else:
            score -= 15

        # Explanation depth
        if len(explanation) >= QuestionQualityEvaluator.MIN_EXPLANATION_CHARS:
            score += 15
            if any(token in explanation.lower() for token in ['because', 'therefore', 'hence', 'due to']):
                score += 5
        else:
            score -= 10

        # Category alignment
        category_keywords = CATEGORIES.get(category, [])
        category_hits = sum(1 for keyword in category_keywords if keyword in text.lower())
        if category_hits:
            score += min(20, category_hits * 5)
        else:
            score += 5  # neutral bump to avoid harsh penalty for small categories

        # General relevance
        relevance_hits = sum(1 for keyword in RELEVANT_KEYWORDS if keyword in text.lower())
        score += min(10, relevance_hits * 2)

        # Article overlap
        if article_content:
            overlap = QuestionQualityEvaluator._content_overlap(text, article_content)
            if overlap >= 4:
                score += 15
            elif overlap >= 2:
                score += 5
            else:
                score -= 5

        return max(0.0, min(100.0, score))

    @staticmethod
    def filter_questions(
        questions: List[Dict],
        category: Optional[str] = None,
        article_content: Optional[str] = None
    ) -> List[Dict]:
        """Filter questions below configured score threshold and remove duplicates."""
        min_score = settings.QUESTION_QUALITY_MIN_SCORE
        filtered: List[Dict] = []
        seen_questions = set()

        for idx, question in enumerate(questions, start=1):
            normalized = str(question.get("question", "")).strip().lower()
            if not normalized or len(normalized) < 10:
                logger.debug("Dropping question %s: text too short", idx)
                continue
            if normalized in seen_questions:
                logger.debug("Dropping question %s: duplicate detected", idx)
                continue

            score = QuestionQualityEvaluator.score_question(
                question,
                category=category,
                article_content=article_content
            )

            if score >= min_score:
                filtered.append(question)
                seen_questions.add(normalized)
                logger.debug(
                    "Keeping question %s with score %.1f (category=%s)",
                    idx,
                    score,
                    category or "Unknown"
                )
            else:
                logger.debug(
                    "Dropping question %s with low score %.1f (threshold %.1f)",
                    idx,
                    score,
                    min_score
                )

        return filtered
