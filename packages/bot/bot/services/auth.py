# src/bot/services/auth.py
"""
Handles loading and managing authorized users exclusively from MongoDB.
"""
import logging
from typing import Set

# Import the database store type hint for clarity
from bot.storage.database import MongoDBStore

logger = logging.getLogger("Bot.Services.Auth")

def load_authorized_users(mongodb_store: MongoDBStore) -> Set[int]:
    """
    Loads the set of authorized users directly from MongoDB.

    Args:
        mongodb_store: The initialized MongoDB store instance.

    Returns:
        A set of authorized user IDs.
    """
    try:
        users_set = mongodb_store.get_authorized_users()
        logger.info(f"[OK] Loaded {len(users_set)} authorized users from MongoDB.")
        return users_set
    except Exception as e:
        logger.exception(f"[ERROR] Failed to load authorized users from MongoDB: {e}")
        # Return an empty set on failure to prevent bot crash
        return set()

def add_authorized_user(user_id: int, mongodb_store: MongoDBStore) -> bool:
    """
    Adds a user to the authorized list in MongoDB.

    Args:
        user_id: The Discord user ID to authorize.
        mongodb_store: The initialized MongoDB store instance.

    Returns:
        True if the operation was successful, False otherwise.
    """
    try:
        success = mongodb_store.add_authorized_user(user_id)
        if success:
            logger.info(f"Successfully added user {user_id} to authorized list in MongoDB.")
        else:
            logger.warning(f"Failed to add user {user_id} to authorized list (might already exist).")
        return success
    except Exception as e:
        logger.exception(f"An error occurred while adding authorized user {user_id}: {e}")
        return False


def remove_authorized_user(user_id: int, mongodb_store: MongoDBStore) -> bool:
    """
    Removes a user from the authorized list in MongoDB.

    Args:
        user_id: The Discord user ID to deauthorize.
        mongodb_store: The initialized MongoDB store instance.

    Returns:
        True if the operation was successful, False otherwise.
    """
    try:
        success = mongodb_store.remove_authorized_user(user_id)
        if success:
            logger.info(f"Successfully removed user {user_id} from authorized list in MongoDB.")
        else:
            logger.warning(f"Failed to remove user {user_id} from authorized list (might not exist).")
        return success
    except Exception as e:
        logger.exception(f"An error occurred while removing authorized user {user_id}: {e}")
        return False