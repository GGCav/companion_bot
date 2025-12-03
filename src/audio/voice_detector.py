"""
Voice Activity Detector
Enhanced voice detection for mini microphone
"""

import numpy as np
import webrtcvad
import logging
from collections import deque
from scipy import signal

logger = logging.getLogger(__name__)


class VoiceActivityDetector:
    """Advanced voice activity detection with noise filtering"""

    def __init__(self, config: dict):
        """
        Initialize voice activity detector

        Args:
            config: Audio configuration dictionary
        """
        self.config = config
        self.vad_config = config['audio']['processing']
        self.sample_rate = config['audio']['input']['sample_rate']

        # WebRTC VAD
        self.vad = webrtcvad.Vad(self.vad_config['vad_aggressiveness'])

        # Running average for noise floor estimation
        self.noise_floor = self.vad_config['silence_threshold']
        self.noise_floor_samples = deque(maxlen=100)

        # Voice detection state
        self.is_voice_active = False
        self.voice_frames = 0
        self.silence_frames = 0

        # Thresholds
        self.min_voice_frames = 3  # Minimum consecutive frames to confirm voice
        self.max_silence_frames = 10  # Maximum silence frames before deactivating

    def detect(self, audio_chunk: bytes) -> bool:
        """
        Detect if audio chunk contains voice activity

        Args:
            audio_chunk: Raw audio bytes (int16)

        Returns:
            True if voice is detected, False otherwise
        """
        # Convert to numpy array
        audio_array = np.frombuffer(audio_chunk, dtype=np.int16)

        # Calculate amplitude
        amplitude = np.abs(audio_array).mean()

        # Update noise floor estimate
        self._update_noise_floor(amplitude)

        # Check amplitude threshold (with adaptive noise floor)
        # Use 2x noise floor as threshold for amplitude
        amplitude_threshold = max(self.noise_floor * 2.0, 150)  # Minimum threshold of 600
        amplitude_check = amplitude > amplitude_threshold

        # Use WebRTC VAD for confirmation (now works with 44100 Hz via resampling)
        vad_check = self._check_webrtc_vad(audio_chunk)

        # BOTH checks must pass (AND logic) to reduce false positives
        is_voice = amplitude_check and vad_check
        
        # Debug logging (every 50 frames)
        if not hasattr(self, '_debug_counter'):
            self._debug_counter = 0
        self._debug_counter += 1
        if self._debug_counter % 50 == 0:
            logger.debug(f"VAD: amp={amplitude:.0f}, threshold={amplitude_threshold:.0f}, "
                        f"amp_ok={amplitude_check}, vad_ok={vad_check}, voice={is_voice}")

        # Update state with hysteresis
        if is_voice:
            self.voice_frames += 1
            self.silence_frames = 0

            if self.voice_frames >= self.min_voice_frames:
                self.is_voice_active = True
        else:
            self.silence_frames += 1
            self.voice_frames = 0

            if self.silence_frames >= self.max_silence_frames:
                self.is_voice_active = False

        return self.is_voice_active

    def _update_noise_floor(self, amplitude: float):
        """
        Update adaptive noise floor estimate

        Args:
            amplitude: Current amplitude value
        """
        self.noise_floor_samples.append(amplitude)

        if len(self.noise_floor_samples) >= 10:
            # Use median of recent samples as noise floor
            self.noise_floor = np.median(list(self.noise_floor_samples))

    def _check_webrtc_vad(self, audio_chunk: bytes) -> bool:
        """
        Check voice activity using WebRTC VAD

        Args:
            audio_chunk: Raw audio bytes

        Returns:
            True if voice detected by WebRTC VAD
        """
        try:
            audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
            
            # WebRTC VAD only supports: 8000, 16000, 32000, 48000 Hz
            # If using 44100 Hz, resample to 16000 Hz
            target_rate = 16000
            if self.sample_rate != target_rate:
                # Resample audio to 16000 Hz
                num_samples = int(len(audio_array) * target_rate / self.sample_rate)
                audio_array = signal.resample(audio_array, num_samples).astype(np.int16)
                vad_sample_rate = target_rate
            else:
                vad_sample_rate = self.sample_rate
            
            # VAD requires specific frame durations (10, 20, or 30 ms)
            frame_duration = 30  # ms
            frame_size = int(vad_sample_rate * frame_duration / 1000)

            # Pad or trim to correct size
            if len(audio_array) < frame_size:
                audio_array = np.pad(audio_array, (0, frame_size - len(audio_array)))
            elif len(audio_array) > frame_size:
                audio_array = audio_array[:frame_size]

            audio_bytes = audio_array.tobytes()
            return self.vad.is_speech(audio_bytes, vad_sample_rate)

        except Exception as e:
            logger.debug(f"WebRTC VAD error: {e}")
            return False

    def reset(self):
        """Reset voice detection state"""
        self.is_voice_active = False
        self.voice_frames = 0
        self.silence_frames = 0
        self.noise_floor_samples.clear()
        logger.debug("Voice detector reset")

    def get_confidence(self) -> float:
        """
        Get voice detection confidence (0-1)

        Returns:
            Confidence score
        """
        if not self.is_voice_active:
            return 0.0

        confidence = min(1.0, self.voice_frames / (self.min_voice_frames * 3))
        return confidence


if __name__ == "__main__":
    # Test voice activity detection
    logging.basicConfig(level=logging.INFO)

    config = {
        'audio': {
            'input': {
                'sample_rate': 16000,
                'chunk_size': 1024
            },
            'processing': {
                'vad_aggressiveness': 2,
                'silence_threshold': 500
            }
        }
    }

    vad = VoiceActivityDetector(config)
    print("Voice Activity Detector initialized")
    print("Test with actual audio input to see results")
