"""
Database module for companion bot memory
Manages SQLite database for user profiles and conversation history
"""

import sqlite3
import logging
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Database:
    """SQLite database manager for companion bot memory"""

    def __init__(self, db_path: str):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database schema
        self._init_database()

        logger.info(f"Database initialized at {self.db_path}")

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections

        Yields:
            sqlite3.Connection
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def _init_database(self):
        """Initialize database schema if not exists"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    face_encoding BLOB,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    interaction_count INTEGER DEFAULT 0,
                    metadata TEXT
                )
            ''')

            # Conversations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    session_id TEXT,
                    role TEXT NOT NULL,
                    message TEXT NOT NULL,
                    emotion TEXT,
                    tokens INTEGER DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

            # Preferences table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS preferences (
                    preference_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    preference_key TEXT NOT NULL,
                    preference_value TEXT NOT NULL,
                    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(user_id, preference_key)
                )
            ''')

            # Interactions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS interactions (
                    interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    interaction_type TEXT NOT NULL,
                    interaction_value TEXT,
                    emotion_response TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

            # Create indexes for performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_conversations_user
                ON conversations(user_id)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_conversations_session
                ON conversations(session_id)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_conversations_timestamp
                ON conversations(timestamp)
            ''')

            logger.info("Database schema initialized")

    def execute_query(
        self,
        query: str,
        params: tuple = (),
        fetch_one: bool = False
    ) -> Optional[Any]:
        """
        Execute SQL query with parameters

        Args:
            query: SQL query string
            params: Query parameters
            fetch_one: If True, return single row; else all rows

        Returns:
            Query results or None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)

            if fetch_one:
                result = cursor.fetchone()
                return dict(result) if result else None
            else:
                results = cursor.fetchall()
                return [dict(row) for row in results]

    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """
        Execute INSERT query and return last row ID

        Args:
            query: SQL INSERT query
            params: Query parameters

        Returns:
            Last inserted row ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.lastrowid

    def cleanup_old_data(self, days: int = 90) -> int:
        """
        Delete conversations older than specified days

        Args:
            days: Age threshold in days

        Returns:
            Number of conversations deleted
        """
        query = '''
            DELETE FROM conversations
            WHERE timestamp < datetime('now', ?)
        '''

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (f'-{days} days',))
            deleted_count = cursor.rowcount

        logger.info(f"Cleaned up {deleted_count} conversations older than {days} days")
        return deleted_count

    def get_database_stats(self) -> Dict[str, int]:
        """
        Get database statistics

        Returns:
            Dictionary with table row counts
        """
        stats = {}

        with self.get_connection() as conn:
            cursor = conn.cursor()

            for table in ['users', 'conversations', 'preferences', 'interactions']:
                cursor.execute(f'SELECT COUNT(*) as count FROM {table}')
                stats[table] = cursor.fetchone()['count']

        return stats
