"""
Voice Input Pipeline
Integrates mini microphone audio capture with Whisper STT
Complete end-to-end voice recognition
"""

import logging
import time
import threading
import queue
from typing import Optional, Callable, Dict
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from audio.audio_input import AudioInput
from audio.voice_detector import VoiceActivityDetector
from llm.stt_engine import STTEngine, RealtimeSTT

logger = logging.getLogger(__name__)


class VoicePipeline:
    """
    Complete voice input pipeline:
    Mini Microphone → VAD → STT (Whisper) → Text Output
    """

    def __init__(self, config: dict):
        """
        Initialize voice pipeline

        Args:
            config: Configuration dictionary from settings.yaml
        """
        self.config = config
        self.audio_config = config['audio']

        # Initialize components
        logger.info("Initializing voice pipeline components...")

        self.audio_input = AudioInput(config)
        self.vad = VoiceActivityDetector(config)
        self.stt_engine = STTEngine(config)
        self.realtime_stt = RealtimeSTT(config, self.stt_engine)

        # State management
        self.is_running = False
        self.is_listening = False
        self.pipeline_thread: Optional[threading.Thread] = None

        # Transcription queue
        self.transcription_queue = queue.Queue()

        # Callbacks
        self.on_transcription: Optional[Callable[[Dict], None]] = None
        self.on_speech_start: Optional[Callable[[], None]] = None
        self.on_speech_end: Optional[Callable[[], None]] = None

        # Statistics
        self.total_utterances = 0
        self.total_transcription_time = 0.0
        self.last_transcription_time = 0.0

        logger.info("Voice pipeline initialized")

    def start(self):
        """Start the voice input pipeline"""
        if self.is_running:
            logger.warning("Pipeline already running")
            return

        logger.info("Starting voice pipeline...")

        # Start audio input
        self.audio_input.start_listening()

        # Start pipeline thread
        self.is_running = True
        self.pipeline_thread = threading.Thread(target=self._pipeline_loop, daemon=True)
        self.pipeline_thread.start()

        logger.info("Voice pipeline started - listening for speech")

    def stop(self):
        """Stop the voice input pipeline"""
        if not self.is_running:
            return

        logger.info("Stopping voice pipeline...")

        self.is_running = False

        if self.pipeline_thread:
            self.pipeline_thread.join(timeout=2.0)

        self.audio_input.stop_listening()

        logger.info("Voice pipeline stopped")

    def _pipeline_loop(self):
        """Main pipeline processing loop"""
        logger.info("Pipeline loop started")

        audio_buffer = []
        speech_detected = False
        silence_frames = 0
        max_silence_frames = 20  # ~2 seconds at 10 Hz

        while self.is_running:
            try:
                # Get audio chunk from input
                if not self.audio_input.audio_queue.empty():
                    audio_chunk = self.audio_input.audio_queue.get(timeout=0.1)

                    # Detect voice activity
                    has_voice = self.vad.detect(audio_chunk)

                    if has_voice:
                        if not speech_detected:
                            # Speech started
                            speech_detected = True
                            audio_buffer = []
                            silence_frames = 0
                            logger.info("🎤 Speech detected - recording...")

                            if self.on_speech_start:
                                self.on_speech_start()

                        # Add to buffer
                        audio_buffer.append(audio_chunk)

                    elif speech_detected:
                        # In speech but current frame has no voice
                        audio_buffer.append(audio_chunk)
                        silence_frames += 1

                        # Check if speech has ended
                        if silence_frames >= max_silence_frames:
                            # Speech ended
                            logger.info("🔇 Speech ended - transcribing...")

                            if self.on_speech_end:
                                self.on_speech_end()

                            # Process the recorded audio
                            self._process_audio_buffer(audio_buffer)

                            # Reset state
                            speech_detected = False
                            audio_buffer = []
                            silence_frames = 0
                            self.vad.reset()

                else:
                    # No audio available, short sleep
                    time.sleep(0.01)

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in pipeline loop: {e}", exc_info=True)

        logger.info("Pipeline loop ended")

    def _process_audio_buffer(self, audio_buffer: list):
        """
        Process recorded audio buffer through STT

        Args:
            audio_buffer: List of audio chunks
        """
        if not audio_buffer:
            logger.warning("Empty audio buffer, skipping transcription")
            return

        try:
            # Combine audio chunks
            audio_data = b''.join(audio_buffer)

            # Check minimum length (at least 0.5 seconds)
            min_length = int(0.5 * self.audio_config['input']['sample_rate'] * 2)  # 2 bytes per sample
            if len(audio_data) < min_length:
                logger.debug("Audio too short, skipping transcription")
                return

            logger.info(f"Transcribing {len(audio_data)} bytes of audio...")
            start_time = time.time()

            # Transcribe with Whisper
            result = self.realtime_stt.transcribe(audio_data)

            transcription_time = time.time() - start_time
            self.total_transcription_time += transcription_time
            self.last_transcription_time = transcription_time

            # Check if transcription was successful
            text = result.get('text', '').strip()

            if text:
                self.total_utterances += 1

                logger.info(f"✅ Transcription: '{text}' "
                           f"(confidence: {result.get('confidence', 0):.2f}, "
                           f"time: {transcription_time:.2f}s)")

                # Add to queue
                self.transcription_queue.put(result)

                # Call callback
                if self.on_transcription:
                    self.on_transcription(result)

            else:
                logger.info("❌ No speech detected in audio")

        except Exception as e:
            logger.error(f"Failed to process audio buffer: {e}", exc_info=True)

    def get_transcription(self, timeout: float = 0.1) -> Optional[Dict]:
        """
        Get next transcription from queue (non-blocking)

        Args:
            timeout: Maximum time to wait

        Returns:
            Transcription result dictionary or None
        """
        try:
            return self.transcription_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def wait_for_transcription(self, timeout: float = 30.0) -> Optional[Dict]:
        """
        Wait for next transcription (blocking)

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            Transcription result dictionary or None
        """
        try:
            return self.transcription_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def set_transcription_callback(self, callback: Callable[[Dict], None]):
        """
        Set callback function for transcriptions

        Args:
            callback: Function to call with transcription result
        """
        self.on_transcription = callback
        logger.info("Transcription callback registered")

    def set_speech_callbacks(
        self,
        on_start: Optional[Callable[[], None]] = None,
        on_end: Optional[Callable[[], None]] = None
    ):
        """
        Set callbacks for speech detection events

        Args:
            on_start: Called when speech starts
            on_end: Called when speech ends
        """
        self.on_speech_start = on_start
        self.on_speech_end = on_end
        logger.info("Speech event callbacks registered")

    def get_statistics(self) -> Dict:
        """
        Get pipeline statistics

        Returns:
            Dictionary with statistics
        """
        avg_time = (self.total_transcription_time / max(1, self.total_utterances))

        return {
            'total_utterances': self.total_utterances,
            'total_transcription_time': self.total_transcription_time,
            'avg_transcription_time': avg_time,
            'last_transcription_time': self.last_transcription_time,
            'is_running': self.is_running,
            'stt_stats': self.stt_engine.get_performance_stats()
        }

    def test_microphone(self) -> bool:
        """
        Test if microphone is working

        Returns:
            True if microphone is detected
        """
        logger.info("Testing microphone...")

        try:
            devices = self.audio_input.list_devices()

            if not devices:
                logger.error("No audio input devices found!")
                return False

            logger.info(f"Found {len(devices)} audio device(s):")
            for device in devices:
                logger.info(f"  [{device['index']}] {device['name']} "
                           f"({device['channels']} ch, {device['sample_rate']} Hz)")

            # Try to start listening briefly
            self.audio_input.start_listening()
            time.sleep(0.5)

            # Check audio level
            level = self.audio_input.get_audio_level()
            logger.info(f"Current audio level: {level:.2f}")

            self.audio_input.stop_listening()

            logger.info("✅ Microphone test passed")
            return True

        except Exception as e:
            logger.error(f"❌ Microphone test failed: {e}")
            return False

    def cleanup(self):
        """Clean up all resources"""
        logger.info("Cleaning up voice pipeline...")

        self.stop()
        self.audio_input.cleanup()
        self.stt_engine.cleanup()

        logger.info("Voice pipeline cleanup complete")


