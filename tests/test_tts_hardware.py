#!/usr/bin/env python3
"""
TTS Hardware Test Script
Tests TTS output with wm8960-soundcard and all emotion voices
"""

import sys
import logging
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import yaml
from llm.tts_engine import TTSEngine


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_audio_device():
    """Display audio device information"""
    print("\n" + "="*70)
    print("AUDIO DEVICE INFORMATION")
    print("="*70)

    try:
        import subprocess


        print("\n📻 ALSA Playback Devices:")
        result = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("   ⚠️  Could not list ALSA devices")


        print("\n🔊 Testing default audio device:")
        print("   Playing a brief test tone...")
        result = subprocess.run(
            ['speaker-test', '-t', 'wav', '-c', '2', '-l', '1'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("   ✅ Audio playback successful!")
        else:
            print("   ❌ Audio test failed")
            print(result.stderr)

    except FileNotFoundError:
        print("   ⚠️  ALSA tools not found (install with: sudo apt install alsa-utils)")
    except Exception as e:
        print(f"   ⚠️  Error checking audio: {e}")


def test_tts_engine(config):
    """Test TTS engine with basic speech"""
    print("\n" + "="*70)
    print("TTS ENGINE TEST")
    print("="*70)

    try:
        print("\n📦 Initializing TTS engine...")
        tts = TTSEngine(config)
        print("   ✅ TTS engine initialized")


        print("\n⚙️  TTS Configuration:")
        print(f"   Provider: {config.get('speech', {}).get('tts', {}).get('provider', 'pyttsx3')}")
        tts_config = config.get('speech', {}).get('tts', {}).get('pyttsx3', {})
        print(f"   Rate: {tts_config.get('rate', 150)} words/min")
        print(f"   Volume: {tts_config.get('volume', 0.9)}")
        print(f"   Pitch: {tts_config.get('pitch', 1.5)}")


        print("\n🔊 Testing basic speech:")
        print("   Speaking: 'Hello! Audio test.'")
        tts.speak("Hello! Audio test.", wait=True)
        print("   ✅ Basic speech complete")

        return tts

    except Exception as e:
        print(f"   ❌ TTS engine failed: {e}")
        logger.error("TTS initialization error", exc_info=True)
        return None


def test_emotion_voices(tts):
    """Test all emotion voices"""
    print("\n" + "="*70)
    print("EMOTION VOICE TEST")
    print("="*70)
    print("\nTesting all 12 emotion states...")
    print("(Listen for rate, pitch, and volume changes)")
    print("")

    emotions_to_test = [
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

    for i, (emotion, text) in enumerate(emotions_to_test, 1):
        print(f"[{i}/12] {emotion.upper():12s} - {text}")
        try:
            tts.speak_with_emotion(text, emotion, wait=True)
        except Exception as e:
            print(f"        ❌ Error: {e}")

    print("\n✅ All emotion voices tested")


def test_multi_emotion_speech(tts):
    """Test multi-emotion speech with transitions"""
    print("\n" + "="*70)
    print("MULTI-EMOTION SPEECH TEST")
    print("="*70)
    print("\nTesting emotion transitions within a single response...")
    print("")


    segments = [
        ('happy', "Hi there! I'm glad to see you!"),
        ('curious', "What have you been up to?"),
        ('excited', "I can't wait to hear about it!"),
    ]

    print("Segments:")
    for emotion, text in segments:
        print(f"  [{emotion}] {text}")

    print("\n🔊 Speaking with emotion transitions...")
    try:
        tts.speak_segments_with_emotions(segments, wait=True)
        print("✅ Multi-emotion speech complete")
    except Exception as e:
        print(f"❌ Multi-emotion speech failed: {e}")
        logger.error("Multi-emotion speech error", exc_info=True)


def test_statistics(tts):
    """Display TTS statistics"""
    print("\n" + "="*70)
    print("TTS STATISTICS")
    print("="*70)

    stats = tts.get_statistics()
    print(f"\n📊 Performance Stats:")
    print(f"   Total utterances: {stats['total_utterances']}")
    print(f"   Total duration: {stats['total_duration']:.2f}s")
    print(f"   Current emotion: {stats['current_emotion'] or 'neutral'}")
    print(f"   Provider: {stats['provider']}")


def main():
    """Main test function"""
    print("\n" + "="*70)
    print("🔊 TTS HARDWARE TEST - wm8960-soundcard")
    print("="*70)
    print("\nThis script tests TTS output with your audio hardware.")
    print("Make sure speakers are connected to the wm8960-soundcard.")
    print("")


    config_path = Path(__file__).parent.parent / 'config' / 'settings.yaml'

    if not config_path.exists():
        print("❌ Config file not found!")
        print(f"   Looking for: {config_path}")
        return 1

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        print("✅ Configuration loaded")
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return 1


    try:

        test_audio_device()


        tts = test_tts_engine(config)
        if not tts:
            print("\n❌ Cannot continue without TTS engine")
            return 1


        test_emotion_voices(tts)


        test_multi_emotion_speech(tts)


        test_statistics(tts)


        print("\n" + "="*70)
        print("CLEANUP")
        print("="*70)
        tts.cleanup()
        print("✅ TTS engine cleanup complete")

    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        return 1

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        logger.error("Test error", exc_info=True)
        return 1


    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print("\n✅ All TTS hardware tests complete!")
    print("\nIf you heard all the test phrases, your audio setup is working correctly.")
    print("The companion bot will now be able to speak using the wm8960-soundcard.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
