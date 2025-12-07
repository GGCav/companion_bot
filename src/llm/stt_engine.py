"""
Speech-to-Text Engine
Optimized for mini microphone with OpenAI Whisper
"""

import whisper
import numpy as np
import logging
import time
import tempfile
import wave
from pathlib import Path
from typing import Optional, Dict
import torch

logger = logging.getLogger(__name__)


class STTEngine:
    """Speech-to-Text engine using OpenAI Whisper, optimized for mini microphones"""

    def __init__(self, config: dict):
        """
        Initialize STT engine with Whisper

        Args:
            config: Configuration dictionary from settings.yaml
        """
        self.config = config
        self.stt_config = config['speech']['stt']
        self.whisper_config = self.stt_config['whisper']
        self.audio_config = config['audio']['input']
        self.target_sample_rate = self.whisper_config.get(
            'target_sample_rate', self.audio_config['sample_rate']
        )
        self.max_duration = float(self.whisper_config.get('max_duration', 8.0))

        # Model selection
        self.model_size = self.whisper_config['model_size']  # tiny, base, small
        self.device = self.whisper_config.get('device', 'cpu')
        self.language = self.stt_config.get('language', 'en')

        # Performance tracking
        self.total_transcriptions = 0
        self.total_time = 0.0
        self.avg_confidence = 0.0

        # Load Whisper model
        logger.info(f"Loading Whisper model: {self.model_size} on {self.device}")
        self.model = self._load_model()

        logger.info("STT Engine initialized with Whisper")

    def _load_model(self) -> whisper.Whisper:
        """
        Load Whisper model with optimizations

        Returns:
            Loaded Whisper model
        """
        try:
            # Load model
            model = whisper.load_model(
                self.model_size,
                device=self.device
            )

            # Optimize for inference
            if self.device == 'cpu':
                # CPU optimizations
                logger.info("Applying CPU optimizations")
                # Use FP32 for CPU (more stable than FP16)
            else:
                # GPU optimizations
                logger.info("Applying GPU optimizations")
                model = model.half()  # Use FP16 on GPU

            logger.info(f"Whisper model '{self.model_size}' loaded successfully")
            return model

        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            # Fallback to smallest model
            logger.warning("Falling back to 'tiny' model")
            return whisper.load_model('tiny', device='cpu')

    def transcribe_audio(self, audio_data: bytes) -> Dict[str, any]:
        """
        Transcribe audio data to text

        Args:
            audio_data: Raw audio bytes (int16, mono)

        Returns:
            Dictionary with 'text', 'language', 'confidence', 'duration'
        """
        start_time = time.time()

        try:
            processed_audio, sample_rate = self._prepare_audio(audio_data)

            # Save audio to temporary WAV file (Whisper expects file)
            temp_file = self._save_temp_audio(processed_audio, sample_rate)

            # Transcribe with Whisper
            result = self.model.transcribe(
                str(temp_file),
                language=self.language if self.language != 'auto' else None,
                fp16=(self.device != 'cpu'),
                verbose=False,
                condition_on_previous_text=False,  # Better for short utterances
                temperature=0.0,  # Deterministic output
                compression_ratio_threshold=2.4,
                logprob_threshold=-1.0,
                no_speech_threshold=0.6
            )

            # Clean up temp file
            temp_file.unlink()

            # Extract results
            text = result['text'].strip()
            detected_language = result.get('language', self.language)

            # Calculate average confidence from segments
            segments = result.get('segments', [])
            if segments:
                confidences = []
                for segment in segments:
                    # Whisper doesn't directly provide confidence, estimate from logprobs
                    avg_logprob = segment.get('avg_logprob', -1.0)
                    # Convert logprob to approximate confidence (0-1)
                    confidence = np.exp(avg_logprob)
                    confidences.append(confidence)
                avg_confidence = np.mean(confidences)
            else:
                avg_confidence = 0.5  # Default if no segments

            # Performance tracking
            duration = time.time() - start_time
            self.total_transcriptions += 1
            self.total_time += duration
            self.avg_confidence = (self.avg_confidence * (self.total_transcriptions - 1) + avg_confidence) / self.total_transcriptions

            logger.info(f"Transcribed: '{text}' (lang: {detected_language}, conf: {avg_confidence:.2f}, time: {duration:.2f}s)")

            return {
                'text': text,
                'language': detected_language,
                'confidence': avg_confidence,
                'duration': duration,
                'segments': segments
            }

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {
                'text': '',
                'language': 'unknown',
                'confidence': 0.0,
                'duration': time.time() - start_time,
                'error': str(e)
            }

    def transcribe_audio_array(self, audio_array: np.ndarray, sample_rate: int = 16000) -> Dict[str, any]:
        """
        Transcribe audio from numpy array

        Args:
            audio_array: Audio as numpy array (float32, -1 to 1)
            sample_rate: Sample rate in Hz

        Returns:
            Dictionary with transcription results
        """
        # Convert float32 to int16
        if audio_array.dtype == np.float32 or audio_array.dtype == np.float64:
            audio_array = (audio_array * 32767).astype(np.int16)

        # Convert to bytes
        audio_bytes = audio_array.tobytes()

        return self.transcribe_audio(audio_bytes)

    def _prepare_audio(self, audio_data: bytes) -> tuple[bytes, int]:
        """
        Resample and trim audio before transcription.
        """
        src_rate = self.audio_config['sample_rate']
        target_rate = self.target_sample_rate

        # Convert bytes to numpy array
        samples = np.frombuffer(audio_data, dtype=np.int16)

        # Trim to max_duration
        max_samples = int(self.max_duration * src_rate)
        if samples.size > max_samples:
            samples = samples[-max_samples:]

        # Resample if needed
        if src_rate != target_rate and samples.size > 0:
            src_len = samples.size
            target_len = int(src_len * target_rate / src_rate)
            if target_len > 0:
                x_old = np.linspace(0, 1, src_len, endpoint=False)
                x_new = np.linspace(0, 1, target_len, endpoint=False)
                samples = np.interp(x_new, x_old, samples).astype(np.int16)
                src_rate = target_rate

        return samples.tobytes(), src_rate

    def _save_temp_audio(self, audio_data: bytes, sample_rate: int) -> Path:
        """
        Save audio data to temporary WAV file

        Args:
            audio_data: Raw audio bytes (int16)

        Returns:
            Path to temporary file
        """
        # Create temporary file
        temp_file = Path(tempfile.mktemp(suffix='.wav'))

        try:
            # Write WAV file
            with wave.open(str(temp_file), 'wb') as wf:
                wf.setnchannels(self.audio_config['channels'])
                wf.setsampwidth(2)  # 16-bit = 2 bytes
                wf.setframerate(sample_rate)
                wf.writeframes(audio_data)

            return temp_file

        except Exception as e:
            logger.error(f"Failed to save temporary audio: {e}")
            raise

    def transcribe_from_file(self, audio_file: str) -> Dict[str, any]:
        """
        Transcribe audio from file

        Args:
            audio_file: Path to audio file

        Returns:
            Dictionary with transcription results
        """
        try:
            # Read audio file
            with wave.open(audio_file, 'rb') as wf:
                audio_data = wf.readframes(wf.getnframes())

            return self.transcribe_audio(audio_data)

        except Exception as e:
            logger.error(f"Failed to transcribe file {audio_file}: {e}")
            return {
                'text': '',
                'language': 'unknown',
                'confidence': 0.0,
                'duration': 0.0,
                'error': str(e)
            }

    def get_supported_languages(self) -> list:
        """
        Get list of supported languages

        Returns:
            List of language codes
        """
        return list(whisper.tokenizer.LANGUAGES.keys())

    def get_performance_stats(self) -> Dict[str, float]:
        """
        Get performance statistics

        Returns:
            Dictionary with performance metrics
        """
        avg_time = self.total_time / max(1, self.total_transcriptions)

        return {
            'total_transcriptions': self.total_transcriptions,
            'total_time': self.total_time,
            'avg_time_per_transcription': avg_time,
            'avg_confidence': self.avg_confidence,
            'model_size': self.model_size,
            'device': self.device
        }

    def change_language(self, language: str):
        """
        Change transcription language

        Args:
            language: Language code (e.g., 'en', 'es', 'fr') or 'auto'
        """
        if language != 'auto' and language not in self.get_supported_languages():
            logger.warning(f"Language '{language}' not supported, using 'auto'")
            language = 'auto'

        self.language = language
        logger.info(f"Language changed to: {language}")

    def cleanup(self):
        """Clean up resources"""
        # Clear model from memory
        if hasattr(self, 'model'):
            del self.model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        logger.info("STT Engine cleanup complete")


