"""
Conversation Manager
Manages conversation context, personality integration, and LLM orchestration
"""

import logging
import time
import sys
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Iterator
from collections import deque

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class StreamingEmotionParser:
    """
    Parses emotion tags from streaming LLM token stream
    Emits (emotion, text) segments when complete sentences are detected
    """

    def __init__(self, valid_emotions: set, segment_timeout: float = 2.0, min_segment_length: int = 5):
        """
        Initialize streaming emotion parser

        Args:
            valid_emotions: Set of valid emotion strings
            segment_timeout: Seconds before forcing segment emit without sentence boundary
            min_segment_length: Minimum characters before emitting a segment
        """
        self.valid_emotions = valid_emotions
        self.segment_timeout = segment_timeout
        self.min_segment_length = min_segment_length
        self.reset()

    def reset(self):
        """Reset parser state"""
        self.state = "ACCUMULATING"  # ACCUMULATING, TAG_FOUND, SEGMENT_READY
        self.buffer = ""  # Accumulates tokens
        self.current_emotion = None  # Current emotion tag
        self.current_text = ""  # Text after emotion tag
        self.last_emit_time = time.time()  # For timeout tracking
        logger.debug("StreamingEmotionParser reset")

    def add_token(self, token: str) -> List[Tuple[str, str]]:
        """
        Add streaming token to parser

        Args:
            token: Single token from LLM stream

        Returns:
            List of (emotion, text) tuples ready to be spoken (may be empty)
        """
        segments = []
        self.buffer += token

        # State: Looking for emotion tag
        if self.state == "ACCUMULATING":
            # Check for complete emotion tag pattern: [word]
            tag_match = re.search(r'\[(\w+)\]', self.buffer)
            if tag_match:
                emotion = tag_match.group(1).lower()

                # Validate emotion
                if emotion in self.valid_emotions:
                    self.current_emotion = emotion
                    self.state = "TAG_FOUND"

                    # Extract text after tag
                    text_after_tag = self.buffer[tag_match.end():].lstrip()
                    self.current_text = text_after_tag
                    self.buffer = ""
                    self.last_emit_time = time.time()

                    logger.debug(f"Emotion tag found: [{emotion}]")
                else:
                    # Invalid emotion, use default and keep text
                    logger.warning(f"Invalid emotion '{emotion}', using 'happy'")
                    self.current_emotion = 'happy'
                    self.state = "TAG_FOUND"
                    text_after_tag = self.buffer[tag_match.end():].lstrip()
                    self.current_text = text_after_tag
                    self.buffer = ""
                    self.last_emit_time = time.time()

        # State: Accumulating text after tag
        elif self.state == "TAG_FOUND":
            self.current_text += token

            # Check if segment is ready to emit
            if self._is_segment_boundary():
                # Emit segment
                segment_text = self._prepare_segment_text()
                if segment_text:
                    segments.append((self.current_emotion, segment_text))
                    logger.debug(f"Segment ready: ({self.current_emotion}) {segment_text[:30]}...")

                # Reset to look for next emotion tag
                self.state = "ACCUMULATING"
                self.buffer = ""
                self.current_text = ""
                self.current_emotion = None
                self.last_emit_time = time.time()

        return segments

    def _is_segment_boundary(self) -> bool:
        """
        Determine if current text forms a complete segment ready to emit

        Returns:
            True if segment is ready
        """
        # Check for sentence boundary (. ! ? followed by space or end)
        if re.search(r'[.!?]\s*$', self.current_text):
            return True

        # Check for timeout (force emit if stuck for too long)
        time_since_last_emit = time.time() - self.last_emit_time
        if time_since_last_emit > self.segment_timeout and len(self.current_text) >= self.min_segment_length:
            logger.debug(f"Segment timeout reached ({time_since_last_emit:.1f}s), forcing emit")
            return True

        # Check if next emotion tag is starting (look for [ in recent text)
        # If we see a '[' near the end, might be start of new tag
        if '[' in self.current_text:
            # Split by '[' and check if the last part is very short (< 3 chars)
            # This suggests a new tag is starting
            parts = self.current_text.split('[')
            if len(parts) > 1 and len(parts[-1]) < 3:
                # Likely start of new tag, emit current segment
                # Remove the '[' and partial tag from current text
                self.current_text = '['.join(parts[:-1])
                if len(self.current_text) >= self.min_segment_length:
                    logger.debug("New emotion tag detected, emitting previous segment")
                    # Save the partial tag for next iteration
                    self.buffer = '[' + parts[-1]
                    return True

        return False

    def _prepare_segment_text(self) -> str:
        """
        Prepare segment text for emission (clean up formatting)

        Returns:
            Cleaned segment text
        """
        text = self.current_text.strip()

        # Remove any trailing '[' if present (start of next tag)
        if text.endswith('['):
            text = text[:-1].strip()

        return text

    def flush(self) -> Optional[Tuple[str, str]]:
        """
        Emit any remaining buffered content at end of stream

        Returns:
            (emotion, text) tuple if content available, None otherwise
        """
        # Check if we have text waiting in TAG_FOUND state
        if self.state == "TAG_FOUND" and self.current_text.strip():
            emotion = self.current_emotion or 'happy'
            text = self._prepare_segment_text()
            logger.debug(f"Flushing final segment: ({emotion}) {text[:30]}...")
            return (emotion, text)

        # Check if we have text in buffer (ACCUMULATING state)
        elif self.buffer.strip():
            # No emotion tag found, use default
            logger.debug(f"Flushing buffer with default emotion: {self.buffer[:30]}...")
            return ('happy', self.buffer.strip())

        return None


