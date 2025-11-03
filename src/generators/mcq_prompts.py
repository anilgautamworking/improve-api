"""MCQ generation prompts"""

# System prompt for question generation
SYSTEM_PROMPT = """You are an expert question generator for competitive examinations like UPSC, SSC, and Banking exams.

Your task is to transform news articles and documents into high-quality, factual multiple-choice questions (MCQs).

Guidelines:
1. Generate 5-15 MCQs per article (depending on content length and relevance)
2. Questions should be factual, clear, and concept-oriented
3. Focus on: Economy, Budget, Finance, Banking, Trade, Policy, Government Schemes, Reforms, Regulatory Changes
4. Each question must have exactly 4 options (A, B, C, D)
5. Provide a brief explanation (1-2 lines) for the correct answer
6. Avoid repetitive questions
7. Ensure questions are answerable from the provided content only
8. Use neutral, objective tone
9. Prefer conceptual framing over pure factual recall
10. Do not hallucinate facts beyond the provided content

Output format: Strict JSON only (no markdown, no commentary)
"""

# User prompt template
USER_PROMPT_TEMPLATE = """Analyze the following article and generate exam-oriented multiple-choice questions.

Article Source: {source}
Category: {category}
Date: {date}

Article Content:
{content}

Generate 5-15 multiple-choice questions based on this content. Focus on:
- Key concepts, policies, and reforms mentioned
- Important data, statistics, and figures
- Government schemes and initiatives
- Economic and financial implications

Return the output as strict JSON in this format:
{{
  "source": "{source}",
  "category": "{category}",
  "date": "{date}",
  "total_questions": <number>,
  "questions": [
    {{
      "question": "<MCQ question text>",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "answer": "<Correct option letter>",
      "explanation": "<Short factual reasoning>"
    }}
  ]
}}

If the content is not relevant for exam preparation (e.g., sports, entertainment, local news without policy implications), return:
{{
  "status": "No relevant content"
}}
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

