"""
Audio Output Handler
Manages speaker output and audio playback
"""

import pygame
import pyttsx3
import logging
import queue
import threading
import subprocess
import tempfile
import uuid
import time
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioOutput:
    """Handles audio output to speaker"""

    def __init__(self, config: dict):
        """
        Initialize audio output handler

        Args:
            config: Audio configuration dictionary from settings.yaml
        """
        self.config = config
        self.audio_config = config['audio']['output']

        # Initialize pygame mixer for sound effects
        pygame.mixer.init(
            frequency=self.audio_config['sample_rate'],
            channels=self.audio_config['channels']
        )

        # Audio playback queue
        self.playback_queue = queue.Queue()
        self.is_playing = False
        self.playback_thread: Optional[threading.Thread] = None

        logger.info("Audio output initialized")

    def play_sound(self, sound_file: str, wait: bool = False):
        """
        Play a sound effect

        Args:
            sound_file: Path to sound file (WAV, OGG, MP3)
            wait: If True, wait for sound to finish before returning
        """
        try:
            sound = pygame.mixer.Sound(sound_file)
            channel = sound.play()

            if wait and channel:
                while channel.get_busy():
                    pygame.time.wait(100)

            logger.info(f"Played sound: {sound_file}")

        except Exception as e:
            logger.error(f"Failed to play sound {sound_file}: {e}")

    def play_sound_async(self, sound_file: str):
        """
        Play sound asynchronously in background

        Args:
            sound_file: Path to sound file
        """
        self.playback_queue.put(('sound', sound_file))

        if not self.is_playing:
            self._start_playback_thread()

    def stop_all_sounds(self):
        """Stop all currently playing sounds"""
        pygame.mixer.stop()
        logger.info("Stopped all sounds")

    def set_volume(self, volume: float):
        """
        Set master volume for audio output

        Args:
            volume: Volume level (0.0 to 1.0)
        """
        volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(volume)
        logger.info(f"Volume set to {volume:.2f}")

    def _start_playback_thread(self):
        """Start background thread for audio playback"""
        if self.playback_thread and self.playback_thread.is_alive():
            return

        self.is_playing = True
        self.playback_thread = threading.Thread(target=self._playback_worker)
        self.playback_thread.daemon = True
        self.playback_thread.start()

    def _playback_worker(self):
        """Background worker for playing queued audio"""
        while self.is_playing or not self.playback_queue.empty():
            try:
                item = self.playback_queue.get(timeout=0.5)
                item_type, data = item

                if item_type == 'sound':
                    self.play_sound(data, wait=True)

                self.playback_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Playback worker error: {e}")

        self.is_playing = False

    def cleanup(self):
        """Clean up audio resources"""
        self.is_playing = False
        self.stop_all_sounds()

        if self.playback_thread:
            self.playback_thread.join(timeout=2.0)

        pygame.mixer.quit()
        logger.info("Audio output cleanup complete")


