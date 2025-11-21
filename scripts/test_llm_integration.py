#!/usr/bin/env python3
"""
LLM Integration Test Script
Test Ollama integration and conversation without voice
"""

import sys
import logging
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import yaml
from llm import OllamaClient, ConversationManager, TTSEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_ollama_connection(config):
    """Test basic Ollama connection"""
    print("\n" + "="*70)
    print("TEST 1: Ollama Connection")
    print("="*70)

    client = OllamaClient(config)

    if client.is_available:
        print("✅ Ollama is running and available")

        # Get model info
        info = client.get_model_info()
        if info:
            print(f"   Model: {info.get('model', 'Unknown')}")
            print(f"   Size: {info.get('size', 0) / 1e9:.2f} GB")

        return True
    else:
        print("❌ Ollama is NOT available")
        print("\n   To fix:")
        print("   1. Start Ollama: ollama serve")
        print(f"   2. Pull model: ollama pull {config['llm']['ollama']['model']}")
        return False


def test_text_generation(config):
    """Test basic text generation"""
    print("\n" + "="*70)
    print("TEST 2: Text Generation")
    print("="*70)

    client = OllamaClient(config)

    if not client.is_available:
        print("⏭️  Skipping (Ollama not available)")
        return False

    print("\nGenerating response...")
    result = client.generate("Say hello in one short sentence!")

    print(f"\n📝 Response: {result['response']}")
    print(f"⏱️  Time: {result['duration']:.2f}s")
    print(f"📊 Tokens: {result['tokens']}")

    return True


def test_personality_prompts(config):
    """Test personality-aware generation"""
    print("\n" + "="*70)
    print("TEST 3: Personality Prompts")
    print("="*70)

    client = OllamaClient(config)

    if not client.is_available:
        print("⏭️  Skipping (Ollama not available)")
        return False

    # Test that LLM autonomously chooses appropriate emotions
    test_prompts = [
        ("Hello! How are you today?", "should express greeting emotion"),
        ("I just won a prize!", "should express excited/happy emotion"),
        ("Tell me something interesting", "should express curious emotion"),
    ]

    for prompt, expected_behavior in test_prompts:
        print(f"\n💬 Testing: '{prompt}'")
        print(f"   Expected: {expected_behavior}")

        result = client.generate_with_personality(
            user_input=prompt,
            user_name="friend"
        )

        response = result['response']
        print(f"   Response: {response}")

        # Verify response includes emotion tag format: [emotion] text
        if response.startswith('[') and ']' in response:
            emotion_end = response.index(']')
            emotion = response[1:emotion_end]
            print(f"   ✅ LLM chose emotion: {emotion}")
        else:
            print("   ⚠️  No emotion tag detected in response")

    return True


def test_conversation_manager(config):
    """Test conversation manager with context"""
    print("\n" + "="*70)
    print("TEST 4: Conversation Manager")
    print("="*70)

    manager = ConversationManager(config)

    if not manager.llm.is_available:
        print("⏭️  Skipping (Ollama not available)")
        return False

    conversation = [
        "Hello! What's your name?",
        "Nice to meet you! How are you feeling?",
        "What do you like to do for fun?"
    ]

    print("\nHaving a conversation...\n")

    for i, msg in enumerate(conversation, 1):
        print(f"[{i}] 👤 You: {msg}")

        response, metadata = manager.process_user_input(msg)

        print(f"    🤖 Bot ({metadata['emotion']}): {response}")
        print(f"    ⏱️  {metadata['response_time']:.2f}s | "
              f"🎭 {metadata['emotion']} | "
              f"⚡ {metadata['energy']:.0%}\n")

        time.sleep(0.5)

    # Show summary
    print("─" * 70)
    print(manager.get_conversation_summary())

    return True


def test_tts_engine(config):
    """Test TTS with emotions"""
    print("\n" + "="*70)
    print("TEST 5: TTS Engine")
    print("="*70)

    tts = TTSEngine(config)

    print("\nAvailable voices:")
    voices = tts.get_available_voices()
    for voice in voices[:3]:  # Show first 3
        print(f"   [{voice['index']}] {voice['name']}")

    print("\nTesting TTS with emotions...")

    test_phrase = "Hello! This is a test."
    emotions_to_test = ['happy', 'sad', 'excited']

    for emotion in emotions_to_test:
        print(f"\n   🎵 Speaking with '{emotion}' emotion...")
        tts.speak(test_phrase, emotion=emotion, wait=True)
        time.sleep(0.3)

    tts.cleanup()
    print("\n✅ TTS test complete")

    return True


