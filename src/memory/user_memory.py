"""
User Memory Module
Manages user profiles, preferences, and interactions
"""

import logging
import json
import pickle
from typing import Optional, Dict, List
from datetime import datetime

from .database import Database

logger = logging.getLogger(__name__)


class UserMemory:
    """User profile and preference management"""

    def __init__(self, database: Database):
        """
        Initialize user memory

        Args:
            database: Database instance
        """
        self.db = database
        logger.info("UserMemory initialized")

    def create_user(self, name: str, face_encoding: Optional[bytes] = None) -> int:
        """
        Create new user profile

        Args:
            name: User's name
            face_encoding: Optional face encoding (pickled numpy array)

        Returns:
            New user ID
        """
        query = '''
            INSERT INTO users (name, face_encoding, metadata)
            VALUES (?, ?, ?)
        '''

        metadata = json.dumps({'created_via': 'api'})
        user_id = self.db.execute_insert(query, (name, face_encoding, metadata))

        logger.info(f"Created user: {name} (ID: {user_id})")
        return user_id

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """
        Get user profile by ID

        Args:
            user_id: User ID

        Returns:
            User profile dictionary or None
        """
        query = '''
            SELECT user_id, name, created_date, last_interaction,
                   interaction_count, metadata
            FROM users
            WHERE user_id = ?
        '''

        result = self.db.execute_query(query, (user_id,), fetch_one=True)

        if result and result.get('metadata'):
            result['metadata'] = json.loads(result['metadata'])

        return result

    def get_user_by_name(self, name: str) -> Optional[Dict]:
        """
        Get user profile by name

        Args:
            name: User's name

        Returns:
            User profile dictionary or None
        """
        query = '''
            SELECT user_id, name, created_date, last_interaction,
                   interaction_count, metadata
            FROM users
            WHERE name = ? COLLATE NOCASE
        '''

        result = self.db.execute_query(query, (name,), fetch_one=True)

        if result and result.get('metadata'):
            result['metadata'] = json.loads(result['metadata'])

        return result

    def get_all_users(self) -> List[Dict]:
        """
        Get all user profiles

        Returns:
            List of user profile dictionaries
        """
        query = '''
            SELECT user_id, name, created_date, last_interaction, interaction_count
            FROM users
            ORDER BY last_interaction DESC
        '''

        return self.db.execute_query(query)

    def update_user_interaction(self, user_id: int) -> bool:
        """
        Update user's last interaction time and count

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        query = '''
            UPDATE users
            SET last_interaction = CURRENT_TIMESTAMP,
                interaction_count = interaction_count + 1
            WHERE user_id = ?
        '''

        try:
            self.db.execute_query(query, (user_id,))
            return True
        except Exception as e:
            logger.error(f"Error updating user interaction: {e}")
            return False

    def delete_user(self, user_id: int) -> bool:
        """
        Delete user profile

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        query = 'DELETE FROM users WHERE user_id = ?'

        try:
            self.db.execute_query(query, (user_id,))
            logger.info(f"Deleted user ID: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False

    def set_preference(
        self,
        user_id: int,
        key: str,
        value: str
    ) -> bool:
        """
        Set user preference

        Args:
            user_id: User ID
            key: Preference key
            value: Preference value

        Returns:
            True if successful
        """
        query = '''
            INSERT OR REPLACE INTO preferences
            (user_id, preference_key, preference_value, updated_date)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        '''

        try:
            self.db.execute_query(query, (user_id, key, value))
            logger.debug(f"Set preference for user {user_id}: {key}={value}")
            return True
        except Exception as e:
            logger.error(f"Error setting preference: {e}")
            return False

    def get_preference(
        self,
        user_id: int,
        key: str,
        default: Optional[str] = None
    ) -> Optional[str]:
        """
        Get user preference

        Args:
            user_id: User ID
            key: Preference key
            default: Default value if not found

        Returns:
            Preference value or default
        """
        query = '''
            SELECT preference_value
            FROM preferences
            WHERE user_id = ? AND preference_key = ?
        '''

        result = self.db.execute_query(query, (user_id, key), fetch_one=True)
        return result['preference_value'] if result else default

    def get_all_preferences(self, user_id: int) -> Dict[str, str]:
        """
        Get all preferences for a user

        Args:
            user_id: User ID

        Returns:
            Dictionary of preferences
        """
        query = '''
            SELECT preference_key, preference_value
            FROM preferences
            WHERE user_id = ?
        '''

        results = self.db.execute_query(query, (user_id,))
        return {row['preference_key']: row['preference_value'] for row in results}

    def delete_preference(self, user_id: int, key: str) -> bool:
        """
        Delete user preference

        Args:
            user_id: User ID
            key: Preference key

        Returns:
            True if successful
        """
        query = '''
            DELETE FROM preferences
            WHERE user_id = ? AND preference_key = ?
        '''

        try:
            self.db.execute_query(query, (user_id, key))
            return True
        except Exception as e:
            logger.error(f"Error deleting preference: {e}")
            return False

    def record_interaction(
        self,
        user_id: int,
        interaction_type: str,
        interaction_value: Optional[str] = None,
        emotion_response: Optional[str] = None
    ) -> bool:
        """
        Record user interaction

        Args:
            user_id: User ID
            interaction_type: Type of interaction (voice, touch, face, etc.)
            interaction_value: Optional interaction details
            emotion_response: Bot's emotional response

        Returns:
            True if successful
        """
        query = '''
            INSERT INTO interactions
            (user_id, interaction_type, interaction_value, emotion_response)
            VALUES (?, ?, ?, ?)
        '''

        try:
            self.db.execute_query(
                query,
                (user_id, interaction_type, interaction_value, emotion_response)
            )
            self.update_user_interaction(user_id)
            return True
        except Exception as e:
            logger.error(f"Error recording interaction: {e}")
            return False

    def get_interaction_history(
        self,
        user_id: int,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get user's recent interactions

        Args:
            user_id: User ID
            limit: Maximum number of interactions to return

        Returns:
            List of interaction dictionaries
        """
        query = '''
            SELECT interaction_type, interaction_value, emotion_response, timestamp
            FROM interactions
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        '''

        return self.db.execute_query(query, (user_id, limit))

    def get_interaction_stats(self, user_id: int) -> Dict:
        """
        Get interaction statistics for user

        Args:
            user_id: User ID

        Returns:
            Dictionary with interaction counts by type
        """
        query = '''
            SELECT interaction_type, COUNT(*) as count
            FROM interactions
            WHERE user_id = ?
            GROUP BY interaction_type
        '''

        results = self.db.execute_query(query, (user_id,))
        return {row['interaction_type']: row['count'] for row in results}

    def save_face_encoding(self, user_id: int, face_encoding) -> bool:
        """
        Save face encoding for user

        Args:
            user_id: User ID
            face_encoding: Numpy array of face encoding

        Returns:
            True if successful
        """
        try:
            encoded = pickle.dumps(face_encoding)
            query = 'UPDATE users SET face_encoding = ? WHERE user_id = ?'
            self.db.execute_query(query, (encoded, user_id))
            logger.info(f"Saved face encoding for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving face encoding: {e}")
            return False

    def get_face_encoding(self, user_id: int):
        """
        Get face encoding for user

        Args:
            user_id: User ID

        Returns:
            Numpy array of face encoding or None
        """
        query = 'SELECT face_encoding FROM users WHERE user_id = ?'

        result = self.db.execute_query(query, (user_id,), fetch_one=True)

        if result and result['face_encoding']:
            try:
                return pickle.loads(result['face_encoding'])
            except Exception as e:
                logger.error(f"Error loading face encoding: {e}")
                return None

        return None

    def get_all_face_encodings(self) -> Dict[int, any]:
        """
        Get all face encodings

        Returns:
            Dictionary mapping user_id to face encoding
        """
        query = '''
            SELECT user_id, face_encoding
            FROM users
            WHERE face_encoding IS NOT NULL
        '''

        results = self.db.execute_query(query)
        encodings = {}

        for row in results:
            try:
                encodings[row['user_id']] = pickle.loads(row['face_encoding'])
            except Exception as e:
                logger.error(f"Error loading face encoding for user {row['user_id']}: {e}")

        return encodings
