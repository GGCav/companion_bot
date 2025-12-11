#!/usr/bin/env python3
"""
Expression Pipeline - Standalone Demo
Demonstrates emotion display on piTFT with smooth transitions
Based on two_collide.py reference implementation
"""

import sys
import time
import logging
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import yaml
from expression import EmotionDisplay


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from settings.yaml"""
    config_path = Path(__file__).parent.parent / 'config' / 'settings.yaml'

    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        logger.info("Configuration loaded")
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)


def demo_emotion_cycle(display: EmotionDisplay, emotions: list, duration: float = 3.0):
    """
    Cycle through emotions with smooth transitions

    Args:
        display: EmotionDisplay instance
        emotions: List of emotion names to cycle through
        duration: How long to show each emotion (seconds)
    """
    logger.info(f"Starting emotion cycle through {len(emotions)} emotions")

    for emotion in emotions:
        logger.info(f"Showing emotion: {emotion}")
        display.set_emotion(emotion, transition_duration=0.5)
        time.sleep(duration)


def demo_speaking_animation(display: EmotionDisplay):
    """
    Demonstrate speaking animation

    Args:
        display: EmotionDisplay instance
    """
    logger.info("Demonstrating speaking animation")

    display.set_emotion('happy', transition_duration=0.5)
    time.sleep(1.0)


    display.set_speaking(True)
    logger.info("Speaking animation started")
    time.sleep(3.0)


    display.set_speaking(False)
    logger.info("Speaking animation stopped")
    time.sleep(1.0)


def demo_listening_state(display: EmotionDisplay):
    """
    Demonstrate listening state

    Args:
        display: EmotionDisplay instance
    """
    logger.info("Demonstrating listening state")


    display.set_listening(True)
    logger.info("Listening state activated")
    time.sleep(3.0)


    display.set_listening(False)
    logger.info("Listening state deactivated")
    time.sleep(1.0)


def main():
    """Main demo function"""
    print("\n" + "="*70)
    print("🎭 EMOTION EXPRESSION PIPELINE DEMO")
    print("="*70)
    print("\nThis demo cycles through emotions with smooth transitions.")
    print("Press GPIO pin 27 to exit (or Ctrl+C)")
    print("─" * 70)


    config = load_config()


    try:
        display = EmotionDisplay(config)
        logger.info("EmotionDisplay initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize display: {e}")
        logger.error("Make sure emotion sprites exist in src/display/")
        return 1


    display.start()
    logger.info("Display started")


    all_emotions = [
        'happy',
        'excited',
        'curious',
        'loving',
        'playful',
        'surprised',
        'bored',
        'sad',
        'lonely',
        'sleepy',
        'scared',
        'angry',
    ]

    try:

        print("\n🔄 Demo 1: Cycling through all 12 emotions...")
        demo_emotion_cycle(display, all_emotions, duration=2.5)


        print("\n🗣️  Demo 2: Speaking animation...")
        demo_speaking_animation(display)


        print("\n🎤 Demo 3: Listening state...")
        demo_listening_state(display)


        print("\n⚡ Demo 4: Rapid emotion changes...")
        rapid_emotions = ['excited', 'happy', 'surprised', 'playful']
        demo_emotion_cycle(display, rapid_emotions, duration=1.5)


        print("\n🌅 Demo 5: Slow smooth transitions...")
        display.set_emotion('happy', transition_duration=2.0)
        time.sleep(3.0)
        display.set_emotion('sad', transition_duration=2.0)
        time.sleep(3.0)
        display.set_emotion('loving', transition_duration=2.0)
        time.sleep(3.0)

        print("\n✅ Demo complete!")
        print("Press GPIO pin 27 to exit, or waiting 5 seconds...")
        time.sleep(5.0)

    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")

    except Exception as e:
        logger.error(f"Demo error: {e}", exc_info=True)
        return 1

    finally:

        print("\n🧹 Cleaning up...")
        display.cleanup()
        print("✅ Cleanup complete")


    print("\n" + "="*70)
    print("DEMO SUMMARY")
    print("="*70)
    print("✅ All emotion transitions demonstrated")
    print("✅ Speaking animation tested")
    print("✅ Listening state tested")
    print("\nThe expression pipeline is ready for integration!")
    print("="*70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
