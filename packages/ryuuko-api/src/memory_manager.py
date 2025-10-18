# /packages/ryuuko-api/src/memory_manager.py

import logging
from typing import List, Dict, Any

from .database import db_store

logger = logging.getLogger("RyuukoAPI.MemoryManager")

class MemoryManager:
    """Handles high-level memory operations, acting as a service layer."""

    def __init__(self, database_store):
        self.db = database_store

    def get_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieves the full conversation history for a user."""
        logger.debug(f"Fetching memory for user_id: {user_id}")
        return self.db.get_user_memory(user_id)

    def add_message(self, user_id: str, role: str, content: Any):
        """Adds a single message to the user's conversation history."""
        logger.debug(f"Adding '{role}' message to memory for user_id: {user_id}")
        message = {"role": role, "content": content}
        self.db.add_message_to_memory(user_id, message)

    def clear_history(self, user_id: str) -> bool:
        """Clears the entire conversation history for a user."""
        logger.info(f"Clearing memory for user_id: {user_id}")
        return self.db.clear_user_memory(user_id)

    def prepare_prompt_history(self, user_id: str, new_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepares the conversation history for use in a prompt.
        For now, it simply concatenates old and new messages.
        """
        logger.debug(f"Preparing prompt history for user_id: {user_id}")
        history = self.get_history(user_id)
        # This is where future logic like summarization or pruning will go.
        return history + new_messages

# Create a single, shared instance of the MemoryManager
memory_manager = MemoryManager(db_store)
