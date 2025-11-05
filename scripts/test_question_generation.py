#!/usr/bin/env python3
"""
Test script for question generation functionality.
This script tests if the AI provider can generate questions from sample content.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.generators.question_generator import QuestionGenerator
from src.config.settings import settings
from dotenv import load_dotenv

load_dotenv()

# Sample article content for testing
SAMPLE_ARTICLE = """
India's GDP Growth Rate Reaches 7.2% in Q2 2025

The Indian economy showed robust growth in the second quarter of 2025, with GDP expanding 
at 7.2% year-on-year, according to data released by the Ministry of Statistics. This marks 
a significant improvement from the 6.8% growth recorded in Q1.

The surge was driven primarily by strong performance in the manufacturing and services sectors. 
Manufacturing output grew by 8.1%, while services sector expanded by 7.5%. Agriculture, however, 
showed modest growth of 3.2% due to uneven monsoon distribution.

Government expenditure on infrastructure projects, particularly in roads, railways, and digital 
infrastructure, played a crucial role in boosting economic activity. Private consumption also 
picked up, with retail sales growing 6.5% compared to the same quarter last year.

Economists are optimistic about India maintaining this growth momentum, though they caution 
about potential headwinds from global economic uncertainties and inflationary pressures. 
The Reserve Bank of India has maintained its policy rates, signaling confidence in the 
current growth trajectory while remaining watchful of price stability.
"""

def print_success(text):
    print(f"\033[92m✓ {text}\033[0m")

def print_error(text):
    print(f"\033[91m✗ {text}\033[0m")

def print_info(text):
    print(f"\033[94mℹ {text}\033[0m")

def print_header(text):
    print(f"\n\033[95m\033[1m{'='*70}\033[0m")
    print(f"\033[95m\033[1m{text}\033[0m")
    print(f"\033[95m\033[1m{'='*70}\033[0m\n")

def main():
    print_header("Question Generation Test")
    
    # Check AI provider configuration
    ai_provider = settings.AI_PROVIDER.lower()
    print_info(f"Using AI Provider: {ai_provider}")
    
    if ai_provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your_openai_api_key_here":
            print_error("OpenAI API key not configured properly")
            print_info("Please set OPENAI_API_KEY in your .env file")
            return 1
        print_info(f"Model: {settings.OPENAI_MODEL}")
    elif ai_provider == "ollama":
        print_info(f"Ollama URL: {settings.OLLAMA_BASE_URL}")
        print_info(f"Model: {settings.OLLAMA_MODEL}")
    
    # Initialize question generator
    print_info("Initializing question generator...")
    try:
        generator = QuestionGenerator()
        print_success("Question generator initialized successfully")
    except Exception as e:
        print_error(f"Failed to initialize question generator: {str(e)}")
        return 1
    
    # Test question generation
    print_info("\nTesting question generation with sample article...")
    print_info("Sample article topic: India's GDP Growth")
    
    try:
        result = generator.generate_questions(
            source="Test Source",
            category="Economy",
            content=SAMPLE_ARTICLE,
            date="2025-11-05"
        )
        
        if not result:
            print_error("Question generation returned None")
            print_info("This could be due to:")
            print_info("  - API connection issues")
            print_info("  - Content deemed not relevant")
            print_info("  - AI provider errors")
            return 1
        
        if result.get("status") == "No relevant content":
            print_error("AI deemed content not relevant")
            print_info("This is unusual for the test article. Check AI provider configuration.")
            return 1
        
        # Validate result structure
        if "questions" not in result:
            print_error("Result missing 'questions' field")
            return 1
        
        questions = result.get("questions", [])
        total_questions = result.get("total_questions", 0)
        
        if total_questions == 0:
            print_error("No questions were generated")
            return 1
        
        print_success(f"Successfully generated {total_questions} questions!")
        
        # Display questions
        print_header("Generated Questions")
        for i, q in enumerate(questions, 1):
            print(f"\n\033[1mQuestion {i}:\033[0m")
            print(f"  Q: {q.get('question', 'N/A')}")
            print(f"\n  Options:")
            for j, opt in enumerate(q.get('options', []), 1):
                marker = f"  {chr(64+j)}. "
                if chr(64+j) == q.get('answer'):
                    print(f"    \033[92m{marker}{opt}\033[0m ✓")
                else:
                    print(f"    {marker}{opt}")
            print(f"\n  \033[1mCorrect Answer:\033[0m {q.get('answer')}")
            print(f"  \033[1mExplanation:\033[0m {q.get('explanation', 'N/A')}")
        
        print_header("Test Summary")
        print_success("Question generation is working correctly!")
        print_info(f"Source: {result.get('source')}")
        print_info(f"Category: {result.get('category')}")
        print_info(f"Date: {result.get('date')}")
        print_info(f"Total Questions: {result.get('total_questions')}")
        
        return 0
        
    except Exception as e:
        print_error(f"Error during question generation: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\033[93mTest interrupted by user\033[0m")
        sys.exit(1)
    except Exception as e:
        print(f"\n\033[91mUnexpected error: {str(e)}\033[0m")
        import traceback
        traceback.print_exc()
        sys.exit(1)

