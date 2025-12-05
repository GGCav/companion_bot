"""
TTS Engine
Text-to-Speech with emotion-based voice modulation
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from audio.audio_output import TextToSpeech as BaseTTS

logger = logging.getLogger(__name__)


class TTSEngine:
    """
    Text-to-Speech engine with emotion-aware voice modulation
    Wraps the existing TextToSpeech class with personality features
    """

    def __init__(self, config: dict):
        """
        Initialize TTS engine

        Args:
            config: Configuration dictionary from settings.yaml
        """
        self.config = config
        self.tts_config = config['speech']['tts']
        self.provider = self.tts_config['provider']

        # Initialize base TTS engine
        self.tts = BaseTTS(config)

        # Base voice settings (provider-specific)
        if self.provider == 'piper':
            # Piper uses length_scale (1.0 = normal) instead of rate (WPM)
            self.base_rate = self.tts_config['piper'].get('length_scale', 1.0)
            self.base_volume = 0.9  # Default volume for pygame playback
            self.base_pitch = 1.0  # Piper doesn't support pitch control
        elif self.provider == 'pyttsx3':
            # pyttsx3 uses words per minute for rate
            self.base_rate = self.tts_config['pyttsx3']['rate']
            self.base_volume = self.tts_config['pyttsx3']['volume']
            self.base_pitch = self.tts_config['pyttsx3'].get('pitch', 1.0)
        else:
            # Fallback defaults
            self.base_rate = 150
            self.base_volume = 0.9
            self.base_pitch = 1.0
            logger.warning(f"Unknown TTS provider: {self.provider}, using default settings")

        # Emotion-to-voice mappings
        self.emotion_modulations = {
            'happy': {'rate_mult': 1.1, 'pitch_mult': 1.2, 'volume_mult': 1.0},
            'excited': {'rate_mult': 1.3, 'pitch_mult': 1.4, 'volume_mult': 1.1},
            'sad': {'rate_mult': 0.8, 'pitch_mult': 0.8, 'volume_mult': 0.9},
            'sleepy': {'rate_mult': 0.7, 'pitch_mult': 0.7, 'volume_mult': 0.8},
            'angry': {'rate_mult': 1.2, 'pitch_mult': 0.9, 'volume_mult': 1.0},
            'scared': {'rate_mult': 1.1, 'pitch_mult': 1.3, 'volume_mult': 0.9},
            'loving': {'rate_mult': 0.9, 'pitch_mult': 1.1, 'volume_mult': 0.95},
            'playful': {'rate_mult': 1.15, 'pitch_mult': 1.25, 'volume_mult': 1.05},
            'curious': {'rate_mult': 1.05, 'pitch_mult': 1.15, 'volume_mult': 1.0},
            'lonely': {'rate_mult': 0.85, 'pitch_mult': 0.9, 'volume_mult': 0.85},
            'bored': {'rate_mult': 0.8, 'pitch_mult': 0.85, 'volume_mult': 0.9},
            'surprised': {'rate_mult': 1.25, 'pitch_mult': 1.35, 'volume_mult': 1.05},
        }

        # Speaking state
        self.current_emotion = None
        self.is_speaking = False

        # Performance stats
        self.total_utterances = 0
        self.total_duration = 0.0

        logger.info(f"TTS Engine initialized with {self.provider}")

    def speak(
        self,
        text: str,
        emotion: Optional[str] = None,
        wait: bool = False
    ):
        """
        Speak text with optional emotion modulation

        Args:
            text: Text to speak
            emotion: Optional emotion for voice modulation
            wait: If True, wait for speech to finish
        """
        if not text or not text.strip():
            logger.warning("Empty text, skipping TTS")
            return

        try:
            # Apply emotion modulation if specified
            if emotion and emotion in self.emotion_modulations:
                self._set_emotion_voice(emotion)
            else:
                self._reset_voice()

            # Speak
            self.tts.speak(text, wait=wait)

            # Update stats
            self.total_utterances += 1
            logger.info(f"Speaking ({emotion or 'neutral'}): {text[:50]}...")

        except Exception as e:
            logger.error(f"TTS error: {e}")

    def speak_with_emotion(self, text: str, emotion: str, wait: bool = False):
        """
        Convenience method to speak with emotion

        Args:
            text: Text to speak
            emotion: Emotion for voice modulation
            wait: If True, wait for speech to finish
        """
        self.speak(text, emotion=emotion, wait=wait)

    def speak_segments_with_emotions(self, segments: list, wait: bool = False):
        """
        Speak multiple text segments, each with its own emotion

        Enables natural emotion transitions within a single response.
        Each segment is spoken with appropriate voice modulation.

        Args:
            segments: List of (emotion, text) tuples
            wait: If True, wait for all segments to finish

        Example:
            segments = [
                ("excited", "Hello!"),
                ("curious", "What are you doing?")
            ]
        """
        if not segments:
            logger.warning("Empty segments list, skipping TTS")
            return

        try:
            import time

            logger.info(f"Speaking {len(segments)} emotion segment(s)")

            for i, (emotion, text) in enumerate(segments):
                if not text or not text.strip():
                    continue

                # Apply emotion for this segment
                if emotion and emotion in self.emotion_modulations:
                    self._set_emotion_voice(emotion)
                else:
                    self._reset_voice()

                # Speak this segment (always wait for it to finish)
                self.tts.speak(text, wait=True)

                # Small pause between segments (50ms) for natural transition
                # Skip pause after the last segment
                if i < len(segments) - 1:
                    time.sleep(0.05)

                # Update stats
                self.total_utterances += 1

                logger.debug(f"Segment {i+1}/{len(segments)}: ({emotion}) {text[:30]}...")

            logger.info(f"Completed speaking {len(segments)} segment(s)")

        except Exception as e:
            logger.error(f"Error in segmented TTS: {e}")

    def speak_async(self, text: str, emotion: Optional[str] = None):
        """
        Speak asynchronously (non-blocking)

        Args:
            text: Text to speak
            emotion: Optional emotion for voice modulation
        """
        self.speak(text, emotion=emotion, wait=False)

    def stop_speaking(self):
        """Stop current speech"""
        try:
            self.tts.stop_speaking()
            logger.info("Speech stopped")
        except Exception as e:
            logger.error(f"Error stopping speech: {e}")

    def _set_emotion_voice(self, emotion: str):
        """
        Set voice parameters based on emotion

        Args:
            emotion: Emotion state
        """
        if emotion not in self.emotion_modulations:
            logger.warning(f"Unknown emotion: {emotion}, using neutral voice")
            return

        modulation = self.emotion_modulations[emotion]

        # Calculate modulated parameters
        new_rate = int(self.base_rate * modulation['rate_mult'])
        new_volume = self.base_volume * modulation['volume_mult']
        # Note: pitch modulation depends on TTS engine capabilities

        # Apply to engine (use factory methods for provider compatibility)
        try:
            # For Piper: rate becomes length_scale (inverse: slower = higher value)
            # For pyttsx3: rate is words per minute
            if hasattr(self.tts, 'provider_name') and self.tts.provider_name == 'piper':
                # Piper uses length_scale: 1.0 = normal, 1.2 = slower, 0.8 = faster
                # Invert rate multiplier for Piper's length_scale
                length_scale = 1.0 / modulation['rate_mult']
                self.tts.set_rate(length_scale)
            else:
                # pyttsx3 uses words per minute
                self.tts.set_rate(new_rate)

            self.tts.set_volume(min(1.0, new_volume))

            self.current_emotion = emotion
            logger.debug(f"Voice set to {emotion}: rate={new_rate}, volume={new_volume:.2f}")

        except Exception as e:
            logger.error(f"Error setting voice parameters: {e}")

    def _reset_voice(self):
        """Reset voice to base parameters"""
        try:
            # Use factory methods instead of direct engine access
            if hasattr(self.tts, 'provider_name') and self.tts.provider_name == 'piper':
                self.tts.set_rate(1.0)  # Piper: 1.0 = normal length_scale
            else:
                self.tts.set_rate(self.base_rate)  # pyttsx3: words per minute

            self.tts.set_volume(self.base_volume)

            self.current_emotion = None
            logger.debug("Voice reset to base parameters")

        except Exception as e:
            logger.error(f"Error resetting voice: {e}")

    def get_available_voices(self) -> list:
        """
        Get list of available TTS voices

        Returns:
            List of voice dictionaries
        """
        return self.tts.list_voices()

    def set_voice(self, voice_id: int):
        """
        Set TTS voice by ID

        Args:
            voice_id: Voice index
        """
        voices = self.get_available_voices()
        if 0 <= voice_id < len(voices):
            self.tts.engine.setProperty('voice', voices[voice_id]['id'])
            logger.info(f"Voice changed to: {voices[voice_id]['name']}")
        else:
            logger.error(f"Invalid voice ID: {voice_id}")

    def test_emotions(self):
        """Test all emotion voices"""
        test_phrase = "Hello! This is how I sound."

        for emotion in self.emotion_modulations.keys():
            print(f"\nTesting {emotion} voice...")
            self.speak(test_phrase, emotion=emotion, wait=True)
            import time
            time.sleep(0.5)

    def get_statistics(self) -> Dict:
        """
        Get TTS statistics

        Returns:
            Dictionary with stats
        """
        return {
            'total_utterances': self.total_utterances,
            'total_duration': self.total_duration,
            'current_emotion': self.current_emotion,
            'provider': self.provider
        }

    def cleanup(self):
        """Clean up TTS resources"""
        self.stop_speaking()
        self.tts.cleanup()
        logger.info("TTS Engine cleanup complete")


if __name__ == "__main__":
    # Test TTS engine
    logging.basicConfig(level=logging.INFO)

    import yaml

    # Load config or use mock
    config_path = Path(__file__).parent.parent.parent / 'config' / 'settings.yaml'

    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
    else:
        # Mock config
        config = {
            'speech': {
                'tts': {
                    'provider': 'pyttsx3',
                    'pyttsx3': {
                        'rate': 150,
                        'volume': 0.9,
                        'voice_id': 0,
                        'pitch': 1.5
                    }
                }
            }
        }

    print("=" * 60)
    print("TTS Engine Test")
    print("=" * 60)

    # Initialize engine
    tts = TTSEngine(config)

    # Show available voices
    print("\nAvailable voices:")
    for voice in tts.get_available_voices():
        print(f"  [{voice['index']}] {voice['name']}")

    # Test basic speech
    print("\n1. Testing neutral voice...")
    tts.speak("Hello! I am your companion bot.", wait=True)

    # Test emotions
    print("\n2. Testing emotion voices...")

    emotions_to_test = ['happy', 'excited', 'sad', 'sleepy', 'playful']

    for emotion in emotions_to_test:
        print(f"\n   Testing {emotion}...")
        tts.speak(f"I feel {emotion}!", emotion=emotion, wait=True)
        import time
        time.sleep(0.3)

    # Test interruption
    print("\n3. Testing stop...")
    tts.speak_async("This is a very long sentence that will be interrupted before it finishes speaking.")
    import time
    time.sleep(1.0)
    tts.stop_speaking()
    print("   Speech stopped!")

    # Show stats
    stats = tts.get_statistics()
    print("\nStatistics:")
    print(f"  Total utterances: {stats['total_utterances']}")
    print(f"  Provider: {stats['provider']}")

    # Cleanup
    tts.cleanup()

    print("\n✅ Test complete!")
