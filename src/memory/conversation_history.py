"""
Conversation History Module
Manages conversation persistence and retrieval
"""

import logging
import uuid
from typing import Optional, Dict, List
from datetime import datetime

from .database import Database

logger = logging.getLogger(__name__)


class ConversationHistory:
    """Conversation persistence and retrieval"""

    def __init__(self, database: Database):
        """
        Initialize conversation history

        Args:
            database: Database instance
        """
        self.db = database
        logger.info("ConversationHistory initialized")

    def save_message(
        self,
        user_id: Optional[int],
        session_id: str,
        role: str,
        message: str,
        emotion: Optional[str] = None,
        tokens: int = 0
    ) -> int:
        """
        Save single conversation message

        Args:
            user_id: User ID (None for anonymous)
            session_id: Session identifier
            role: 'user' or 'assistant'
            message: Message text
            emotion: Bot's emotion (for assistant messages)
            tokens: Token count (for assistant messages)

        Returns:
            Conversation ID
        """
        query = '''
            INSERT INTO conversations
            (user_id, session_id, role, message, emotion, tokens)
            VALUES (?, ?, ?, ?, ?, ?)
        '''

        conversation_id = self.db.execute_insert(
            query,
            (user_id, session_id, role, message, emotion, tokens)
        )

        logger.debug(f"Saved message: session={session_id}, role={role}")
        return conversation_id

    def save_conversation_batch(
        self,
        user_id: Optional[int],
        session_id: str,
        messages: List[Dict]
    ) -> int:
        """
        Save multiple conversation messages

        Args:
            user_id: User ID
            session_id: Session identifier
            messages: List of message dictionaries with keys:
                      role, message, emotion (optional), tokens (optional)

        Returns:
            Number of messages saved
        """
        count = 0
        for msg in messages:
            self.save_message(
                user_id=user_id,
                session_id=session_id,
                role=msg['role'],
                message=msg['message'],
                emotion=msg.get('emotion'),
                tokens=msg.get('tokens', 0)
            )
            count += 1

        logger.info(f"Saved {count} messages for session {session_id}")
        return count

    def get_session_conversation(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Get all messages for a session

        Args:
            session_id: Session identifier
            limit: Optional limit on number of messages

        Returns:
            List of message dictionaries
        """
        query = '''
            SELECT conversation_id, role, message, emotion, tokens, timestamp
            FROM conversations
            WHERE session_id = ?
            ORDER BY timestamp ASC
        '''

        if limit:
            query += f' LIMIT {limit}'

        return self.db.execute_query(query, (session_id,))

    def get_user_conversations(
        self,
        user_id: int,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get recent conversations for a user

        Args:
            user_id: User ID
            limit: Maximum number of messages to return

        Returns:
            List of message dictionaries
        """
        query = '''
            SELECT conversation_id, session_id, role, message, emotion, timestamp
            FROM conversations
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        '''

        return self.db.execute_query(query, (user_id, limit))

    def get_recent_context(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get recent conversation context for a user (last N exchanges)

        Args:
            user_id: User ID
            limit: Number of recent exchanges (user+assistant pairs)

        Returns:
            List of message dictionaries ordered oldest to newest
        """

        query = '''
            SELECT role, message, emotion
            FROM conversations
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        '''

        results = self.db.execute_query(query, (user_id, limit * 2))


        return list(reversed(results))

    def get_session_list(
        self,
        user_id: Optional[int] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Get list of conversation sessions

        Args:
            user_id: Optional user ID filter
            limit: Maximum number of sessions

        Returns:
            List of session info dictionaries
        """
        if user_id:
            query = '''
                SELECT session_id, user_id, MIN(timestamp) as start_time,
                       MAX(timestamp) as end_time, COUNT(*) as message_count
                FROM conversations
                WHERE user_id = ?
                GROUP BY session_id
                ORDER BY start_time DESC
                LIMIT ?
            '''
            params = (user_id, limit)
        else:
            query = '''
                SELECT session_id, user_id, MIN(timestamp) as start_time,
                       MAX(timestamp) as end_time, COUNT(*) as message_count
                FROM conversations
                GROUP BY session_id
                ORDER BY start_time DESC
                LIMIT ?
            '''
            params = (limit,)

        return self.db.execute_query(query, params)

    def search_conversations(
        self,
        search_term: str,
        user_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Search conversations by content

        Args:
            search_term: Text to search for
            user_id: Optional user ID filter
            limit: Maximum results

        Returns:
            List of matching message dictionaries
        """
        if user_id:
            query = '''
                SELECT conversation_id, session_id, role, message, timestamp
                FROM conversations
                WHERE user_id = ? AND message LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            '''
            params = (user_id, f'%{search_term}%', limit)
        else:
            query = '''
                SELECT conversation_id, session_id, role, message, timestamp
                FROM conversations
                WHERE message LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            '''
            params = (f'%{search_term}%', limit)

        return self.db.execute_query(query, params)

    def get_conversation_stats(self, user_id: Optional[int] = None) -> Dict:
        """
        Get conversation statistics

        Args:
            user_id: Optional user ID filter

        Returns:
            Dictionary with statistics
        """
        stats = {}

        if user_id:

            query = '''
                SELECT COUNT(*) as count
                FROM conversations
                WHERE user_id = ?
            '''
            result = self.db.execute_query(query, (user_id,), fetch_one=True)
            stats['total_messages'] = result['count'] if result else 0


            query = '''
                SELECT COUNT(DISTINCT session_id) as count
                FROM conversations
                WHERE user_id = ?
            '''
            result = self.db.execute_query(query, (user_id,), fetch_one=True)
            stats['total_sessions'] = result['count'] if result else 0


            if stats['total_sessions'] > 0:
                stats['avg_messages_per_session'] = stats['total_messages'] / stats['total_sessions']
            else:
                stats['avg_messages_per_session'] = 0


            query = '''
                SELECT emotion, COUNT(*) as count
                FROM conversations
                WHERE user_id = ? AND emotion IS NOT NULL AND role = 'assistant'
                GROUP BY emotion
                ORDER BY count DESC
                LIMIT 5
            '''
            emotion_counts = self.db.execute_query(query, (user_id,))
            stats['top_emotions'] = {row['emotion']: row['count'] for row in emotion_counts}

        else:

            query = 'SELECT COUNT(*) as count FROM conversations'
            result = self.db.execute_query(query, fetch_one=True)
            stats['total_messages'] = result['count'] if result else 0

            query = 'SELECT COUNT(DISTINCT session_id) as count FROM conversations'
            result = self.db.execute_query(query, fetch_one=True)
            stats['total_sessions'] = result['count'] if result else 0

            query = 'SELECT COUNT(DISTINCT user_id) as count FROM conversations WHERE user_id IS NOT NULL'
            result = self.db.execute_query(query, fetch_one=True)
            stats['total_users'] = result['count'] if result else 0

        return stats

    def delete_session(self, session_id: str) -> bool:
        """
        Delete all messages in a session

        Args:
            session_id: Session identifier

        Returns:
            True if successful
        """
        query = 'DELETE FROM conversations WHERE session_id = ?'

        try:
            self.db.execute_query(query, (session_id,))
            logger.info(f"Deleted session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return False

    def delete_user_conversations(self, user_id: int) -> bool:
        """
        Delete all conversations for a user

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        query = 'DELETE FROM conversations WHERE user_id = ?'

        try:
            self.db.execute_query(query, (user_id,))
            logger.info(f"Deleted conversations for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting user conversations: {e}")
            return False

    def cleanup_old_conversations(self, days: int = 90) -> int:
        """
        Delete conversations older than specified days

        Args:
            days: Age threshold in days

        Returns:
            Number of conversations deleted
        """
        return self.db.cleanup_old_data(days)

    @staticmethod
    def generate_session_id() -> str:
        """
        Generate unique session ID

        Returns:
            Session ID string
        """
        return str(uuid.uuid4())