def interactive_mode(config):
    """Interactive conversation mode"""
    print("\n" + "="*70)
    print("INTERACTIVE MODE")
    print("="*70)
    print("\nType your messages (or 'quit' to exit)")
    print("─" * 70)

    manager = ConversationManager(config)

    if not manager.llm.is_available:
        print("❌ Ollama not available - cannot run interactive mode")
        return False

    conversation_num = 0

    try:
        while True:
            # Get user input
            user_input = input("\n👤 You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\n👋 Goodbye!")
                break

            # Generate response
            conversation_num += 1
            response, metadata = manager.process_user_input(user_input)

            # Display response
            print(f"🤖 Bot ({metadata['emotion']}): {response}")

            # Show metadata
            if conversation_num % 3 == 0:  # Every 3 messages
                print(f"    [⏱️  {metadata['response_time']:.2f}s | "
                      f"🎭 {metadata['emotion']} | "
                      f"📊 {metadata['tokens']} tokens]")

    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")

    # Show final stats
    print("\n" + "─" * 70)
    print(manager.get_conversation_summary())

    return True


def test_emotion_segments(config):
    """Test that metadata includes emotion_segments for multi-emotion responses"""
    print("\n" + "="*70)
    print("TEST 6: Emotion Segments in Metadata")
    print("="*70)

    manager = ConversationManager(config)

    if not manager.llm.is_available:
        print("⏭️  Skipping (Ollama not available)")
        return False

    print("\n📊 Testing emotion segments...")

    # Test with a prompt that might generate multiple emotions
    response, metadata = manager.process_user_input(
        "Tell me a short story with different emotions!"
    )

    print(f"\n🤖 Response: {response}")

    # Check metadata structure
    assert 'emotion_segments' in metadata, "metadata should include emotion_segments"
    assert isinstance(metadata['emotion_segments'], list), "emotion_segments should be a list"

    segments = metadata['emotion_segments']
    print(f"\n✅ Found {len(segments)} emotion segment(s)")

    # Verify each segment structure
    for i, segment in enumerate(segments, 1):
        assert isinstance(segment, tuple), f"Segment {i} should be a tuple"
        assert len(segment) == 2, f"Segment {i} should have 2 elements (emotion, text)"

        emotion, text = segment
        assert isinstance(emotion, str), f"Segment {i} emotion should be a string"
        assert isinstance(text, str), f"Segment {i} text should be a string"

        print(f"   Segment {i}: ({emotion}) {text[:50]}...")

    print("\n✅ Emotion segments test complete")
    return True


def test_segmented_tts(config):
    """Test segmented TTS with multiple emotions"""
    print("\n" + "="*70)
    print("TEST 7: Segmented TTS")
    print("="*70)

    tts = TTSEngine(config)

    segments = [
        ("excited", "Hello friend!"),
        ("curious", "What are you up to today?"),
        ("happy", "That sounds great!")
    ]

    print(f"\n🔊 Testing segmented speech with {len(segments)} segments...")

    for i, (emotion, text) in enumerate(segments, 1):
        print(f"   Segment {i}: ({emotion}) {text}")

    # Speak all segments
    tts.speak_segments_with_emotions(segments, wait=True)

    print("\n✅ Segmented TTS test complete")
    return True


def main():
    """Main test function"""
    print("\n" + "="*70)
    print("🤖 LLM INTEGRATION TEST SUITE")
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

    # Run tests
    tests = [
        ("Ollama Connection", test_ollama_connection),
        ("Text Generation", test_text_generation),
        ("Personality Prompts", test_personality_prompts),
        ("Conversation Manager", test_conversation_manager),
        ("TTS Engine", test_tts_engine),
        ("Emotion Segments", test_emotion_segments),
        ("Segmented TTS", test_segmented_tts),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func(config)
            results.append((test_name, result))
        except KeyboardInterrupt:
            print("\n\n⏹️  Tests interrupted")
            return 1
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            logger.error("Test error", exc_info=True)
            results.append((test_name, False))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL/SKIP"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    # Interactive mode
    if passed > 0:
        print("\n" + "="*70)
        response = input("\nRun interactive mode? (y/n): ").strip().lower()
        if response == 'y':
            interactive_mode(config)

    print("\n✅ All tests complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
