"""MCQ generation prompts"""

# System prompt for question generation - Modern Competitive Exam Style
SYSTEM_PROMPT = """You are an expert question generator for competitive exams (UPSC/SSC/Banking). Generate high-quality, modern MCQs.

CRITICAL REQUIREMENTS:
1. Questions must be SELF-CONTAINED - the question and options should be enough to answer without the article context
2. Generate CONCEPTUAL questions, not just factual recall
3. Use modern question formats:
   - "Which of the following statements is/are correct?"
   - "Which of the following best describes..."
   - "What is the most likely implication of..."
   - "Which option most accurately explains..."
4. Options should be COMPLETE STATEMENTS (not just single words/phrases)
5. Questions should test UNDERSTANDING and APPLICATION, not just memory
6. Focus on: Economic concepts, Policy implications, Cause-effect relationships, Comparative analysis
7. Each question: 4 options (A-D), clear answer, brief explanation
8. Answer format: single letter only (A, B, C, or D)
9. Output: Strict JSON only (no markdown)
"""

# User prompt template - Focus on quality, self-contained questions
USER_PROMPT_TEMPLATE = """Article Context: {source} | Category: {category} | Date: {date}

Article Content:
{content}

Generate 3-5 HIGH-QUALITY MCQ questions that are:
1. SELF-CONTAINED: Question and options provide all necessary context
2. CONCEPTUAL: Test understanding, not just factual recall
3. MODERN FORMAT: Use statement-based questions like:
   - "Which of the following statements is/are correct regarding..."
   - "What is the most significant implication of..."
   - "Which of the following best explains the relationship between..."
   - "Consider the following statements about..."

4. COMPLETE OPTIONS: Each option should be a full statement (not fragments)
5. EXAM-RELEVANT: Focus on concepts useful for competitive exams

Focus areas: Economic implications, Policy analysis, Cause-effect relationships, Comparative understanding, Conceptual clarity.

JSON format:
{{
  "source": "{source}",
  "category": "{category}",
  "date": "{date}",
  "total_questions": <number>,
  "questions": [
    {{
      "question": "<Complete self-contained question text>",
      "options": [
        "A. <Complete statement option 1>",
        "B. <Complete statement option 2>",
        "C. <Complete statement option 3>",
        "D. <Complete statement option 4>"
      ],
      "answer": "<A/B/C/D only>",
      "explanation": "<Brief explanation of why the answer is correct>"
    }}
  ]
}}

If not relevant: {{"status": "No relevant content"}}
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

