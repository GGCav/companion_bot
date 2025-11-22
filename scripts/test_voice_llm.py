#!/usr/bin/env python3
"""
Voice + LLM Test Script
Test voice input with LLM conversation (text output, no TTS)
"""

import sys
import logging
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import yaml
from llm.voice_pipeline import VoicePipeline
from llm import ConversationManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main test function"""
    print("\n" + "="*70)
    print("🎤 VOICE + LLM TEST (Text Output Only)")
    print("="*70)

    # Load configuration
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

    # Initialize components
    print("\n📦 Initializing components...")

    try:
        # Voice input
        voice_input = VoicePipeline(config)
        print("   ✅ Voice input initialized")

        # Conversation manager (LLM)
        conversation_manager = ConversationManager(config)
        print("   ✅ Conversation manager initialized")

    except Exception as e:
        print(f"❌ Failed to initialize components: {e}")
        logger.error("Initialization error", exc_info=True)
        return 1

    # Check Ollama availability
    if not conversation_manager.llm.is_available:
        print("\n⚠️  WARNING: Ollama not available!")
        print("   Starting Ollama: ollama serve")
        print("   Pull model: ollama pull qwen2.5:0.5b")
        print("\n   Continuing with fallback responses...")

    # Start listening
    print("\n" + "="*70)
    print("🎤 LISTENING MODE")
    print("="*70)
    print("\nSpeak into your microphone...")
    print("(The bot will respond with text only, no speech)")
    print("\nPress Ctrl+C to exit")
    print("─" * 70)

    conversation_count = 0

    # Start the voice pipeline
    voice_input.start()

    try:
        while True:
            # Wait for voice input (blocks until speech detected or timeout)
            print("\n🎤 Listening...")
            result = voice_input.wait_for_transcription(timeout=30.0)

            if result is None:
                print("   No speech detected, trying again...")
                continue

            # Extract transcription from result
            transcription = result.get('text', '').strip()
            confidence = result.get('confidence', 0.0)

            if not transcription:
                print("   Could not transcribe, trying again...")
                continue

            # Display what user said
            print(f"\n👤 You said: {transcription} (confidence: {confidence:.0%})")

            # Check for exit command
            if transcription.lower() in ['quit', 'exit', 'goodbye', 'bye']:
                print("\n👋 Goodbye!")
                break

            # Generate LLM response
            print("🤖 Thinking...")
            start_time = time.time()

            response, metadata = conversation_manager.process_user_input(
                transcription
            )

            response_time = time.time() - start_time

            # Display bot response
            print(f"\n🤖 Bot ({metadata['emotion']}): {response}")

            # Display metadata every 3 conversations
            conversation_count += 1
            if conversation_count % 3 == 0:
                print("\n   📊 Metadata:")
                print(f"      ⏱️  Response time: {response_time:.2f}s")
                print(f"      🎭 Emotion: {metadata['emotion']}")
                print(f"      📊 Tokens: {metadata['tokens']}")
                print(f"      ⚡ Energy: {metadata['energy']:.0%}")
                print(f"      💬 Messages: {metadata['message_count']}")
                if metadata.get('fallback'):
                    print("      ⚠️  Using fallback response")

            print("\n" + "─" * 70)

    except KeyboardInterrupt:
        print("\n\n⏹️  Stopped by user")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error("Runtime error", exc_info=True)
        return 1

    finally:
        # Clean up voice pipeline
        voice_input.cleanup()

    # Show summary
    print("\n" + "="*70)
    print("SESSION SUMMARY")
    print("="*70)

    summary = conversation_manager.get_conversation_summary()
    print(summary)

    print("\n✅ Test complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
