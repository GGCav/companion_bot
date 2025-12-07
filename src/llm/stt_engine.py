"""
Speech-to-Text Engine
Optimized for mini microphone with Whisper or Faster-Whisper
"""

import logging
import time
import tempfile
import wave
from pathlib import Path
from typing import Optional, Dict

import numpy as np
import torch

try:
    import whisper  # type: ignore
except ImportError:  # pragma: no cover
    whisper = None  # type: ignore

try:
    from faster_whisper import WhisperModel  # type: ignore
except ImportError:  # pragma: no cover
    WhisperModel = None  # type: ignore

logger = logging.getLogger(__name__)


class STTEngine:
    """Speech-to-Text engine using Whisper or Faster-Whisper"""

    def __init__(self, config: dict):
        """
        Initialize STT engine with selected provider

        Args:
            config: Configuration dictionary from settings.yaml
        """
        self.config = config
        self.stt_config = config['speech']['stt']
        self.whisper_config = self.stt_config.get('whisper', {})
        self.fw_config = self.stt_config.get('faster_whisper', {})
        self.audio_config = config['audio']['input']

        # Provider selection
        self.provider = self.stt_config.get('provider', 'whisper')
        self.model_size = self.whisper_config.get('model_size', 'tiny')
        self.device = self.whisper_config.get('device', 'cpu')
        self.language = self.stt_config.get('language', 'en')
        if self.provider == 'faster-whisper':
            self.model_size = self.fw_config.get('model_size', 'tiny')
            self.device = self.fw_config.get('device', 'cpu')
            self.compute_type = self.fw_config.get('compute_type', 'int8')
        else:
            self.compute_type = None

        # Performance tracking
        self.total_transcriptions = 0
        self.total_time = 0.0
        self.avg_confidence = 0.0

        # Load model
        logger.info(
            "Loading STT model (%s): %s on %s",
            self.provider,
            self.model_size,
            self.device,
        )
        self.model = self._load_model()

        logger.info("STT Engine initialized with provider: %s", self.provider)

    def _load_model(self):
        """
        Load STT model with optimizations
        """
        try:
            if self.provider == 'faster-whisper':
                if WhisperModel is None:
                    raise ImportError("faster-whisper not installed")
                compute_type = self.compute_type or 'int8'
                model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=compute_type
                )
                logger.info(
                    "Faster-Whisper model '%s' loaded (%s, %s)",
                    self.model_size,
                    self.device,
                    compute_type,
                )
                return model

            # Default to openai/whisper
            if whisper is None:
                raise ImportError("openai-whisper not installed")
            model = whisper.load_model(
                self.model_size,
                device=self.device
            )

            # Optimize for inference
            if self.device != 'cpu':
                logger.info("Applying GPU optimizations")
                model = model.half()
            else:
                logger.info("Using CPU precision (fp32)")

            logger.info("Whisper model '%s' loaded successfully", self.model_size)
            return model

        except Exception as e:
            logger.error("Failed to load STT model: %s", e)
            # Fallback to smallest
            if self.provider == 'faster-whisper' and WhisperModel is not None:
                return WhisperModel('tiny', device='cpu', compute_type='int8')
            if whisper is not None:
                return whisper.load_model('tiny', device='cpu')
            raise

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
            # Save audio to temporary WAV file (Whisper expects file)
            temp_file = self._save_temp_audio(audio_data)

            if self.provider == 'faster-whisper':
                result = self._transcribe_faster_whisper(str(temp_file))
            else:
                result = self._transcribe_whisper(str(temp_file))

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

    def _save_temp_audio(self, audio_data: bytes) -> Path:
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
                wf.setframerate(self.audio_config['sample_rate'])
                wf.writeframes(audio_data)

            return temp_file

        except Exception as e:
            logger.error(f"Failed to save temporary audio: {e}")
            raise

    def _transcribe_whisper(self, file_path: str) -> Dict:
        if whisper is None:
            raise RuntimeError("Whisper not installed")
        return self.model.transcribe(
            file_path,
            language=self.language if self.language != 'auto' else None,
            fp16=(self.device != 'cpu'),
            verbose=False,
            condition_on_previous_text=False,
            temperature=0.0,
            compression_ratio_threshold=2.4,
            logprob_threshold=-1.0,
            no_speech_threshold=0.6,
        )

    def _transcribe_faster_whisper(self, file_path: str) -> Dict:
        if WhisperModel is None:
            raise RuntimeError("faster-whisper not installed")

        segments, info = self.model.transcribe(
            file_path,
            language=self.language if self.language != 'auto' else None,
            beam_size=1,
            temperature=0.0,
        )

        text_parts = []
        confidences = []
        fw_segments = []
        for segment in segments:
            text_parts.append(segment.text.strip())
            fw_segments.append(
                {
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text.strip(),
                    'avg_logprob': segment.avg_logprob,
                }
            )
            if segment.avg_logprob is not None:
                confidences.append(np.exp(segment.avg_logprob))

        text = " ".join(text_parts).strip()
        avg_conf = float(np.mean(confidences)) if confidences else 0.5

        return {
            'text': text,
            'language': info.language or self.language,
            'confidence': avg_conf,
            'duration': info.duration if info else 0.0,
            'segments': fw_segments,
        }

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
