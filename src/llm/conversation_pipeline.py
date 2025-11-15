"""
Conversation Pipeline
Complete end-to-end conversational AI pipeline
Voice Input → LLM Processing → Voice Output
"""

import logging
import time
import sys
from pathlib import Path
from typing import Optional, Callable, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from llm.voice_pipeline import VoicePipeline
from llm.conversation_manager import ConversationManager
from llm.tts_engine import TTSEngine

logger = logging.getLogger(__name__)


class ConversationPipeline:
    """
    Complete conversational pipeline integrating:
    - Voice input (STT)
    - LLM processing
    - Voice output (TTS)
    - Emotion awareness
    """

    def __init__(
        self,
        config: dict,
        emotion_engine=None,
        user_memory=None
    ):
        """
        Initialize conversation pipeline

        Args:
            config: Configuration dictionary
            emotion_engine: Optional EmotionEngine instance
            user_memory: Optional UserMemory instance
        """
        self.config = config
        self.emotion_engine = emotion_engine
        self.user_memory = user_memory

        # Initialize components
        logger.info("Initializing conversation pipeline components...")

        self.voice_input = VoicePipeline(config)
        self.conversation_manager = ConversationManager(
            config,
            emotion_engine=emotion_engine,
            user_memory=user_memory
        )
        self.tts = TTSEngine(config)

        # State
        self.is_running = False
        self.is_processing = False

        # Callbacks
        self.on_listening: Optional[Callable[[], None]] = None
        self.on_transcribed: Optional[Callable[[str], None]] = None
        self.on_thinking: Optional[Callable[[], None]] = None
        self.on_responding: Optional[Callable[[str, str], None]] = None  # (text, emotion)
        self.on_speaking: Optional[Callable[[], None]] = None
        self.on_complete: Optional[Callable[[], None]] = None

        # Statistics
        self.total_conversations = 0
        self.total_response_time = 0.0
        self.average_response_time = 0.0

        logger.info("Conversation pipeline initialized")

    def start(self):
        """Start the conversation pipeline"""
        if self.is_running:
            logger.warning("Pipeline already running")
            return

        logger.info("Starting conversation pipeline...")

        # Set up voice input callbacks
        self.voice_input.set_transcription_callback(self._on_transcription)
        self.voice_input.set_speech_callbacks(
            on_start=self._on_speech_start,
            on_end=self._on_speech_end
        )

        # Start voice input
        self.voice_input.start()

        self.is_running = True
        logger.info("Conversation pipeline started - ready for voice input")

    def stop(self):
        """Stop the conversation pipeline"""
        if not self.is_running:
            return

        logger.info("Stopping conversation pipeline...")

        self.is_running = False

        # Stop components
        self.voice_input.stop()
        self.tts.stop_speaking()

        logger.info("Conversation pipeline stopped")

    def _on_speech_start(self):
        """Called when user starts speaking"""
        logger.debug("User started speaking")

        # Stop any ongoing TTS
        if self.tts.is_speaking:
            self.tts.stop_speaking()
            logger.info("Interrupted bot speech")

        # Trigger callback
        if self.on_listening:
            self.on_listening()

    def _on_speech_end(self):
        """Called when user stops speaking"""
        logger.debug("User stopped speaking, processing...")

    def _on_transcription(self, result: Dict):
        """
        Called when speech is transcribed

        Args:
            result: Transcription result from voice pipeline
        """
        transcribed_text = result.get('text', '').strip()
        confidence = result.get('confidence', 0.0)

        if not transcribed_text:
            logger.warning("Empty transcription, ignoring")
            return

        logger.info(f"Transcribed: '{transcribed_text}' (confidence: {confidence:.0%})")

        # Trigger callback
        if self.on_transcribed:
            self.on_transcribed(transcribed_text)

        # Process and respond
        self._process_and_respond(transcribed_text)

    def _process_and_respond(self, user_text: str):
        """
        Process user input and generate response

        Args:
            user_text: User's transcribed speech
        """
        if self.is_processing:
            logger.warning("Already processing, skipping")
            return

        self.is_processing = True
        start_time = time.time()

        try:
            # Trigger thinking callback
            if self.on_thinking:
                self.on_thinking()

            # Generate response using conversation manager
            response_text, metadata = self.conversation_manager.process_user_input(user_text)

            # Get current emotion for TTS modulation
            emotion = metadata.get('emotion', 'happy')

            logger.info(f"Generated response ({emotion}): {response_text}")

            # Trigger responding callback
            if self.on_responding:
                self.on_responding(response_text, emotion)

            # Speak response with emotion
            if self.on_speaking:
                self.on_speaking()

            self.tts.speak_with_emotion(response_text, emotion, wait=True)

            # Update statistics
            response_time = time.time() - start_time
            self.total_conversations += 1
            self.total_response_time += response_time
            self.average_response_time = self.total_response_time / self.total_conversations

            logger.info(f"Complete conversation cycle in {response_time:.2f}s")

            # Trigger complete callback
            if self.on_complete:
                self.on_complete()

        except Exception as e:
            logger.error(f"Error processing conversation: {e}", exc_info=True)

        finally:
            self.is_processing = False

    def process_text_input(self, text: str) -> str:
        """
        Process text input directly (without voice)

        Args:
            text: User's text input

        Returns:
            Bot's response text
        """
        try:
            response_text, metadata = self.conversation_manager.process_user_input(text)
            emotion = metadata.get('emotion', 'happy')

            logger.info(f"Text response ({emotion}): {response_text}")

            return response_text

        except Exception as e:
            logger.error(f"Error processing text: {e}")
            return "Sorry, I had trouble understanding that."

    def speak_response(self, text: str, emotion: Optional[str] = None):
        """
        Speak a response directly

        Args:
            text: Text to speak
            emotion: Optional emotion for voice modulation
        """
        if not emotion:
            emotion = self.conversation_manager._get_current_emotion()

        self.tts.speak_with_emotion(text, emotion, wait=False)

    def set_callbacks(
        self,
        on_listening: Optional[Callable[[], None]] = None,
        on_transcribed: Optional[Callable[[str], None]] = None,
        on_thinking: Optional[Callable[[], None]] = None,
        on_responding: Optional[Callable[[str, str], None]] = None,
        on_speaking: Optional[Callable[[], None]] = None,
        on_complete: Optional[Callable[[], None]] = None
    ):
        """
        Set callbacks for pipeline events

        Args:
            on_listening: Called when user starts speaking
            on_transcribed: Called when speech is transcribed (receives text)
            on_thinking: Called when LLM is processing
            on_responding: Called when response is ready (receives text and emotion)
            on_speaking: Called when TTS starts
            on_complete: Called when full cycle completes
        """
        self.on_listening = on_listening
        self.on_transcribed = on_transcribed
        self.on_thinking = on_thinking
        self.on_responding = on_responding
        self.on_speaking = on_speaking
        self.on_complete = on_complete

        logger.info("Pipeline callbacks set")

    def get_statistics(self) -> Dict:
        """
        Get pipeline statistics

        Returns:
            Dictionary with stats from all components
        """
        return {
            'conversations': self.total_conversations,
            'avg_response_time': self.average_response_time,
            'is_processing': self.is_processing,
            'voice_input': self.voice_input.get_statistics(),
            'llm': self.conversation_manager.llm.get_statistics(),
            'tts': self.tts.get_statistics(),
            'conversation': {
                'message_count': self.conversation_manager.message_count,
                'current_emotion': self.conversation_manager._get_current_emotion()
            }
        }

    def get_conversation_history(self, limit: Optional[int] = None) -> list:
        """
        Get conversation history

        Args:
            limit: Optional limit on messages

        Returns:
            List of conversation messages
        """
        return self.conversation_manager.get_conversation_history(limit)

    def clear_conversation(self):
        """Clear conversation context and history"""
        self.conversation_manager.clear_history()
        logger.info("Conversation cleared")

    def save_conversation(self, filename: str):
        """
        Save conversation to file

        Args:
            filename: Output file path
        """
        self.conversation_manager.save_conversation(filename)

    def cleanup(self):
        """Clean up all pipeline resources"""
        logger.info("Cleaning up conversation pipeline...")

        self.stop()
        self.voice_input.cleanup()
        self.tts.cleanup()

        logger.info("Conversation pipeline cleanup complete")


