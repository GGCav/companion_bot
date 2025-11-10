#!/usr/bin/env python3
"""
Voice Input Test Script
Test mini microphone with Whisper STT
"""

import sys
import logging
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import yaml
from llm.voice_pipeline import VoicePipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main test function"""
    print("=" * 70)
    print("🎤 Voice Input Test - Mini Microphone + Whisper")
    print("=" * 70)

    # Load configuration
    config_path = Path(__file__).parent.parent / 'config' / 'settings.yaml'

    if not config_path.exists():
        print("❌ Config file not found at:", config_path)
        print("Run setup.sh first!")
        return 1

    print("\n📋 Loading configuration...")
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Show audio settings
    print("\n🔧 Audio Configuration:")
    print(f"  Sample Rate: {config['audio']['input']['sample_rate']} Hz")
    print(f"  Channels: {config['audio']['input']['channels']}")
    print(f"  Chunk Size: {config['audio']['input']['chunk_size']}")
    print(f"  VAD Aggressiveness: {config['audio']['processing']['vad_aggressiveness']}")

    print("\n🤖 Whisper Configuration:")
    print(f"  Model: {config['speech']['stt']['whisper']['model_size']}")
    print(f"  Device: {config['speech']['stt']['whisper']['device']}")
    print(f"  Language: {config['speech']['stt']['language']}")

    # Initialize pipeline
    print("\n🚀 Initializing voice pipeline...")
    try:
        pipeline = VoicePipeline(config)
    except Exception as e:
        print(f"❌ Failed to initialize pipeline: {e}")
        return 1

    # Test microphone
    print("\n🎙️  Testing microphone...")
    if not pipeline.test_microphone():
        print("❌ Microphone test failed!")
        print("\nTroubleshooting:")
        print("  1. Check if mini microphone is plugged in")
        print("  2. Run: arecord -l")
        print("  3. Test with: arecord -D hw:1,0 -d 3 test.wav && aplay test.wav")
        return 1

    print("✅ Microphone working!")

    # Set up transcription tracking
    transcription_count = 0

    def on_transcription(result):
        nonlocal transcription_count
        transcription_count += 1

        print("\n" + "=" * 70)
        print(f"📝 TRANSCRIPTION #{transcription_count}")
        print("=" * 70)
        print(f"Text:       {result['text']}")
        print(f"Language:   {result['language']}")
        print(f"Confidence: {result['confidence']:.2%}")
        print(f"Duration:   {result['duration']:.2f}s")
        print("=" * 70)

    def on_speech_start():
        print("\n🎤 [LISTENING] Speak now...")

    def on_speech_end():
        print("⏳ [PROCESSING] Transcribing with Whisper...")

    pipeline.set_transcription_callback(on_transcription)
    pipeline.set_speech_callbacks(on_speech_start, on_speech_end)

    # Start pipeline
    print("\n✅ Voice pipeline ready!")
    print("\n" + "=" * 70)
    print("Instructions:")
    print("  1. Speak clearly into your mini microphone")
    print("  2. The system will detect when you start/stop speaking")
    print("  3. Wait for transcription results")
    print("  4. Press Ctrl+C to stop")
    print("=" * 70)
    print("\n🎯 Starting voice recognition...\n")

    try:
        pipeline.start()

        # Run for a specified time or until interrupted
        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping voice pipeline...")

    finally:
        pipeline.cleanup()

        # Show final statistics
        stats = pipeline.get_statistics()

        print("\n" + "=" * 70)
        print("📊 Session Statistics")
        print("=" * 70)
        print(f"Total Utterances:         {stats['total_utterances']}")
        print(f"Total Transcription Time: {stats['total_transcription_time']:.2f}s")
        print(f"Avg Time per Utterance:   {stats['avg_transcription_time']:.2f}s")
        print(f"Last Transcription Time:  {stats['last_transcription_time']:.2f}s")
        print("=" * 70)

        if stats['total_utterances'] > 0:
            print("\n✅ Test completed successfully!")
            print(f"   Transcribed {stats['total_utterances']} utterance(s)")
        else:
            print("\n⚠️  No speech detected")
            print("   Try speaking louder or closer to the microphone")

    return 0


if __name__ == "__main__":
    sys.exit(main())
