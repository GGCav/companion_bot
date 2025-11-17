"""
Conversation Manager
Manages conversation context, personality integration, and LLM orchestration
"""

import logging
import time
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import deque

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Manages conversation flow with context, personality, and emotion awareness
    """

    def __init__(
        self,
        config: dict,
        emotion_engine=None,
        user_memory=None
    ):
        """
        Initialize conversation manager

        Args:
            config: Configuration dictionary
            emotion_engine: Optional EmotionEngine instance
            user_memory: Optional UserMemory instance
        """
        self.config = config
        self.emotion_engine = emotion_engine
        self.user_memory = user_memory

        # Initialize LLM client
        self.llm = OllamaClient(config)

        # Conversation context settings
        self.context_window = config.get('memory', {}).get('conversation', {}).get('context_window', 10)
        self.max_history = config.get('memory', {}).get('conversation', {}).get('max_history', 50)

        # Conversation history
        self.conversation_history: deque = deque(maxlen=self.max_history)
        self.current_context: deque = deque(maxlen=self.context_window)

        # Session info
        self.current_user_id: Optional[int] = None
        self.current_user_name: str = "friend"
        self.conversation_start_time = time.time()
        self.message_count = 0

        # Response filtering
        self.max_response_length = 200  # Characters
        self.response_filters = [
            self._ensure_short,
            self._ensure_pet_like,
            self._add_expressiveness
        ]

        logger.info("Conversation manager initialized")

    def process_user_input(
        self,
        user_text: str,
        user_id: Optional[int] = None
    ) -> Tuple[str, Dict]:
        """
        Process user input and generate response

        Args:
            user_text: User's message
            user_id: Optional user ID

        Returns:
            Tuple of (response_text, metadata)
        """
        if not user_text or not user_text.strip():
            logger.warning("Empty user input")
            return "...", {'error': 'empty_input'}

        # Update user info
        if user_id is not None:
            self.current_user_id = user_id
            self._update_user_name()

        # Get current emotion and energy
        emotion = self._get_current_emotion()
        energy = self._get_current_energy()

        # Build context
        context = self._build_context()

        # Generate response from LLM
        start_time = time.time()

        result = self.llm.generate_with_personality(
            user_input=user_text,
            emotion=emotion,
            energy=energy,
            user_name=self.current_user_name
        )

        response_time = time.time() - start_time

        # Extract and filter response
        raw_response = result.get('response', '')
        filtered_response = self._filter_response(raw_response)

        # Update conversation history
        self._add_to_history('user', user_text)
        self._add_to_history('assistant', filtered_response)

        # Update context window
        self._update_context(user_text, filtered_response)

        # Update emotion engine (if available)
        if self.emotion_engine:
            self.emotion_engine.on_voice_interaction()

        # Update stats
        self.message_count += 1

        # Build metadata
        metadata = {
            'emotion': emotion,
            'energy': energy,
            'response_time': response_time,
            'tokens': result.get('tokens', 0),
            'model': result.get('model', 'unknown'),
            'message_count': self.message_count,
            'fallback': result.get('fallback', False)
        }

        logger.info(f"Response generated in {response_time:.2f}s ({metadata['tokens']} tokens)")

        return filtered_response, metadata

    def _build_context(self) -> List[str]:
        """
        Build conversation context for LLM

        Returns:
            List of formatted context messages
        """
        context = []

        for role, message in self.current_context:
            if role == 'user':
                context.append(f"User: {message}")
            else:
                context.append(f"Assistant: {message}")

        return context

    def _update_context(self, user_msg: str, assistant_msg: str):
        """
        Update the sliding context window

        Args:
            user_msg: User's message
            assistant_msg: Assistant's response
        """
        self.current_context.append(('user', user_msg))
        self.current_context.append(('assistant', assistant_msg))

    def _add_to_history(self, role: str, message: str):
        """
        Add message to full conversation history

        Args:
            role: 'user' or 'assistant'
            message: Message content
        """
        self.conversation_history.append({
            'role': role,
            'message': message,
            'timestamp': time.time()
        })

    def _get_current_emotion(self) -> str:
        """
        Get current emotion from emotion engine

        Returns:
            Emotion state string
        """
        if self.emotion_engine:
            try:
                return self.emotion_engine.get_emotion()
            except Exception as e:
                logger.error(f"Error getting emotion: {e}")

        return "happy"  # Default

    def _get_current_energy(self) -> float:
        """
        Get current energy level

        Returns:
            Energy level (0-1)
        """
        if self.emotion_engine:
            try:
                return self.emotion_engine.energy_level
            except Exception as e:
                logger.error(f"Error getting energy: {e}")

        return 0.7  # Default

    def _update_user_name(self):
        """Update current user name from memory"""
        if self.user_memory and self.current_user_id:
            try:
                # Get user profile (if memory module is implemented)
                # For now, use default
                self.current_user_name = "friend"
            except Exception as e:
                logger.error(f"Error getting user name: {e}")

    def _filter_response(self, response: str) -> str:
        """
        Apply filters to ensure response is appropriate

        Args:
            response: Raw LLM response

        Returns:
            Filtered response
        """
        filtered = response

        for filter_func in self.response_filters:
            try:
                filtered = filter_func(filtered)
            except Exception as e:
                logger.error(f"Filter error: {e}")

        return filtered

    def _ensure_short(self, response: str) -> str:
        """
        Ensure response is short (pet-like)

        Args:
            response: Input response

        Returns:
            Shortened response
        """
        if len(response) > self.max_response_length:
            # Truncate at sentence boundary if possible
            sentences = response.split('. ')
            if sentences:
                # Take first 1-2 sentences
                short = '. '.join(sentences[:2])
                if not short.endswith('.'):
                    short += '.'
                return short
            else:
                return response[:self.max_response_length] + '...'

        return response

    def _ensure_pet_like(self, response: str) -> str:
        """
        Ensure response sounds pet-like

        Args:
            response: Input response

        Returns:
            Pet-like response
        """
        # Remove overly formal language
        replacements = {
            'I apologize': 'Sorry!',
            'I understand': 'I get it!',
            'However': 'But',
            'Nevertheless': 'But',
            'Furthermore': 'Also',
        }

        result = response
        for formal, casual in replacements.items():
            result = result.replace(formal, casual)

        return result

    def _add_expressiveness(self, response: str) -> str:
        """
        Add expressiveness to response (optional)

        Args:
            response: Input response

        Returns:
            More expressive response
        """
        # Could add emotive actions based on emotion
        # For now, just return as-is
        return response

    def get_conversation_summary(self) -> str:
        """
        Get summary of conversation

        Returns:
            Summary string
        """
        duration = time.time() - self.conversation_start_time
        duration_min = duration / 60.0

        summary = f"Conversation Summary:\n"
        summary += f"  Duration: {duration_min:.1f} minutes\n"
        summary += f"  Messages: {self.message_count}\n"
        summary += f"  Current emotion: {self._get_current_emotion()}\n"
        summary += f"  User: {self.current_user_name}\n"

        return summary

    def get_conversation_history(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get conversation history

        Args:
            limit: Optional limit on number of messages

        Returns:
            List of message dictionaries
        """
        history = list(self.conversation_history)

        if limit:
            history = history[-limit:]

        return history

    def clear_context(self):
        """Clear conversation context (but keep history)"""
        self.current_context.clear()
        logger.info("Conversation context cleared")

    def clear_history(self):
        """Clear all conversation history"""
        self.conversation_history.clear()
        self.current_context.clear()
        self.message_count = 0
        self.conversation_start_time = time.time()
        logger.info("Conversation history cleared")

    def save_conversation(self, filename: str):
        """
        Save conversation history to file

        Args:
            filename: Output file path
        """
        import json

        try:
            data = {
                'user_name': self.current_user_name,
                'start_time': self.conversation_start_time,
                'message_count': self.message_count,
                'history': list(self.conversation_history)
            }

            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Conversation saved to {filename}")

        except Exception as e:
            logger.error(f"Error saving conversation: {e}")


