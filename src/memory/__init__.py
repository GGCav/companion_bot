"""
Memory Module
Manages user profiles, conversation history, and learned preferences
"""

from .database import Database
from .user_memory import UserMemory
from .conversation_history import ConversationHistory

__all__ = ['Database', 'UserMemory', 'ConversationHistory', 'initialize_memory']


def initialize_memory(config: dict):
    """
    Initialize memory system with database

    Args:
        config: Configuration dictionary from settings.yaml

    Returns:
        Tuple of (user_memory, conversation_history) instances
    """
    db_path = config.get('memory', {}).get('database_path', 'data/companion.db')

    database = Database(db_path)

    user_memory = UserMemory(database)
    conversation_history = ConversationHistory(database)

    return user_memory, conversation_history
