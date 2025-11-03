"""Question generator module"""

import json
import logging
from typing import Optional, Dict, List
from datetime import datetime
from src.ai.openai_client import OpenAIClient
from src.generators.mcq_prompts import SYSTEM_PROMPT, build_prompt
from src.utils.content_cleaner import clean_text, extract_relevant_sections

logger = logging.getLogger(__name__)


class QuestionGenerator:
    """Generates MCQs from article content using OpenAI"""

    def __init__(self, openai_client: Optional[OpenAIClient] = None):
        """
        Initialize question generator
        
        Args:
            openai_client: OpenAI client instance (creates new if None)
        """
        self.openai_client = openai_client or OpenAIClient()
        self.min_questions = 5
        self.max_questions = 15

    def generate_questions(self, source: str, category: str, content: str, 
                          date: Optional[str] = None) -> Optional[Dict]:
        """
        Generate MCQs from article content
        
        Args:
            source: Article source (The Hindu, Indian Express, etc.)
            category: Article category (Business, Economy, etc.)
            content: Article content text
            date: Article date (YYYY-MM-DD), defaults to today
            
        Returns:
            Dictionary with questions in JSON format or None on failure
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Clean and filter content
        cleaned_content = clean_text(content)
        relevant_content = extract_relevant_sections(cleaned_content)
        
        if not relevant_content or len(relevant_content.strip()) < 100:
            logger.warning(f"Insufficient content for question generation (source: {source})")
            return {"status": "No relevant content"}
        
        # Build prompt
        prompt = build_prompt(source, category, date, relevant_content)
        
        # Generate questions via OpenAI
        logger.info(f"Generating questions for {source} - {category}")
        response_text = self.openai_client.generate_completion(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT
        )
        
        if not response_text:
            logger.error(f"Failed to generate questions for {source}")
            return None
        
        # Parse JSON response
        try:
            # Clean response text (remove markdown code blocks if present)
            response_text = self._clean_json_response(response_text)
            questions_data = json.loads(response_text)
            
            # Validate response structure
            if questions_data.get("status") == "No relevant content":
                logger.info(f"Content deemed not relevant for {source}")
                return questions_data
            
            validated_data = self._validate_questions(questions_data, source, category, date)
            
            if validated_data:
                logger.info(f"Successfully generated {validated_data.get('total_questions', 0)} questions")
                return validated_data
            else:
                logger.warning(f"Generated questions failed validation")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {str(e)}")
            logger.debug(f"Response text: {response_text[:500]}")
            return None
        except Exception as e:
            logger.error(f"Error processing question generation: {str(e)}")
            return None

    def _clean_json_response(self, response_text: str) -> str:
        """
        Clean JSON response (remove markdown code blocks if present)
        
        Args:
            response_text: Raw response text
            
        Returns:
            Cleaned JSON string
        """
        # Remove markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split('\n')
            # Remove first line (```json or ```)
            if len(lines) > 1:
                lines = lines[1:]
            # Remove last line (```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = '\n'.join(lines)
        
        return response_text.strip()

    def _validate_questions(self, data: Dict, source: str, category: str, date: str) -> Optional[Dict]:
        """
        Validate and normalize question data
        
        Args:
            data: Parsed JSON data
            source: Expected source
            category: Expected category
            date: Expected date
            
        Returns:
            Validated data dictionary or None
        """
        # Check required fields
        if "questions" not in data:
            logger.error("Missing 'questions' field in response")
            return None
        
        questions = data.get("questions", [])
        if not isinstance(questions, list) or len(questions) == 0:
            logger.error("Invalid or empty questions list")
            return None
        
        # Validate each question
        valid_questions = []
        for i, q in enumerate(questions):
            if not isinstance(q, dict):
                logger.warning(f"Skipping invalid question {i+1}: not a dictionary")
                continue
            
            # Check required fields
            required_fields = ["question", "options", "answer", "explanation"]
            missing_fields = [field for field in required_fields if field not in q]
            if missing_fields:
                logger.warning(f"Skipping question {i+1}: missing fields {missing_fields}")
                continue
            
            # Validate options
            options = q.get("options", [])
            if not isinstance(options, list) or len(options) != 4:
                logger.warning(f"Skipping question {i+1}: invalid options (must be list of 4)")
                continue
            
            # Validate answer
            answer = q.get("answer", "").upper().strip()
            if answer not in ["A", "B", "C", "D"]:
                logger.warning(f"Skipping question {i+1}: invalid answer '{answer}'")
                continue
            
            # Normalize question
            valid_question = {
                "question": str(q["question"]).strip(),
                "options": [str(opt).strip() for opt in options],
                "answer": answer,
                "explanation": str(q["explanation"]).strip()
            }
            
            valid_questions.append(valid_question)
        
        if len(valid_questions) < self.min_questions:
            logger.warning(f"Generated only {len(valid_questions)} questions, minimum is {self.min_questions}")
            # Still return if we have some questions
            if len(valid_questions) == 0:
                return None
        
        # Limit to max questions
        if len(valid_questions) > self.max_questions:
            valid_questions = valid_questions[:self.max_questions]
        
        # Build final response
        result = {
            "source": source,
            "category": category,
            "date": date,
            "total_questions": len(valid_questions),
            "questions": valid_questions
        }
        
        return result

    def check_duplicate_questions(self, new_questions: List[Dict], existing_questions: List[Dict]) -> List[Dict]:
        """
        Filter out duplicate questions by comparing question text
        
        Args:
            new_questions: Newly generated questions
            existing_questions: Existing questions to check against
            
        Returns:
            Filtered list of unique questions
        """
        existing_texts = {q.get("question", "").lower().strip() for q in existing_questions}
        
        unique_questions = []
        for q in new_questions:
            question_text = q.get("question", "").lower().strip()
            if question_text not in existing_texts:
                unique_questions.append(q)
                existing_texts.add(question_text)
            else:
                logger.debug(f"Filtered duplicate question: {q.get('question', '')[:50]}...")
        
        return unique_questions

