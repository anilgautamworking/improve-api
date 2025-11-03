"""OpenAI API client wrapper"""

import os
from openai import OpenAI
from typing import Optional, Dict, List
import logging
import time
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Wrapper for OpenAI API interactions"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4", 
                 temperature: float = 0.7, max_tokens: int = 2000):
        """
        Initialize OpenAI client
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use (gpt-4, gpt-3.5-turbo, etc.)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens in response
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", temperature))
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", max_tokens))
        
        logger.info(f"OpenAI client initialized with model: {self.model}")

    def generate_completion(self, prompt: str, system_prompt: Optional[str] = None,
                           retry_attempts: int = 3, retry_delay: int = 5) -> Optional[str]:
        """
        Generate completion from OpenAI API
        
        Args:
            prompt: User prompt text
            system_prompt: System prompt (optional)
            retry_attempts: Number of retry attempts on failure
            retry_delay: Delay between retries in seconds
            
        Returns:
            Generated text or None on failure
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        for attempt in range(retry_attempts):
            try:
                logger.debug(f"Calling OpenAI API (attempt {attempt + 1})")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                
                content = response.choices[0].message.content
                logger.debug(f"Successfully generated completion ({len(content)} characters)")
                
                return content
                
            except Exception as e:
                logger.error(f"Error calling OpenAI API (attempt {attempt + 1}): {str(e)}")
                if attempt < retry_attempts - 1:
                    time.sleep(retry_delay)
                else:
                    return None
        
        return None

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count (rough approximation)
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated token count
        """
        # Rough approximation: 1 token ≈ 4 characters
        return len(text) // 4

    def get_cost_estimate(self, prompt: str, response_length: int = 0) -> float:
        """
        Estimate API cost (rough approximation)
        
        Args:
            prompt: Input prompt
            response_length: Expected response length in characters
            
        Returns:
            Estimated cost in USD
        """
        # Token counts (rough)
        input_tokens = self.estimate_tokens(prompt)
        output_tokens = response_length // 4
        
        # Pricing per 1K tokens (as of 2024, adjust as needed)
        if "gpt-4" in self.model.lower():
            input_cost_per_1k = 0.03  # $0.03 per 1K input tokens
            output_cost_per_1k = 0.06  # $0.06 per 1K output tokens
        else:  # gpt-3.5-turbo
            input_cost_per_1k = 0.0015
            output_cost_per_1k = 0.002
        
        cost = (input_tokens / 1000 * input_cost_per_1k) + (output_tokens / 1000 * output_cost_per_1k)
        return cost

