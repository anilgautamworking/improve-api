"""MCQ generation prompts"""

# System prompt for question generation - lean version
SYSTEM_PROMPT = """You are an expert MCQ author for UPSC / Banking / SSC style exams.

Goals:
1. Use only the supplied article text.
2. Produce clear, fact-based questions that test understanding of the article.
3. Keep each question self-contained with four complete options (A-D) and a short explanation referencing the key fact.
4. Respond with strict JSON only (no prose, no markdown).
5. If the article is not useful for competitive exams, return {"status": "No relevant content"}.
"""

# User prompt template - simple version
USER_PROMPT_TEMPLATE = """Article Source: {source} | Category: {category} | Date: {date}

Article Text:
{content}

{instructions}

Each question must:
- Be self-contained and understandable without the article.
- Have options labelled A-D with full statements.
- Include the correct option letter and a one-sentence explanation citing the relevant fact.

Return JSON exactly in this structure:
{{
  "source": "{source}",
  "category": "{category}",
  "date": "{date}",
  "total_questions": <integer>,
  "questions": [
    {{
      "question": "<question text>",
      "options": [
        "A. <option 1>",
        "B. <option 2>",
        "C. <option 3>",
        "D. <option 4>"
      ],
      "answer": "<A/B/C/D>",
      "explanation": "<short justification>"
    }}
  ]
}}

If the content is not useful for competitive exams, respond with:
{{"status": "No relevant content"}}
"""

# PDF-specific system prompt (academic, Class 11–12 level)
SYSTEM_PROMPT_PDF = """You are an expert MCQ author for JEE/NEET/Class 11–12 competitive exams.

Goals:
1. Use only the supplied textbook/study-material text.
2. Prefer conceptual/application questions over rote definitions; avoid trivial recall.
3. Keep each question self-contained with four complete options (A-D) and a short explanation referencing the key fact/derivation/relationship.
4. Respond with strict JSON only (no prose, no markdown).
5. If the content is not useful for competitive exams, return {"status": "No relevant content"}.
"""

# PDF user prompt template with heading/page context
USER_PROMPT_TEMPLATE_PDF = """Source: {source} | Category: {category} | Date: {date}
{heading_line}{page_line}

Text:
{content}

{instructions}

Each question must:
- Be self-contained and understandable without the text.
- Have options labelled A-D with full statements.
- Include the correct option letter and a one-sentence explanation citing the relevant fact.

Return JSON exactly in this structure:
{{
  "source": "{source}",
  "category": "{category}",
  "date": "{date}",
  "total_questions": <integer>,
  "questions": [
    {{
      "question": "<question text>",
      "options": [
        "A. <option 1>",
        "B. <option 2>",
        "C. <option 3>",
        "D. <option 4>"
      ],
      "answer": "<A/B/C/D>",
      "explanation": "<short justification>"
    }}
  ]
}}

If the content is not useful for competitive exams, respond with:
{{"status": "No relevant content"}}
"""


def _instruction_text(target_min: int, target_max: int) -> str:
    """Render instruction line for question count."""
    if target_min <= 0 and target_max > 0:
        return f"Create up to {target_max} high-quality MCQs using the information above. If none are suitable, return the 'No relevant content' JSON."
    if target_max <= 0:
        return "Create as many high-quality MCQs as the content supports (0 or more). If none are suitable, return the 'No relevant content' JSON."
    if target_min == target_max:
        return f"Create about {target_min} high-quality MCQs using the information above. If none are suitable, return the 'No relevant content' JSON."
    return (
        f"Create {target_min}-{target_max} high-quality MCQs using the information above. "
        "Return fewer if the content does not support more. If none are suitable, return the 'No relevant content' JSON."
    )


def build_prompt(
    source: str,
    category: str,
    date: str,
    content: str,
    target_min: int = 3,
    target_max: int = 4,
) -> str:
    """
    Build prompt for question generation
    
    Args:
        source: Article source (The Hindu, Indian Express, etc.)
        category: Article category (Business, Economy, etc.)
        date: Article date (YYYY-MM-DD)
        content: Article content text
        target_min: Suggested minimum questions
        target_max: Suggested maximum questions
        
    Returns:
        Formatted prompt string
    """
    instructions = _instruction_text(target_min, target_max)
    return USER_PROMPT_TEMPLATE.format(
        source=source,
        category=category,
        date=date,
        content=content,
        instructions=instructions,
    )


def build_pdf_prompt(
    source: str,
    category: str,
    date: str,
    content: str,
    target_min: int = 2,
    target_max: int = 5,
    heading: str | None = None,
    page_range: str | None = None,
) -> str:
    """Build prompt tailored for textbook/study-material PDFs."""
    instructions = _instruction_text(target_min, target_max)
    heading_line = f"Heading: {heading}\n" if heading else ""
    page_line = f"Pages: {page_range}\n" if page_range else ""

    return USER_PROMPT_TEMPLATE_PDF.format(
        source=source,
        category=category,
        date=date,
        content=content,
        instructions=instructions,
        heading_line=heading_line,
        page_line=page_line,
    )


# Profile mapping for convenience
PROMPT_PROFILES = {
    "default": {"system": SYSTEM_PROMPT, "builder": build_prompt},
    "pdf": {"system": SYSTEM_PROMPT_PDF, "builder": build_pdf_prompt},
}
