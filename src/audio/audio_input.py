"""
Audio Input Handler for Mini Microphone
Optimized for USB/I2S mini microphones on Raspberry Pi
"""

import pyaudio
import numpy as np
import wave
import threading
import queue
import logging
from typing import Optional, Callable
import webrtcvad

logger = logging.getLogger(__name__)


class AudioInput:
    """Handles audio input from mini microphone with voice activity detection"""

    def __init__(self, config: dict):
        """
        Initialize audio input handler

        Args:
            config: Audio configuration dictionary from settings.yaml
        """
        self.config = config
        self.audio_config = config['audio']['input']
        self.vad_config = config['audio']['processing']

        self.sample_rate = self.audio_config['sample_rate']
        self.channels = self.audio_config['channels']
        self.chunk_size = self.audio_config['chunk_size']

        self.pyaudio = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        # Limit queue size to prevent memory issues (100 chunks ~= 6 seconds at 16kHz, ~2 seconds at 44kHz)
        self.audio_queue = queue.Queue(maxsize=100)

        self.is_recording = False
        self.is_listening = False
        self.record_thread: Optional[threading.Thread] = None

        # Voice Activity Detection
        self.vad = webrtcvad.Vad(self.vad_config['vad_aggressiveness'])

        self._initialize_audio_device()

    def _initialize_audio_device(self):
        """Find and initialize the audio input device"""
        device_index = self.audio_config.get('device_index')

        if device_index is None:
            # Use default device
            logger.info("Using default audio input device")
        else:
            # Verify the device exists
            try:
                device_info = self.pyaudio.get_device_info_by_index(device_index)
                logger.info(f"Using audio device: {device_info['name']}")
            except Exception as e:
                logger.error(f"Device {device_index} not found: {e}")
                logger.info("Falling back to default device")
                device_index = None

        self.device_index = device_index

    def list_devices(self):
        """List all available audio devices"""
        info = []
        for i in range(self.pyaudio.get_device_count()):
            device_info = self.pyaudio.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                info.append({
                    'index': i,
                    'name': device_info['name'],
                    'channels': device_info['maxInputChannels'],
                    'sample_rate': int(device_info['defaultSampleRate'])
                })
        return info

    def start_listening(self):
        """Start listening for audio input"""
        if self.is_listening:
            logger.warning("Already listening")
            return

        try:
            self.stream = self.pyaudio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )

            self.is_listening = True
            self.stream.start_stream()
            logger.info("Audio input started")

        except Exception as e:
            logger.error(f"Failed to start audio input: {e}")
            raise

    def stop_listening(self):
        """Stop listening for audio input"""
        if not self.is_listening:
            return

        self.is_listening = False

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

        logger.info("Audio input stopped")

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio stream"""
        # Status flags: 1=InputUnderflow, 2=InputOverflow, 4=OutputUnderflow, 8=OutputOverflow
        if status:
            if status == 2:  # Input overflow
                logger.debug(f"Input buffer overflow (status={status}) - data coming faster than processing")
            else:
                logger.warning(f"Audio callback status: {status}")

        if self.is_recording:
            # Use put_nowait to avoid blocking the callback
            try:
                self.audio_queue.put_nowait(in_data)
            except queue.Full:
                logger.warning("Audio queue full, dropping frame")

        return (None, pyaudio.paContinue)

    def start_recording(self) -> threading.Thread:
        """
        Start recording audio with voice activity detection

        Returns:
            Thread object for the recording process
        """
        if self.is_recording:
            logger.warning("Already recording")
            return self.record_thread

        self.is_recording = True
        self.audio_queue.queue.clear()

        self.record_thread = threading.Thread(target=self._record_with_vad)
        self.record_thread.start()

        logger.info("Recording started")
        return self.record_thread

    def stop_recording(self) -> bytes:
        """
        Stop recording and return audio data

        Returns:
            Raw audio bytes
        """
        if not self.is_recording:
            return b''

        self.is_recording = False

        if self.record_thread:
            self.record_thread.join(timeout=2.0)

        # Collect all audio data from queue
        audio_data = []
        while not self.audio_queue.empty():
            try:
                audio_data.append(self.audio_queue.get_nowait())
            except queue.Empty:
                break

        logger.info(f"Recording stopped, collected {len(audio_data)} chunks")
        return b''.join(audio_data)

    def _record_with_vad(self):
        """Record audio with voice activity detection"""
        silence_frames = 0
        max_silence_frames = int(
            self.vad_config['silence_duration'] * self.sample_rate / self.chunk_size
        )

        while self.is_recording:
            try:
                # Get audio chunk (wait with timeout)
                audio_chunk = self.audio_queue.get(timeout=0.1)

                # Check if chunk contains voice
                is_speech = self._detect_voice(audio_chunk)

                if not is_speech:
                    silence_frames += 1
                    if silence_frames >= max_silence_frames:
                        logger.info("Silence detected, stopping recording")
                        self.is_recording = False
                        break
                else:
                    silence_frames = 0

            except queue.Empty:
                continue

    def _detect_voice(self, audio_chunk: bytes) -> bool:
        """
        Detect if audio chunk contains voice

        Args:
            audio_chunk: Raw audio bytes

        Returns:
            True if voice detected, False otherwise
        """
        # Convert to numpy array
        audio_array = np.frombuffer(audio_chunk, dtype=np.int16)

        # Simple amplitude-based detection as fallback
        amplitude = np.abs(audio_array).mean()
        if amplitude < self.vad_config['silence_threshold']:
            return False

        # Use WebRTC VAD for more accurate detection
        try:
            # VAD requires specific frame durations (10, 20, or 30 ms)
            # Ensure audio chunk is the right size
            frame_duration = 30  # ms
            frame_size = int(self.sample_rate * frame_duration / 1000)

            # Pad or trim to correct size
            if len(audio_array) < frame_size:
                audio_array = np.pad(audio_array, (0, frame_size - len(audio_array)))
            elif len(audio_array) > frame_size:
                audio_array = audio_array[:frame_size]

            audio_bytes = audio_array.tobytes()
            return self.vad.is_speech(audio_bytes, self.sample_rate)

        except Exception as e:
            logger.debug(f"VAD error, using amplitude only: {e}")
            return amplitude >= self.vad_config['silence_threshold']

    def save_audio(self, audio_data: bytes, filename: str):
        """
        Save audio data to WAV file

        Args:
            audio_data: Raw audio bytes
            filename: Output filename
        """
        try:
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.pyaudio.get_sample_size(pyaudio.paInt16))
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_data)

            logger.info(f"Audio saved to {filename}")

        except Exception as e:
            logger.error(f"Failed to save audio: {e}")

    def get_audio_level(self) -> float:
        """
        Get current audio input level (0-1)

        Returns:
            Normalized audio level
        """
        if not self.is_listening or self.audio_queue.empty():
            return 0.0

        try:
            audio_chunk = self.audio_queue.get_nowait()
            audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
            level = np.abs(audio_array).mean() / 32768.0  # Normalize to 0-1
            return min(1.0, level)

        except (queue.Empty, Exception):
            return 0.0

    def cleanup(self):
        """Clean up audio resources"""
        self.stop_recording()
        self.stop_listening()
        self.pyaudio.terminate()
        logger.info("Audio input cleanup complete")


if __name__ == "__main__":
    # Test audio input
    logging.basicConfig(level=logging.INFO)

    # Mock config for testing
    config = {
        'audio': {
            'input': {
                'device_index': None,
                'channels': 1,
                'sample_rate': 16000,
                'chunk_size': 1024
            },
            'processing': {
                'vad_aggressiveness': 2,
                'silence_threshold': 500,
                'silence_duration': 1.5
            }
        }
    }

    audio_input = AudioInput(config)

    print("Available audio devices:")
    for device in audio_input.list_devices():
        print(f"  [{device['index']}] {device['name']} "
              f"({device['channels']} ch, {device['sample_rate']} Hz)")

    try:
        audio_input.start_listening()
        print("\nListening... Speak to test (Ctrl+C to stop)")

        while True:
            level = audio_input.get_audio_level()
            bar = '=' * int(level * 50)
            print(f"\rLevel: [{bar:<50}] {level:.2f}", end='')

    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        audio_input.cleanup()
