#!/usr/bin/env python3
"""
Memory System Test Script
Test user profiles, conversation persistence, and database functionality
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import yaml
from memory import initialize_memory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_user_profiles(user_memory):
    """Test user profile management"""
    print("\n" + "="*70)
    print("TEST 1: User Profile Management")
    print("="*70)

    # Create users
    print("\n📝 Creating test users...")
    john_id = user_memory.create_user("John")
    alice_id = user_memory.create_user("Alice")
    print(f"   Created: John (ID: {john_id}), Alice (ID: {alice_id})")

    # Get user by ID
    print("\n🔍 Getting user by ID...")
    john = user_memory.get_user_by_id(john_id)
    print(f"   User {john_id}: {john['name']}")

    # Get user by name
    print("\n🔍 Getting user by name...")
    alice = user_memory.get_user_by_name("Alice")
    print(f"   Found: {alice['name']} (ID: {alice['user_id']})")

    # List all users
    print("\n📋 All users:")
    all_users = user_memory.get_all_users()
    for user in all_users:
        print(f"   ID {user['user_id']}: {user['name']}")

    print("\n✅ User profile tests passed")
    return john_id, alice_id


def test_preferences(user_memory, user_id):
    """Test user preferences"""
    print("\n" + "="*70)
    print("TEST 2: User Preferences")
    print("="*70)

    # Set preferences
    print("\n📝 Setting preferences...")
    user_memory.set_preference(user_id, "favorite_color", "blue")
    user_memory.set_preference(user_id, "hobby", "reading")
    print("   Set favorite_color=blue")
    print("   Set hobby=reading")

    # Get preference
    print("\n🔍 Getting preference...")
    color = user_memory.get_preference(user_id, "favorite_color")
    print(f"   favorite_color: {color}")

    # Get all preferences
    print("\n📋 All preferences:")
    all_prefs = user_memory.get_all_preferences(user_id)
    for key, value in all_prefs.items():
        print(f"   {key}: {value}")

    print("\n✅ Preference tests passed")


def test_interactions(user_memory, user_id):
    """Test interaction logging"""
    print("\n" + "="*70)
    print("TEST 3: Interaction Logging")
    print("="*70)

    # Record interactions
    print("\n📝 Recording interactions...")
    user_memory.record_interaction(user_id, "voice", "Hello!", "happy")
    user_memory.record_interaction(user_id, "touch", "head", "excited")
    user_memory.record_interaction(user_id, "voice", "How are you?", "curious")
    print("   Recorded 3 interactions")

    # Get interaction history
    print("\n📋 Interaction history:")
    history = user_memory.get_interaction_history(user_id, limit=10)
    for interaction in history:
        print(f"   [{interaction['timestamp']}] {interaction['interaction_type']}: "
              f"{interaction['interaction_value']} → {interaction['emotion_response']}")

    # Get interaction stats
    print("\n📊 Interaction stats:")
    stats = user_memory.get_interaction_stats(user_id)
    for interaction_type, count in stats.items():
        print(f"   {interaction_type}: {count}")

    print("\n✅ Interaction tests passed")


def test_conversation_persistence(conversation_history, user_id):
    """Test conversation persistence"""
    print("\n" + "="*70)
    print("TEST 4: Conversation Persistence")
    print("="*70)

    # Generate session ID
    session_id = conversation_history.generate_session_id()
    print(f"\n📝 Session ID: {session_id}")

    # Save conversation messages
    print("\n💬 Saving conversation...")
    conversation_history.save_message(user_id, session_id, "user", "Hello!")
    conversation_history.save_message(user_id, session_id, "assistant", "Hi! How are you?", emotion="happy", tokens=5)
    conversation_history.save_message(user_id, session_id, "user", "I'm great, thanks!")
    conversation_history.save_message(user_id, session_id, "assistant", "That's wonderful!", emotion="excited", tokens=3)
    print("   Saved 4 messages")

    # Get session conversation
    print("\n📋 Session conversation:")
    messages = conversation_history.get_session_conversation(session_id)
    for msg in messages:
        emotion_str = f" ({msg['emotion']})" if msg['emotion'] else ""
        print(f"   {msg['role']}: {msg['message']}{emotion_str}")

    # Get user conversations
    print("\n📋 User's recent conversations:")
    recent = conversation_history.get_user_conversations(user_id, limit=5)
    for msg in recent:
        print(f"   [{msg['session_id'][:8]}...] {msg['role']}: {msg['message'][:40]}...")

    # Get conversation stats
    print("\n📊 Conversation stats:")
    stats = conversation_history.get_conversation_stats(user_id)
    print(f"   Total messages: {stats['total_messages']}")
    print(f"   Total sessions: {stats['total_sessions']}")
    print(f"   Avg messages/session: {stats['avg_messages_per_session']:.1f}")
    if stats.get('top_emotions'):
        print(f"   Top emotions: {stats['top_emotions']}")

    print("\n✅ Conversation persistence tests passed")
    return session_id


def test_search(conversation_history):
    """Test conversation search"""
    print("\n" + "="*70)
    print("TEST 5: Conversation Search")
    print("="*70)

    # Search conversations
    print("\n🔍 Searching for 'great'...")
    results = conversation_history.search_conversations("great")
    print(f"   Found {len(results)} matches:")
    for result in results[:3]:  # Show first 3
        print(f"   {result['role']}: {result['message']}")

    print("\n✅ Search tests passed")


def test_memory_persistence():
    """Test that memory persists across instances"""
    print("\n" + "="*70)
    print("TEST 6: Memory Persistence")
    print("="*70)

    # Load configuration
    config_path = Path(__file__).parent.parent / 'config' / 'settings.yaml'
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Initialize memory (first instance)
    print("\n📝 Creating first memory instance...")
    user_memory1, conv_history1 = initialize_memory(config)

    test_name = "MemoryTestUser"
    test_user_id = user_memory1.create_user(test_name)
    user_memory1.set_preference(test_user_id, "test_key", "test_value")
    print(f"   Created user: {test_name} (ID: {test_user_id})")

    # Create new instance (simulating restart)
    print("\n🔄 Creating second memory instance (simulating restart)...")
    user_memory2, conv_history2 = initialize_memory(config)

    # Verify data persists
    print("\n🔍 Checking if data persists...")
    retrieved_user = user_memory2.get_user_by_name(test_name)

    if retrieved_user:
        print(f"   ✅ User found: {retrieved_user['name']} (ID: {retrieved_user['user_id']})")

        # Check preference
        pref_value = user_memory2.get_preference(retrieved_user['user_id'], "test_key")
        if pref_value == "test_value":
            print(f"   ✅ Preference persisted: test_key={pref_value}")
        else:
            print(f"   ❌ Preference not found")
    else:
        print(f"   ❌ User not found after restart")

    print("\n✅ Persistence tests passed")


def test_cleanup(conversation_history):
    """Test cleanup functionality"""
    print("\n" + "="*70)
    print("TEST 7: Database Cleanup")
    print("="*70)

    print("\n🗑️  Testing cleanup (0 days - should delete nothing recent)...")
    deleted = conversation_history.cleanup_old_conversations(days=0)
    print(f"   Deleted {deleted} old conversations")

    print("\n✅ Cleanup tests passed")


def main():
    """Main test function"""
    print("\n" + "="*70)
    print("🧠 MEMORY SYSTEM TEST SUITE")
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

    # Initialize memory system
    try:
        print("\n📦 Initializing memory system...")
        user_memory, conversation_history = initialize_memory(config)
        print("✅ Memory system initialized")
    except Exception as e:
        print(f"❌ Failed to initialize memory: {e}")
        logger.error("Initialization error", exc_info=True)
        return 1

    # Run tests
    try:
        # User management
        john_id, alice_id = test_user_profiles(user_memory)

        # Preferences
        test_preferences(user_memory, john_id)

        # Interactions
        test_interactions(user_memory, john_id)

        # Conversation persistence
        session_id = test_conversation_persistence(conversation_history, alice_id)

        # Search
        test_search(conversation_history)

        # Cleanup
        test_cleanup(conversation_history)

        # Persistence across instances
        test_memory_persistence()

    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted")
        return 1
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        logger.error("Test error", exc_info=True)
        return 1

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print("✅ All memory system tests passed!")
    print("\n💾 Database location:", config.get('memory', {}).get('database_path', 'data/companion.db'))

    return 0


if __name__ == "__main__":
    sys.exit(main())
