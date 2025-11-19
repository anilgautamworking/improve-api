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

Create 3-4 high-quality MCQs using the information above. Each question must:
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


def build_prompt(source: str, category: str, date: str, content: str) -> str:
    """
    Build prompt for question generation
    
    Args:
        source: Article source (The Hindu, Indian Express, etc.)
        category: Article category (Business, Economy, etc.)
        date: Article date (YYYY-MM-DD)
        content: Article content text
        
    Returns:
        Formatted prompt string
    """
    return USER_PROMPT_TEMPLATE.format(
        source=source,
        category=category,
        date=date,
        content=content
    )