class PiperTTSProvider:
    """Text-to-speech provider using Piper binary"""

    def __init__(self, config: dict):
        """
        Initialize Piper TTS provider

        Args:
            config: Configuration dictionary from settings.yaml
        """
        self.config = config
        self.piper_config = config['speech']['tts']['piper']

        # Piper binary and model paths
        self.piper_binary = self.piper_config['binary_path']
        self.model_path = self.piper_config['model_path']
        self.length_scale = self.piper_config.get('length_scale', 1.0)
        self.temp_dir = self.piper_config.get('temp_dir', '/tmp')

        # Verify piper binary exists
        if not Path(self.piper_binary).exists():
            raise FileNotFoundError(f"Piper binary not found: {self.piper_binary}")

        # Verify model file exists
        if not Path(self.model_path).exists():
            raise FileNotFoundError(f"Piper model not found: {self.model_path}")

        # Initialize pygame mixer for audio playback
        pygame.mixer.init()

        # Speech queue for async TTS
        self.speech_queue = queue.Queue()
        self.is_speaking = False
        self.speech_thread: Optional[threading.Thread] = None
        self.current_channel = None

        logger.info(f"Piper TTS initialized with model: {self.model_path}")

    def speak(self, text: str, wait: bool = False):
        """
        Convert text to speech and play

        Args:
            text: Text to speak
            wait: If True, wait for speech to finish
        """
        try:
            if wait:
                self._synthesize_and_play(text, wait=True)
            else:
                self.speak_async(text)

            logger.info(f"Speaking: {text[:50]}...")

        except Exception as e:
            logger.error(f"Piper TTS error: {e}")

    def _synthesize_and_play(self, text: str, wait: bool = False):
        """
        Synthesize speech with Piper and play the audio

        Args:
            text: Text to synthesize
            wait: If True, wait for playback to finish
        """
        # Generate unique temporary WAV file
        temp_wav = Path(self.temp_dir) / f"piper_{uuid.uuid4()}.wav"

        try:
            # Call Piper binary to synthesize speech
            cmd = [
                self.piper_binary,
                '--model', self.model_path,
                '--length_scale', str(self.length_scale),
                '--output_file', str(temp_wav)
            ]

            # Run Piper with text input via stdin
            subprocess.run(
                cmd,
                input=text,
                text=True,
                capture_output=True,
                check=True,
                timeout=10
            )

            # Play the generated WAV file
            if temp_wav.exists():
                sound = pygame.mixer.Sound(str(temp_wav))
                self.current_channel = sound.play()

                if wait and self.current_channel:
                    # Wait for playback to finish
                    while self.current_channel.get_busy():
                        pygame.time.wait(100)

                # Clean up temporary file after a delay
                if not wait:
                    # Schedule cleanup
                    threading.Timer(2.0, lambda: self._cleanup_wav(temp_wav)).start()
                else:
                    self._cleanup_wav(temp_wav)

        except subprocess.TimeoutExpired:
            logger.error("Piper synthesis timed out")
            self._cleanup_wav(temp_wav)
        except subprocess.CalledProcessError as e:
            logger.error(f"Piper synthesis failed: {e.stderr}")
            self._cleanup_wav(temp_wav)
        except Exception as e:
            logger.error(f"Error synthesizing speech: {e}")
            self._cleanup_wav(temp_wav)

    def _cleanup_wav(self, wav_path: Path):
        """Clean up temporary WAV file"""
        try:
            if wav_path.exists():
                wav_path.unlink()
        except Exception as e:
            logger.debug(f"Could not clean up WAV file: {e}")

    def speak_async(self, text: str):
        """
        Speak text asynchronously in background

        Args:
            text: Text to speak
        """
        self.speech_queue.put(text)

        if not self.is_speaking:
            self._start_speech_thread()

    def _start_speech_thread(self):
        """Start background thread for TTS"""
        if self.speech_thread and self.speech_thread.is_alive():
            return

        self.is_speaking = True
        self.speech_thread = threading.Thread(target=self._speech_worker)
        self.speech_thread.daemon = True
        self.speech_thread.start()

    def _speech_worker(self):
        """Background worker for TTS queue"""
        while self.is_speaking or not self.speech_queue.empty():
            try:
                text = self.speech_queue.get(timeout=0.5)

                # Synthesize and play
                self._synthesize_and_play(text, wait=True)

                self.speech_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Speech worker error: {e}")

        self.is_speaking = False

    def stop_speaking(self):
        """Stop current speech"""
        try:
            # Stop pygame playback
            pygame.mixer.stop()

            # Clear queue
            while not self.speech_queue.empty():
                try:
                    self.speech_queue.get_nowait()
                except queue.Empty:
                    break

            logger.info("Speech stopped")

        except Exception as e:
            logger.error(f"Error stopping speech: {e}")

    def set_rate(self, rate: float):
        """
        Set speech rate (via length_scale)

        Args:
            rate: Speech rate multiplier (1.0 = normal, >1.0 = slower, <1.0 = faster)
        """
        self.length_scale = rate

    def set_volume(self, volume: float):
        """
        Set speech volume

        Args:
            volume: Volume level (0.0 to 1.0)
        """
        pygame.mixer.music.set_volume(volume)

    def cleanup(self):
        """Clean up TTS resources"""
        self.is_speaking = False
        self.stop_speaking()

        if self.speech_thread:
            self.speech_thread.join(timeout=2.0)

        pygame.mixer.quit()

        logger.info("Piper TTS cleanup complete")


