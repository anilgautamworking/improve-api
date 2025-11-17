"""Ollama API client wrapper for local LLM inference"""

import os
import requests
from typing import Optional
import logging
import time
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class OllamaClient:
    """Wrapper for Ollama API interactions (local LLM inference)"""

    # Recommended models for MCQ generation with JSON output (in order of preference)
    RECOMMENDED_MODELS = [
        "myaniu/qwen2.5-1m:14b",  # 1M context variant tuned for long-form generation
        "llama3.1:8b",            # Balanced option when resources are limited
        "llama3.1:70b",           # Highest quality, requires beefy hardware
        "mistral",                # Great structured outputs, smaller model
        "qwen2.5:7b",             # Efficient Qwen variant
        "phi3",                   # Small but capable, good for constrained resources
        "llama3:8b",              # Alternative to llama3.1
    ]

    def __init__(self, base_url: str = "http://localhost:11434", 
                 model: str = "myaniu/qwen2.5-1m:14b",
                 temperature: float = 0.7):
        """
        Initialize Ollama client
        
        Args:
            base_url: Ollama API base URL (default: http://localhost:11434)
            model: Model name to use (default: myaniu/qwen2.5-1m:14b)
            temperature: Sampling temperature (0.0 to 2.0)
        """
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        self.temperature = float(os.getenv("OLLAMA_TEMPERATURE", temperature))
        
        # Verify Ollama is running
        if not self._check_ollama_running():
            raise ConnectionError(
                f"Ollama not running at {self.base_url}. "
                "Start Ollama with: ollama serve"
            )
        
        # Verify model is available, pull if needed
        if not self._check_model_available():
            logger.info(f"Model {self.model} not found. Attempting to pull...")
            self._pull_model()
        
        logger.info(f"Ollama client initialized with model: {self.model}")

    def _check_ollama_running(self) -> bool:
        """Check if Ollama service is running"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama connection check failed: {str(e)}")
            return False

    def _check_model_available(self) -> bool:
        """Check if model is available locally"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = [m.get("name", "") for m in response.json().get("models", [])]
                return self.model in models
            return False
        except Exception:
            return False

    def _pull_model(self):
        """Pull model from Ollama registry"""
        try:
            logger.info(f"Pulling model {self.model}... This may take a few minutes.")
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model},
                stream=True,
                timeout=300
            )
            response.raise_for_status()
            logger.info(f"Successfully pulled model {self.model}")
        except Exception as e:
            logger.error(f"Failed to pull model {self.model}: {str(e)}")
            raise

    def generate_completion(self, prompt: str, system_prompt: Optional[str] = None,
                           retry_attempts: int = 3, retry_delay: int = 5) -> Optional[str]:
        """
        Generate completion from Ollama API
        
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
                logger.debug(f"Calling Ollama API (attempt {attempt + 1})")
                
                response = requests.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "options": {
                            "temperature": self.temperature,
                        },
                        "stream": False
                    },
                    timeout=180  # 2 minute timeout
                )
                
                response.raise_for_status()
                result = response.json()
                content = result.get("message", {}).get("content", "")
                
                if not content:
                    raise ValueError("Empty response from Ollama")
                
                logger.debug(f"Successfully generated completion ({len(content)} characters)")
                return content
                
            except requests.exceptions.Timeout:
                logger.warning(f"Ollama request timeout (attempt {attempt + 1})")
                if attempt < retry_attempts - 1:
                    time.sleep(retry_delay)
                else:
                    return None
            except Exception as e:
                logger.error(f"Error calling Ollama API (attempt {attempt + 1}): {str(e)}")
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
        Estimate cost (always 0 for local Ollama, but useful for comparison)
        
        Args:
            prompt: Input prompt
            response_length: Expected response length in characters
            
        Returns:
            Estimated cost (always 0 for local models)
        """
        return 0.0  # Free when running locally

    @classmethod
    def list_recommended_models(cls) -> list:
        """Get list of recommended models for MCQ generation"""
        return cls.RECOMMENDED_MODELS.copy()