if __name__ == "__main__":
    # Test voice pipeline
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    import yaml

    print("=" * 60)
    print("Voice Pipeline Test")
    print("Mini Microphone → VAD → Whisper STT")
    print("=" * 60)

    # Load config
    config_path = Path(__file__).parent.parent.parent / 'config' / 'settings.yaml'

    if not config_path.exists():
        print("❌ Config file not found!")
        print("Creating mock config...")

        config = {
            'audio': {
                'input': {
                    'device_index': None,
                    'channels': 1,
                    'sample_rate': 16000,
                    'chunk_size': 1024
                },
                'processing': {
                    'noise_reduction': True,
                    'vad_aggressiveness': 2,
                    'silence_threshold': 500,
                    'silence_duration': 1.5
                }
            },
            'speech': {
                'stt': {
                    'provider': 'whisper',
                    'language': 'en',
                    'whisper': {
                        'model_size': 'base',
                        'device': 'cpu'
                    }
                }
            }
        }
    else:
        with open(config_path) as f:
            config = yaml.safe_load(f)

    print("\nInitializing voice pipeline...")
    pipeline = VoicePipeline(config)

    # Test microphone
    print("\nTesting microphone...")
    if not pipeline.test_microphone():
        print("❌ Microphone test failed! Check connections.")
        sys.exit(1)

    # Set up callbacks
    def on_transcription(result):
        print(f"\n💬 YOU SAID: '{result['text']}'")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Language: {result['language']}")
        print(f"   Duration: {result['duration']:.2f}s")

    def on_speech_start():
        print("\n🎤 Listening...")

    def on_speech_end():
        print("🔇 Processing...")

    pipeline.set_transcription_callback(on_transcription)
    pipeline.set_speech_callbacks(on_speech_start, on_speech_end)

    # Start pipeline
    print("\n✅ Starting voice pipeline...")
    print("Speak into your mini microphone. Press Ctrl+C to stop.\n")

    try:
        pipeline.start()

        # Keep running
        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nStopping...")

    finally:
        pipeline.cleanup()

        # Show statistics
        stats = pipeline.get_statistics()
        print("\n" + "=" * 60)
        print("Session Statistics")
        print("=" * 60)
        print(f"Total utterances: {stats['total_utterances']}")
        print(f"Avg transcription time: {stats['avg_transcription_time']:.2f}s")
        print(f"Total time: {stats['total_transcription_time']:.2f}s")
        print("=" * 60)

        print("\n✅ Test complete!")
