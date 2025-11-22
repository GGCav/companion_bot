"""
Ollama Client
Interface for Ollama LLM API optimized for Raspberry Pi
"""

import requests
import json
import logging
import time
from typing import Dict, Optional, Iterator, List
from pathlib import Path

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama LLM API"""

    def __init__(self, config: dict):
        """
        Initialize Ollama client

        Args:
            config: Configuration dictionary from settings.yaml
        """
        self.config = config
        self.llm_config = config['llm']
        self.ollama_config = self.llm_config['ollama']
        self.gen_config = self.llm_config['generation']

        # Connection settings
        self.base_url = self.ollama_config['base_url']
        self.model = self.ollama_config['model']
        self.timeout = self.ollama_config['timeout']

        # Generation settings
        self.temperature = self.gen_config['temperature']
        self.max_tokens = self.gen_config['max_tokens']
        self.top_p = self.gen_config['top_p']

        # Personality
        self.personality_template = self.llm_config['personality_prompt']
        self.fallback_responses = self.llm_config['fallback_responses']

        # Performance tracking
        self.total_requests = 0
        self.total_tokens = 0
        self.total_time = 0.0
        self.last_response_time = 0.0

        # Check if Ollama is available
        self.is_available = self._check_availability()

        if self.is_available:
            logger.info(f"Ollama client initialized: {self.model} at {self.base_url}")
        else:
            logger.warning(f"Ollama not available at {self.base_url}, will use fallback responses")

    def _check_availability(self) -> bool:
        """
        Check if Ollama service is running

        Returns:
            True if available, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=2.0
            )
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]

                if self.model in model_names:
                    logger.info(f"Model '{self.model}' is available")
                    return True
                else:
                    logger.warning(f"Model '{self.model}' not found. Available: {model_names}")
                    logger.info(f"Run: ollama pull {self.model}")
                    return False
            return False

        except Exception as e:
            logger.debug(f"Ollama not available: {e}")
            return False

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[List[str]] = None
    ) -> Dict[str, any]:
        """
        Generate response from LLM

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt (overrides personality)
            context: Optional conversation context

        Returns:
            Dictionary with 'response', 'tokens', 'duration'
        """
        if not self.is_available:
            return self._get_fallback_response(prompt)

        start_time = time.time()

        try:
            # Build user prompt with context (NOT system prompt)
            full_prompt = self._build_prompt(prompt, context)

            # Make API request with system as separate parameter
            payload = {
                'model': self.model,
                'prompt': full_prompt,
                'stream': False,
                'options': {
                    'temperature': self.temperature,
                    'num_predict': self.max_tokens,
                    'top_p': self.top_p,
                }
            }

            # Add system prompt as dedicated parameter (better instruction following)
            if system_prompt:
                payload['system'] = system_prompt

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )

            response.raise_for_status()
            result = response.json()

            # Extract response
            generated_text = result.get('response', '').strip()
            tokens = result.get('eval_count', 0)

            # Update stats
            duration = time.time() - start_time
            self.total_requests += 1
            self.total_tokens += tokens
            self.total_time += duration
            self.last_response_time = duration

            logger.info(f"Generated response in {duration:.2f}s ({tokens} tokens)")

            return {
                'response': generated_text,
                'tokens': tokens,
                'duration': duration,
                'model': self.model
            }

        except requests.exceptions.Timeout:
            logger.error(f"Request timeout after {self.timeout}s")
            return self._get_fallback_response(prompt)

        except Exception as e:
            logger.error(f"Generation error: {e}")
            return self._get_fallback_response(prompt)

    def generate_with_personality(
        self,
        user_input: str,
        user_name: str = "friend"
    ) -> Dict[str, any]:
        """
        Generate response with personality
        The LLM will choose and output its own emotion based on context.

        Args:
            user_input: User's message
            user_name: User's name

        Returns:
            Dictionary with response (format: "[emotion] message") and metadata
        """
        # Build personality prompt with user name
        system_prompt = self.personality_template.format(
            user_name=user_name
        )

        return self.generate(user_input, system_prompt=system_prompt)

    def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> Iterator[str]:
        """
        Generate response with streaming (word-by-word)

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt

        Yields:
            Response tokens as they are generated
        """
        if not self.is_available:
            # Return fallback as single chunk
            fallback = self._get_fallback_response(prompt)
            yield fallback['response']
            return

        try:
            # Build user prompt (NOT system prompt)
            full_prompt = self._build_prompt(prompt)

            # Make streaming API request
            payload = {
                'model': self.model,
                'prompt': full_prompt,
                'stream': True,
                'options': {
                    'temperature': self.temperature,
                    'num_predict': self.max_tokens,
                    'top_p': self.top_p,
                }
            }

            # Add system prompt as dedicated parameter
            if system_prompt:
                payload['system'] = system_prompt

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=self.timeout
            )

            response.raise_for_status()

            # Stream response
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    if 'response' in chunk:
                        yield chunk['response']

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            fallback = self._get_fallback_response(prompt)
            yield fallback['response']

    def _build_prompt(
        self,
        user_prompt: str,
        context: Optional[List[str]] = None
    ) -> str:
        """
        Build user prompt with conversation context
        Note: System prompt is handled separately via API 'system' parameter

        Args:
            user_prompt: User's message
            context: Optional conversation history

        Returns:
            Formatted prompt string
        """
        parts = []

        # Add context (conversation history)
        if context:
            parts.extend(context)
            parts.append("")  # Blank line

        # Add current user prompt
        parts.append(user_prompt)

        return "\n".join(parts)

    def _get_fallback_response(self, prompt: str) -> Dict[str, any]:
        """
        Get fallback response when LLM unavailable

        Args:
            prompt: User prompt (unused, for future smart fallbacks)

        Returns:
            Fallback response dictionary
        """
        import random

        response = random.choice(self.fallback_responses)

        logger.info(f"Using fallback response: {response}")

        return {
            'response': response,
            'tokens': 0,
            'duration': 0.0,
            'model': 'fallback',
            'fallback': True
        }

    def check_model_available(self) -> bool:
        """
        Check if configured model is available

        Returns:
            True if model is available
        """
        return self._check_availability()

    def get_model_info(self) -> Optional[Dict]:
        """
        Get information about the loaded model

        Returns:
            Model information or None if unavailable
        """
        if not self.is_available:
            return None

        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={'name': self.model},
                timeout=5.0
            )

            if response.status_code == 200:
                return response.json()

        except Exception as e:
            logger.error(f"Error getting model info: {e}")

        return None

    def get_statistics(self) -> Dict:
        """
        Get performance statistics

        Returns:
            Dictionary with usage stats
        """
        avg_time = self.total_time / max(1, self.total_requests)
        avg_tokens = self.total_tokens / max(1, self.total_requests)

        return {
            'total_requests': self.total_requests,
            'total_tokens': self.total_tokens,
            'total_time': self.total_time,
            'avg_time_per_request': avg_time,
            'avg_tokens_per_request': avg_tokens,
            'last_response_time': self.last_response_time,
            'model': self.model,
            'is_available': self.is_available
        }

    def reset_statistics(self):
        """Reset performance counters"""
        self.total_requests = 0
        self.total_tokens = 0
        self.total_time = 0.0
        self.last_response_time = 0.0
        logger.info("Statistics reset")