class PyttxTTSProvider:
    """Text-to-speech provider using pyttsx3"""

    def __init__(self, config: dict):
        """
        Initialize TTS engine

        Args:
            config: Configuration dictionary from settings.yaml
        """
        self.config = config
        self.tts_config = config['speech']['tts']['pyttsx3']

        # Initialize pyttsx3 engine
        self.engine = pyttsx3.init()

        # Configure voice settings for cute pet character
        self.engine.setProperty('rate', self.tts_config['rate'])
        self.engine.setProperty('volume', self.tts_config['volume'])

        # Set voice (if specific voice ID provided)
        voices = self.engine.getProperty('voices')
        voice_id = self.tts_config.get('voice_id', 0)
        if 0 <= voice_id < len(voices):
            self.engine.setProperty('voice', voices[voice_id].id)

        # Speech queue for async TTS
        self.speech_queue = queue.Queue()
        self.is_speaking = False
        self.speech_thread: Optional[threading.Thread] = None

        logger.info("TTS initialized")

    def speak(self, text: str, wait: bool = False):
        """
        Convert text to speech and play

        Args:
            text: Text to speak
            wait: If True, wait for speech to finish
        """
        try:
            if wait:
                self.engine.say(text)
                self.engine.runAndWait()
            else:
                self.speak_async(text)

            logger.info(f"Speaking: {text}")

        except Exception as e:
            logger.error(f"TTS error: {e}")

    def speak_async(self, text: str):
        """
        Speak text asynchronously in background

        Args:
            text: Text to speak
        """
        self.speech_queue.put(text)

        if not self.is_speaking:
            self._start_speech_thread()

    def _start_speech_thread(self):
        """Start background thread for TTS"""
        if self.speech_thread and self.speech_thread.is_alive():
            return

        self.is_speaking = True
        self.speech_thread = threading.Thread(target=self._speech_worker)
        self.speech_thread.daemon = True
        self.speech_thread.start()

    def _speech_worker(self):
        """Background worker for TTS queue"""
        while self.is_speaking or not self.speech_queue.empty():
            try:
                text = self.speech_queue.get(timeout=0.5)

                # Speak the text
                self.engine.say(text)
                self.engine.runAndWait()

                self.speech_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Speech worker error: {e}")

        self.is_speaking = False

    def stop_speaking(self):
        """Stop current speech"""
        try:
            self.engine.stop()
            # Clear queue
            while not self.speech_queue.empty():
                try:
                    self.speech_queue.get_nowait()
                except queue.Empty:
                    break

            logger.info("Speech stopped")

        except Exception as e:
            logger.error(f"Error stopping speech: {e}")

    def set_rate(self, rate: int):
        """
        Set speech rate

        Args:
            rate: Words per minute
        """
        self.engine.setProperty('rate', rate)

    def set_volume(self, volume: float):
        """
        Set speech volume

        Args:
            volume: Volume level (0.0 to 1.0)
        """
        self.engine.setProperty('volume', volume)

    def list_voices(self):
        """List available TTS voices"""
        voices = self.engine.getProperty('voices')
        voice_list = []

        for i, voice in enumerate(voices):
            voice_list.append({
                'index': i,
                'id': voice.id,
                'name': voice.name,
                'languages': voice.languages
            })

        return voice_list

    def cleanup(self):
        """Clean up TTS resources"""
        self.is_speaking = False
        self.stop_speaking()

        if self.speech_thread:
            self.speech_thread.join(timeout=2.0)

        logger.info("TTS cleanup complete")


class TextToSpeech:
    """
    TTS Factory - Creates appropriate TTS provider based on configuration
    Maintains backward compatibility with existing code
    """

    def __init__(self, config: dict):
        """
        Initialize TTS with configured provider

        Args:
            config: Configuration dictionary from settings.yaml
        """
        self.config = config
        provider_name = config['speech']['tts'].get('provider', 'pyttsx3')

        # Create appropriate provider
        if provider_name == 'piper':
            logger.info("Initializing Piper TTS provider")
            self.provider = PiperTTSProvider(config)
            self.engine = None  # Piper doesn't expose engine object
        elif provider_name == 'pyttsx3':
            logger.info("Initializing pyttsx3 TTS provider")
            self.provider = PyttxTTSProvider(config)
            self.engine = self.provider.engine  # Expose engine for backward compatibility
        else:
            raise ValueError(f"Unknown TTS provider: {provider_name}. Use 'piper' or 'pyttsx3'")

        self.provider_name = provider_name

    def speak(self, text: str, wait: bool = False):
        """Delegate to provider"""
        return self.provider.speak(text, wait)

    def speak_async(self, text: str):
        """Delegate to provider"""
        return self.provider.speak_async(text)

    def stop_speaking(self):
        """Delegate to provider"""
        return self.provider.stop_speaking()

    def set_rate(self, rate: float):
        """Delegate to provider (behavior differs by provider)"""
        if hasattr(self.provider, 'set_rate'):
            return self.provider.set_rate(rate)

    def set_volume(self, volume: float):
        """Delegate to provider"""
        if hasattr(self.provider, 'set_volume'):
            return self.provider.set_volume(volume)

    def list_voices(self):
        """List available voices (pyttsx3 only)"""
        if hasattr(self.provider, 'list_voices'):
            return self.provider.list_voices()
        else:
            logger.warning(f"{self.provider_name} does not support list_voices()")
            return []

    def cleanup(self):
        """Delegate to provider"""
        return self.provider.cleanup()

    @property
    def is_speaking(self):
        """Check if currently speaking"""
        return self.provider.is_speaking


if __name__ == "__main__":
    # Test audio output and TTS
    logging.basicConfig(level=logging.INFO)

    # Mock config
    config = {
        'audio': {
            'output': {
                'sample_rate': 22050,
                'channels': 1
            }
        },
        'speech': {
            'tts': {
                'pyttsx3': {
                    'rate': 150,
                    'volume': 0.9,
                    'voice_id': 0,
                    'pitch': 1.5
                }
            }
        }
    }

    print("Testing Audio Output...")
    audio_output = AudioOutput(config)
    audio_output.set_volume(0.7)

    print("\nTesting TTS...")
    tts = TextToSpeech(config)

    print("Available voices:")
    for voice in tts.list_voices():
        print(f"  [{voice['index']}] {voice['name']}")

    print("\nSpeaking test...")
    tts.speak("Hello! I'm your companion bot. I love to play and learn!", wait=True)

    print("\nAsync speech test...")
    tts.speak_async("This is asynchronous speech.")
    tts.speak_async("I can queue multiple sentences.")

    import time
    time.sleep(5)

    print("\nCleaning up...")
    audio_output.cleanup()
    tts.cleanup()

    print("Test complete!")
