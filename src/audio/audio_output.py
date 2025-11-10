"""
Audio Output Handler
Manages speaker output and audio playback
"""

import pygame
import pyttsx3
import logging
import queue
import threading
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


class TextToSpeech:
    """Text-to-speech handler using pyttsx3"""

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