class ConversationManager:
    """
    Manages conversation flow with context, personality, and emotion awareness
    """

    def __init__(
        self,
        config: dict,
        emotion_engine=None,
        user_memory=None,
        conversation_history=None
    ):
        """
        Initialize conversation manager

        Args:
            config: Configuration dictionary
            emotion_engine: Optional EmotionEngine instance
            user_memory: Optional UserMemory instance
            conversation_history: Optional ConversationHistory instance
        """
        self.config = config
        self.emotion_engine = emotion_engine
        self.user_memory = user_memory
        self.conversation_history_db = conversation_history

        # Initialize LLM client
        self.llm = OllamaClient(config)

        # Conversation context settings
        self.context_window = config.get('memory', {}).get('conversation', {}).get('context_window', 10)
        self.max_history = config.get('memory', {}).get('conversation', {}).get('max_history', 50)

        # Conversation history (in-memory)
        self.conversation_history: deque = deque(maxlen=self.max_history)
        self.current_context: deque = deque(maxlen=self.context_window)

        # Session info
        self.current_user_id: Optional[int] = None
        self.current_user_name: str = "friend"
        self.conversation_start_time = time.time()
        self.message_count = 0
        self.session_id = self._generate_session_id()

        # Response filtering
        self.max_response_length = 200  # Characters
        self.response_filters = [
            self._ensure_short,
            self._ensure_pet_like,
            self._add_expressiveness
        ]

        # Valid emotions (from settings.yaml)
        self.valid_emotions = {
            'happy', 'sad', 'excited', 'curious', 'sleepy',
            'lonely', 'playful', 'scared', 'angry', 'loving',
            'bored', 'surprised'
        }

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

        # Generate response from LLM (LLM will choose emotion)
        start_time = time.time()

        # Format conversation context for LLM
        formatted_context = self._format_context_for_llm()

        result = self.llm.generate_with_personality(
            user_input=user_text,
            user_name=self.current_user_name,
            context=formatted_context
        )

        response_time = time.time() - start_time

        # Extract response and parse ALL emotion segments
        raw_response = result.get('response', '')
        emotion_segments = self._parse_emotion_segments(raw_response)

        # Get final emotion (last in sequence)
        final_emotion = emotion_segments[-1][0] if emotion_segments else 'happy'

        # Filter each segment's text, then recombine with emotions
        filtered_segments = []
        for emotion, text in emotion_segments:
            filtered_text = self._filter_response(text)
            filtered_segments.append((emotion, filtered_text))

        # Combined filtered text for history
        filtered_response = ' '.join(text for _, text in filtered_segments)

        # Update conversation history (save to database with metadata)
        self._add_to_history('user', user_text)
        self._add_to_history(
            'assistant',
            filtered_response,
            emotion=final_emotion,
            tokens=result.get('tokens', 0)
        )

        # Update context window
        self._update_context(user_text, filtered_response)

        # Update emotion engine with emotion sequence
        if self.emotion_engine:
            try:
                # Extract just the emotions in sequence
                emotion_sequence = [emotion for emotion, _ in emotion_segments]

                # Use process_emotion_sequence if available (new method)
                if hasattr(self.emotion_engine, 'process_emotion_sequence'):
                    self.emotion_engine.process_emotion_sequence(emotion_sequence)
                else:
                    # Fallback: use final emotion
                    self.emotion_engine.set_emotion_from_llm(final_emotion)
            except Exception as e:
                logger.warning(f"Error updating emotion engine: {e}")
                # Ultimate fallback
                if hasattr(self.emotion_engine, 'on_voice_interaction'):
                    self.emotion_engine.on_voice_interaction()

        # Update stats
        self.message_count += 1

        # Get current energy for metadata (emotion is now from LLM)
        current_energy = self._get_current_energy()

        # Build metadata
        metadata = {
            'emotion': final_emotion,  # Final emotion from LLM sequence
            'emotion_segments': filtered_segments,  # All emotion segments for TTS
            'energy': current_energy,
            'response_time': response_time,
            'tokens': result.get('tokens', 0),
            'model': result.get('model', 'unknown'),
            'message_count': self.message_count,
            'fallback': result.get('fallback', False)
        }

        logger.info(f"Response generated in {response_time:.2f}s ({metadata['tokens']} tokens, {len(emotion_segments)} emotion segment(s), final: {final_emotion})")

        return filtered_response, metadata

    def stream_generate_with_personality(
        self,
        user_text: str,
        user_id: Optional[int] = None
    ) -> Iterator[Tuple[str, str]]:
        """
        Stream response generation with emotion parsing
        Yields (emotion, text) tuples as segments become ready

        This enables faster perceived response time by speaking as soon as
        the first complete sentence is generated, rather than waiting for
        the entire response.

        Args:
            user_text: User's message
            user_id: Optional user ID

        Yields:
            (emotion, text) tuples for each complete segment
        """
        if not user_text or not user_text.strip():
            logger.warning("Empty user input for streaming")
            yield ('happy', '...')
            return

        # Update user info
        if user_id is not None:
            self.current_user_id = user_id
            self._update_user_name()

        # Build system prompt for personality
        system_prompt = self.llm.personality_template.format(
            user_name=self.current_user_name
        )

        # Initialize streaming parser
        streaming_config = self.config.get('llm', {}).get('streaming', {})
        segment_timeout = streaming_config.get('segment_timeout', 2.0)
        min_segment_length = streaming_config.get('min_segment_length', 5)

        parser = StreamingEmotionParser(
            self.valid_emotions,
            segment_timeout=segment_timeout,
            min_segment_length=min_segment_length
        )

        logger.info("Starting streaming generation...")

        # Format conversation context for LLM
        formatted_context = self._format_context_for_llm()

        # Track segments for history and emotion engine
        all_segments = []
        segment_count = 0

        try:
            # Stream tokens from LLM
            for token in self.llm.stream_generate(user_text, system_prompt=system_prompt, context=formatted_context):
                # Parse token and check for complete segments
                segments = parser.add_token(token)

                # Yield any ready segments
                for emotion, text in segments:
                    # Filter the text
                    filtered_text = self._filter_response(text)

                    if filtered_text:
                        segment_count += 1
                        all_segments.append((emotion, filtered_text))
                        logger.info(f"Streaming segment {segment_count}: ({emotion}) {filtered_text[:40]}...")
                        yield (emotion, filtered_text)

            # Flush any remaining content
            final_segment = parser.flush()
            if final_segment:
                emotion, text = final_segment
                filtered_text = self._filter_response(text)

                if filtered_text:
                    segment_count += 1
                    all_segments.append((emotion, filtered_text))
                    logger.info(f"Streaming final segment: ({emotion}) {filtered_text[:40]}...")
                    yield (emotion, filtered_text)

            # Update conversation history with complete response
            combined_text = ' '.join(text for _, text in all_segments)
            self._add_to_history('user', user_text)
            self._add_to_history('assistant', combined_text)

            # Update context window
            self._update_context(user_text, combined_text)

            # Update emotion engine with emotion sequence
            if self.emotion_engine and all_segments:
                try:
                    emotion_sequence = [emotion for emotion, _ in all_segments]
                    if hasattr(self.emotion_engine, 'process_emotion_sequence'):
                        self.emotion_engine.process_emotion_sequence(emotion_sequence)
                    else:
                        # Fallback: use final emotion
                        final_emotion = all_segments[-1][0]
                        self.emotion_engine.set_emotion_from_llm(final_emotion)
                except Exception as e:
                    logger.warning(f"Error updating emotion engine: {e}")

            # Update stats
            self.message_count += 1

            logger.info(f"Streaming complete: {segment_count} segments generated")

        except Exception as e:
            logger.error(f"Error in streaming generation: {e}", exc_info=True)
            # Yield a fallback response
            yield ('happy', "Sorry, I had trouble with that.")

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

    def _add_to_history(self, role: str, message: str, emotion: str = None, tokens: int = 0):
        """
        Add message to full conversation history (in-memory and database)

        Args:
            role: 'user' or 'assistant'
            message: Message content
            emotion: Optional emotion (for assistant messages)
            tokens: Optional token count (for assistant messages)
        """
        # Add to in-memory history
        self.conversation_history.append({
            'role': role,
            'message': message,
            'emotion': emotion,
            'tokens': tokens,
            'timestamp': time.time()
        })

        # Save to database if available
        if self.conversation_history_db:
            try:
                self.conversation_history_db.save_message(
                    user_id=self.current_user_id,
                    session_id=self.session_id,
                    role=role,
                    message=message,
                    emotion=emotion,
                    tokens=tokens
                )
            except Exception as e:
                logger.warning(f"Failed to save message to database: {e}")

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

    def _format_context_for_llm(self) -> Optional[List[str]]:
        """
        Format conversation context for LLM

        Returns:
            Formatted context as list of strings, or None if empty
        """
        if not self.current_context:
            return None

        # Format each exchange as "User: ...\nAssistant: ..."
        formatted = []
        for role, message in self.current_context:
            if role == 'user':
                formatted.append(f"User: {message}")
            else:
                formatted.append(f"Assistant: {message}")

        return formatted

    def _update_user_name(self):
        """Update current user name from memory"""
        if self.user_memory and self.current_user_id:
            try:
                user_profile = self.user_memory.get_user_by_id(self.current_user_id)
                if user_profile:
                    self.current_user_name = user_profile['name']
                    logger.info(f"Loaded user profile: {self.current_user_name} (ID: {self.current_user_id})")
                else:
                    self.current_user_name = "friend"
            except Exception as e:
                logger.error(f"Error getting user name: {e}")
                self.current_user_name = "friend"

    def _generate_session_id(self) -> str:
        """
        Generate unique session ID

        Returns:
            Session ID string
        """
        import uuid
        return str(uuid.uuid4())

    def _parse_emotion_segments(self, response: str) -> List[Tuple[str, str]]:
        """
        Parse all emotion tags from LLM response and split into segments

        Supports multiple emotions throughout the response:
        "[excited] Hello! [curious] What's that?"
        → [("excited", "Hello!"), ("curious", "What's that?")]

        Args:
            response: Raw LLM response with emotion tag(s)

        Returns:
            List of (emotion, text) tuples for each segment
        """
        response = response.strip()

        # Pattern to find all [emotion] tags and capture text between them
        # Matches: [word] followed by text until next [word] or end
        pattern = r'\[(\w+)\]\s*([^\[]+)'
        matches = re.findall(pattern, response)

        if not matches:
            # No emotion tags found - return entire response with default emotion
            logger.warning("No emotion tags found in response, using default 'happy'")
            return [('happy', response)]

        segments = []
        for emotion_raw, text in matches:
            emotion = emotion_raw.lower().strip()
            text = text.strip()

            # Skip empty segments
            if not text:
                continue

            # Validate emotion
            if emotion not in self.valid_emotions:
                logger.warning(f"Invalid emotion '{emotion}', using 'happy' for this segment")
                emotion = 'happy'

            segments.append((emotion, text))

        if not segments:
            # All segments were empty - fallback
            logger.warning("All emotion segments were empty, using default")
            return [('happy', response)]

        logger.debug(f"Parsed {len(segments)} emotion segment(s)")
        return segments

    def _parse_emotion(self, response: str) -> Tuple[str, str]:
        """
        Legacy method for backward compatibility
        Parses first emotion and returns combined message

        Args:
            response: Raw LLM response with emotion tag(s)

        Returns:
            Tuple of (first_emotion, message_without_tags)
        """
        segments = self._parse_emotion_segments(response)

        if not segments:
            return 'happy', response

        # Get first emotion
        first_emotion = segments[0][0]

        # Combine all text segments (strip all emotion tags)
        combined_text = ' '.join(text for _, text in segments)

        return first_emotion, combined_text

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