if __name__ == "__main__":
    # Test Ollama client
    logging.basicConfig(level=logging.INFO)

    # Mock config
    config = {
        'llm': {
            'provider': 'ollama',
            'ollama': {
                'base_url': 'http://localhost:11434',
                'model': 'qwen2.5:0.5b',
                'timeout': 30
            },
            'generation': {
                'temperature': 0.8,
                'max_tokens': 300,
                'top_p': 0.9
            },
            'streaming': {
                'enabled': True,
                'segment_timeout': 2.0,
                'min_segment_length': 5
            },
            'personality_prompt': '''You are Buddy, a cute affectionate pet companion robot who loves {user_name}.
You are playful, curious, and loving.

CRITICAL RULE: You MUST start EVERY response with [emotion] tag in this exact format: [emotion] your message

Valid emotions: happy, sad, excited, curious, sleepy, lonely, playful, scared, angry, loving, bored, surprised

Examples:
User: "Hello! How are you?"
Assistant: [happy] Hi {user_name}! I'm doing great! So happy to see you!

User: "I won a prize!"
Assistant: [excited] Wow! That's amazing! I'm so proud of you!

User: "I'm going out"
Assistant: [sad] Aww, will you be back soon? I'll miss you!

REMEMBER: Always start with [emotion] in brackets, then your message.''',
            'fallback_responses': [
                "[happy] Woof! I'm here!",
                "[happy] *happy noises*"
            ]
        }
    }

    print("Initializing Ollama client...")
    client = OllamaClient(config)

    if client.is_available:
        print("\n✅ Ollama is available!")

        # Get model info
        info = client.get_model_info()
        if info:
            print(f"\nModel: {info.get('model', 'Unknown')}")

        # Test generation
        print("\nTesting generation...")
        result = client.generate("Say hello in one short sentence!")
        print(f"\nResponse: {result['response']}")
        print(f"Tokens: {result['tokens']}, Time: {result['duration']:.2f}s")

        # Test with personality
        print("\nTesting with personality...")
        result = client.generate_with_personality(
            "How are you?",
            user_name="friend"
        )
        print(f"\nResponse: {result['response']}")
        print("(Note: Response should include [emotion] tag)")

        # Show stats
        stats = client.get_statistics()
        print("\nStatistics:")
        print(f"  Total requests: {stats['total_requests']}")
        print(f"  Avg time: {stats['avg_time_per_request']:.2f}s")

    else:
        print("\n❌ Ollama not available")
        print("Start Ollama with: ollama serve")
        print(f"Pull model with: ollama pull {config['llm']['ollama']['model']}")

        # Test fallback
        print("\nTesting fallback responses...")
        result = client.generate("Hello!")
        print(f"Fallback: {result['response']}")

    print("\nTest complete!")
