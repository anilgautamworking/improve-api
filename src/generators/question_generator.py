"""Question generator module"""

import json
import logging
import re
from typing import Optional, Dict, List, Union
from datetime import datetime
from src.ai.openai_client import OpenAIClient
from src.ai.ollama_client import OllamaClient
from src.generators.mcq_prompts import SYSTEM_PROMPT, build_prompt
from src.utils.content_cleaner import clean_text, extract_relevant_sections

logger = logging.getLogger(__name__)


class QuestionGenerator:
    """Generates MCQs from article content using OpenAI or Ollama"""

    def __init__(self, client: Optional[Union[OpenAIClient, OllamaClient]] = None):
        """
        Initialize question generator
        
        Args:
            client: AI client instance (OpenAI or Ollama, creates new if None)
                   If None, uses AI_PROVIDER from settings to determine which to use
        """
        from src.config.settings import settings
        
        if client:
            self.client = client
        elif settings.AI_PROVIDER == "ollama":
            try:
                self.client = OllamaClient(
                    base_url=settings.OLLAMA_BASE_URL,
                    model=settings.OLLAMA_MODEL,
                    temperature=settings.OLLAMA_TEMPERATURE
                )
                logger.info(f"Using Ollama with model: {settings.OLLAMA_MODEL}")
            except Exception as e:
                logger.error(f"Failed to initialize Ollama: {e}")
                raise ValueError(
                    f"Cannot initialize Ollama. Check that Ollama is running and model '{settings.OLLAMA_MODEL}' is available. "
                    f"Start Ollama with: ollama serve, then pull model: ollama pull {settings.OLLAMA_MODEL}"
                )
        else:  # Default to OpenAI
            self.client = OpenAIClient(
                model=settings.OPENAI_MODEL,
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS
            )
            logger.info(f"Using OpenAI with model: {settings.OPENAI_MODEL}")
        
        self.min_questions = settings.QUESTION_COUNT_MIN
        self.max_questions = settings.QUESTION_COUNT_MAX  # Per article
        self.max_content_length = settings.ARTICLE_CONTEXT_MAX_CHARS

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
        
        # Truncate content to save tokens (keep first N characters)
        if self.max_content_length > 0 and len(relevant_content) > self.max_content_length:
            relevant_content = relevant_content[:self.max_content_length]
            logger.debug(
                "Truncated content from %s to %s characters",
                len(content),
                len(relevant_content),
            )
        
        # Build prompt
        prompt = build_prompt(source, category, date, relevant_content)
        
        # Generate questions via AI client (OpenAI or Ollama)
        logger.info(f"Generating questions for {source} - {category}")
        response_text = self.client.generate_completion(
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

    @staticmethod
    def _clean_option_text(option: Union[str, int]) -> str:
        """
        Remove leading option labels like 'A.' or 'B)' to keep UI clean.
        """
        text = str(option).strip()
        return re.sub(r"^[A-Da-d]\s*[\.\)\-:]\s*", "", text, count=1).strip()

    @staticmethod
    def _normalize_difficulty(raw_value: Optional[str]) -> str:
        """
        Normalize difficulty labels to easy/medium/hard.
        """
        if not raw_value:
            return "medium"
        value = str(raw_value).strip().lower()
        mapping = {
            "e": "easy",
            "1": "easy",
            "easy": "easy",
            "beginner": "easy",
            "m": "medium",
            "2": "medium",
            "medium": "medium",
            "moderate": "medium",
            "h": "hard",
            "3": "hard",
            "hard": "hard",
            "difficult": "hard",
        }
        return mapping.get(value, "medium")

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
            
            # Validate answer - extract letter if format is "C. TEXT" or just "C"
            answer_raw = q.get("answer", "").upper().strip()
            # Extract first letter if answer contains option text (e.g., "C. WAYMO" -> "C")
            if answer_raw.startswith(("A.", "B.", "C.", "D.")):
                answer = answer_raw[0]
            elif answer_raw.startswith(("A ", "B ", "C ", "D ")):
                answer = answer_raw[0]
            else:
                # Try to extract just the letter
                answer = answer_raw[0] if answer_raw and answer_raw[0] in ["A", "B", "C", "D"] else answer_raw
            
            if answer not in ["A", "B", "C", "D"]:
                logger.warning(f"Skipping question {i+1}: invalid answer '{answer_raw}' (extracted: '{answer}')")
                continue
            
            normalized_options = [self._clean_option_text(opt) for opt in options]
            if any(not opt for opt in normalized_options):
                logger.warning(f"Skipping question {i+1}: empty option after normalization")
                continue

            difficulty = self._normalize_difficulty(q.get("difficulty"))
            
            # Normalize question
            valid_question = {
                "question": str(q["question"]).strip(),
                "options": normalized_options,
                "answer": answer,
                "difficulty": difficulty,
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