if __name__ == "__main__":
    # Test conversation manager
    logging.basicConfig(level=logging.INFO)

    import yaml

    # Load config
    config_path = Path(__file__).parent.parent.parent / 'config' / 'settings.yaml'

    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
    else:
        # Mock config
        config = {
            'llm': {
                'provider': 'ollama',
                'ollama': {
                    'base_url': 'http://localhost:11434',
                    'model': 'tinyllama:latest',
                    'timeout': 30
                },
                'generation': {
                    'temperature': 0.8,
                    'max_tokens': 150,
                    'top_p': 0.9
                },
                'personality_prompt': 'You are a cute pet. Current emotion: {emotion}. Energy: {energy}',
                'fallback_responses': ['Woof!', '*happy noises*']
            },
            'memory': {
                'conversation': {
                    'context_window': 10,
                    'max_history': 50
                }
            }
        }

    print("=" * 60)
    print("Conversation Manager Test")
    print("=" * 60)

    # Initialize manager
    print("\nInitializing conversation manager...")
    manager = ConversationManager(config)

    if manager.llm.is_available:
        print("✅ LLM available!\n")

        # Test conversation
        test_messages = [
            "Hello! What's your name?",
            "How are you feeling today?",
            "Do you want to play?",
            "Tell me something fun!"
        ]

        for i, msg in enumerate(test_messages, 1):
            print(f"\n[{i}] User: {msg}")

            response, metadata = manager.process_user_input(msg)

            print(f"    Bot ({metadata['emotion']}): {response}")
            print(f"    [Time: {metadata['response_time']:.2f}s, Tokens: {metadata['tokens']}]")

        # Show summary
        print("\n" + "=" * 60)
        print(manager.get_conversation_summary())

        # Show context
        print("\nCurrent context:")
        for role, msg in manager.current_context:
            print(f"  {role}: {msg[:50]}...")

    else:
        print("❌ LLM not available")
        print("Testing with fallback responses...\n")

        response, metadata = manager.process_user_input("Hello!")
        print(f"User: Hello!")
        print(f"Bot (fallback): {response}")

    print("\n✅ Test complete!")