# Optimized wrapper for real-time transcription
class RealtimeSTT:
    """Real-time speech-to-text optimized for mini microphone"""

    def __init__(self, config: dict, stt_engine: STTEngine = None):
        """
        Initialize real-time STT

        Args:
            config: Configuration dictionary
            stt_engine: Optional existing STT engine
        """
        self.config = config
        self.stt_engine = stt_engine or STTEngine(config)

        # Audio preprocessing for mini microphones
        self.sample_rate = config['audio']['input']['sample_rate']
        self.normalize_audio = True
        self.noise_reduction = config['audio']['processing']['noise_reduction']

        logger.info("Real-time STT initialized")

    def transcribe(self, audio_data: bytes) -> Dict[str, any]:
        """
        Transcribe with preprocessing optimized for mini microphones

        Args:
            audio_data: Raw audio bytes

        Returns:
            Transcription result
        """
        # Preprocess audio
        audio_array = np.frombuffer(audio_data, dtype=np.int16)

        # Normalize volume (mini mics often have low volume)
        if self.normalize_audio:
            audio_array = self._normalize_audio(audio_array)

        # Apply noise reduction if enabled
        if self.noise_reduction:
            audio_array = self._reduce_noise(audio_array)

        # Convert back to bytes
        processed_audio = audio_array.tobytes()

        # Transcribe
        return self.stt_engine.transcribe_audio(processed_audio)

    def _normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """
        Normalize audio volume

        Args:
            audio: Audio array

        Returns:
            Normalized audio
        """
        # Calculate RMS
        rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))

        if rms < 100:  # Very quiet
            # Amplify
            target_rms = 3000
            gain = target_rms / (rms + 1e-6)
            gain = min(gain, 10.0)  # Limit max gain
            audio = (audio.astype(np.float32) * gain).astype(np.int16)
            logger.debug(f"Audio normalized, gain: {gain:.2f}x")

        return audio

    def _reduce_noise(self, audio: np.ndarray) -> np.ndarray:
        """
        Simple noise reduction for mini microphones

        Args:
            audio: Audio array

        Returns:
            Noise-reduced audio
        """
        # Simple high-pass filter to remove low-frequency noise
        from scipy import signal

        # High-pass filter at 80 Hz (removes rumble/hum)
        sos = signal.butter(4, 80, 'hp', fs=self.sample_rate, output='sos')
        filtered = signal.sosfilt(sos, audio.astype(np.float32))

        return filtered.astype(np.int16)

    def cleanup(self):
        """Clean up resources"""
        if self.stt_engine:
            self.stt_engine.cleanup()


if __name__ == "__main__":
    # Test STT engine
    logging.basicConfig(level=logging.INFO)

    # Mock config
    config = {
        'speech': {
            'stt': {
                'provider': 'whisper',
                'language': 'en',
                'whisper': {
                    'model_size': 'base',
                    'device': 'cpu'
                }
            }
        },
        'audio': {
            'input': {
                'sample_rate': 16000,
                'channels': 1
            },
            'processing': {
                'noise_reduction': True
            }
        }
    }

    print("Initializing STT Engine with Whisper...")
    stt = STTEngine(config)

    print(f"\nSupported languages: {len(stt.get_supported_languages())} languages")
    print(f"Model: {stt.model_size} on {stt.device}")

    # Test with a sample audio file (if available)
    print("\nReady for transcription!")
    print("Use the RealtimeSTT class with AudioInput for live transcription.")

    # Show performance stats
    stats = stt.get_performance_stats()
    print(f"\nPerformance: {stats}")

    stt.cleanup()
    print("\nTest complete!")