if __name__ == "__main__":
    # Test conversation pipeline
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    import yaml

    print("=" * 70)
    print("Conversation Pipeline Test")
    print("=" * 70)

    # Load config
    config_path = Path(__file__).parent.parent.parent / 'config' / 'settings.yaml'

    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
        print("✅ Config loaded")
    else:
        print("❌ Config not found, using mock config")
        # Would need full mock config here
        sys.exit(1)

    # Initialize pipeline
    print("\nInitializing pipeline...")
    pipeline = ConversationPipeline(config)

    # Test text-only mode first
    print("\n" + "=" * 70)
    print("TEXT MODE TEST (no voice)")
    print("=" * 70)

    test_inputs = [
        "Hello!",
        "How are you?",
        "What's your favorite thing to do?"
    ]

    for user_input in test_inputs:
        print(f"\nYou: {user_input}")
        response = pipeline.process_text_input(user_input)
        print(f"Bot: {response}")
        time.sleep(0.5)

    # Show stats
    stats = pipeline.get_statistics()
    print("\n" + "=" * 70)
    print("Statistics:")
    print("=" * 70)
    print(f"Total conversations: {stats['conversations']}")
    print(f"Avg response time: {stats['avg_response_time']:.2f}s")
    print(f"LLM requests: {stats['llm']['total_requests']}")
    print(f"Current emotion: {stats['conversation']['current_emotion']}")

    # Test voice mode
    print("\n" + "=" * 70)
    print("VOICE MODE TEST")
    print("=" * 70)
    print("Starting voice conversation...")
    print("Speak into your microphone (Ctrl+C to stop)")
    print("=" * 70)

    try:
        pipeline.start()

        # Keep running
        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nStopping...")

    finally:
        pipeline.cleanup()
        print("\n✅ Test complete!")
