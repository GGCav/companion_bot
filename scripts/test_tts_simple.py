#!/usr/bin/env python3
"""
Simple TTS Test Script
Tests text-to-speech with basic speech and all emotion voices
No hardware detection - just pure TTS functionality
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import yaml
from llm.tts_engine import TTSEngine


def load_config():
    """Load configuration from settings.yaml"""
    config_path = Path(__file__).parent.parent / 'config' / 'settings.yaml'

    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)

    try:
        with open(config_path) as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)


def test_basic_speech(tts):
    """Test basic neutral speech"""
    print("\n1. Testing basic speech...")
    print("   Speaking: 'Hello! TTS test.'")
    tts.speak("Hello! TTS test.", wait=True)
    print("   Done")


def test_all_emotions(tts):
    """Test all 12 emotion voices"""
    print("\n2. Testing all emotion voices...")
    print("   (Listen for rate, pitch, and volume changes)")

    emotions = [
        ('happy', "I'm so happy to see you!"),
        ('excited', "This is so exciting!"),
        ('sad', "I feel sad when you're away."),
        ('sleepy', "I'm feeling so sleepy..."),
        ('angry', "I'm angry about this!"),
        ('scared', "That was scary!"),
        ('loving', "I love you so much!"),
        ('playful', "Let's play together!"),
        ('curious', "I wonder what that is?"),
        ('lonely', "I'm feeling lonely."),
        ('bored', "This is boring."),
        ('surprised', "Wow! What a surprise!"),
    ]

    for i, (emotion, text) in enumerate(emotions, 1):
        print(f"   [{i}/12] {emotion:12s} - {text}")
        tts.speak_with_emotion(text, emotion, wait=True)
        time.sleep(0.3)  # Brief pause between emotions

    print("   Done")


def test_multi_emotion_speech(tts):
    """Test multi-emotion speech with transitions"""
    print("\n3. Testing multi-emotion speech...")
    print("   (Single response with 3 emotion transitions)")

    segments = [
        ('happy', "Hi there! I'm glad to see you!"),
        ('curious', "What have you been up to?"),
        ('excited', "I can't wait to hear about it!"),
    ]

    for emotion, text in segments:
        print(f"   [{emotion}] {text}")

    tts.speak_segments_with_emotions(segments, wait=True)
    print("   Done")


def main():
    """Main test function"""
    print("="*70)
    print("TTS Test Script")
    print("="*70)
    print("\nThis script tests TTS output with emotion modulation.")
    print("Make sure your speakers/headphones are connected.")

    # Load config and initialize TTS
    print("\nInitializing TTS engine...")
    try:
        config = load_config()
        tts = TTSEngine(config)
        print("TTS engine initialized")
    except Exception as e:
        print(f"Error initializing TTS: {e}")
        return 1

    # Run tests
    try:
        test_basic_speech(tts)
        test_all_emotions(tts)
        test_multi_emotion_speech(tts)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1

    except Exception as e:
        print(f"\nError during test: {e}")
        return 1

    finally:
        # Cleanup
        print("\nCleaning up...")
        tts.cleanup()

    # Success
    print("\n" + "="*70)
    print("All tests complete!")
    print("="*70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
