# src/storage/memory.py
import tiktoken
import logging
from typing import List, Dict
from src.config import loader
from src.storage.database import MongoDBStore  # Import để type hinting

logger = logging.getLogger("Storage.Memory")

try:
    TOKENIZER = tiktoken.encoding_for_model("gpt-4")
except Exception:
    TOKENIZER = tiktoken.get_encoding("cl100k_base")


class Msg(Dict):
    role: str
    content: str


class MemoryStore:
    def __init__(self, mongodb_store: MongoDBStore):
        """
        Initializes the MemoryStore as a layer on top of MongoDB.
        Args:
            mongodb_store: The initialized MongoDB store instance.
        """
        if not mongodb_store:
            raise ValueError("MemoryStore requires a valid mongodb_store instance.")
        self.mongo_store = mongodb_store
        logger.info("MemoryStore initialized with MongoDB backend.")

    def get_user_messages(self, user_id: int) -> List[Msg]:
        """Get user's conversation history from MongoDB."""
        try:
            return self.mongo_store.get_user_messages(user_id)
        except Exception as e:
            logger.exception(f"Error getting messages from MongoDB for user {user_id}: {e}")
            return []

    def add_message(self, user_id: int, msg: Msg) -> bool:
        """Add message to user's conversation history in MongoDB."""
        try:
            # Lấy cấu hình giới hạn từ loader
            max_messages = getattr(loader, 'MEMORY_MAX_MESSAGES', 25)
            max_tokens = getattr(loader, 'MEMORY_MAX_TOKENS', 4000)
            return self.mongo_store.add_message(user_id, msg, max_messages, max_tokens)
        except Exception as e:
            logger.exception(f"Error adding message to MongoDB for user {user_id}: {e}")
            return False

    def clear_user_messages(self, user_id: int) -> bool:
        """
        Clears the conversation history for a specific user in MongoDB.
        Returns True on success, False on failure.
        """
        try:
            # Call the correct method on the MongoDBStore instance.
            # Assuming the method is named 'clear_user_memory' and returns a tuple (success, message).
            success = self.mongo_store.clear_user_memory(user_id)
            return success
        except Exception as e:
            logger.exception(f"Error clearing memory from MongoDB for user {user_id}: {e}")
            return False

    def remove_last_message(self, user_id: int) -> bool:
        """Remove the last message from user's conversation history in MongoDB."""
        try:
            return self.mongo_store.remove_last_message(user_id)
        except Exception as e:
            logger.exception(f"Error removing last message from MongoDB for user {user_id}: {e}")
            return False

    def get_message_count(self, user_id: int) -> int:
        """Get the number of messages for a user from MongoDB."""
        return len(self.get_user_messages(user_id))

    def get_token_count(self, user_id: int) -> int:
        """Get approximate token count for user's messages from MongoDB."""
        messages = self.get_user_messages(user_id)
        return sum(len(TOKENIZER.encode(msg.get("content", ""))) for msg in messages)