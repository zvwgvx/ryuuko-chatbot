# Fixed memory.py - Replace the entire file

import json
import tiktoken
import logging
from pathlib import Path
from collections import deque
from typing import Dict, List, Union, TypedDict
import load_config

logger = logging.getLogger("Memory")

# Configuration
CONFIG_DIR = Path(__file__).parent.parent / "config"

try:
    TOKENIZER = tiktoken.encoding_for_model("gpt-4")
except:
    TOKENIZER = tiktoken.get_encoding("cl100k_base")

class Msg(TypedDict):
    role: str
    content: str

class MemoryStore:
    def __init__(self, path: Union[Path, str] = None):
        self.use_mongodb = getattr(load_config, 'USE_MONGODB', False)
        
        if self.use_mongodb:
            # MongoDB mode - delegate to MongoDB store
            try:
                from database import get_mongodb_store
                self.mongo_store = get_mongodb_store()
                logger.info("MemoryStore initialized with MongoDB backend")
            except Exception as e:
                logger.error(f"Failed to initialize MongoDB backend: {e}")

    def get_user_messages(self, user_id: int) -> List[Msg]:
        """Get user's conversation history"""
        try:
            messages = self.mongo_store.get_user_messages(user_id)
            logger.debug(f"Retrieved {len(messages)} messages from MongoDB for user {user_id}")
            return messages
        except Exception as e:
            logger.exception(f"Error getting messages from MongoDB for user {user_id}: {e}")
            return []


    def add_message(self, user_id: int, msg: Msg) -> bool:
        """Add message to user's conversation history"""
        try:
            max_messages = getattr(load_config, 'MEMORY_MAX_PER_USER', 25)
            max_tokens = getattr(load_config, 'MEMORY_MAX_TOKENS', 4000)

            success = self.mongo_store.add_message(user_id, msg, max_messages, max_tokens)
            if success:
                logger.debug(f"Successfully added message to MongoDB for user {user_id}")
            else:
                logger.error(f"Failed to add message to MongoDB for user {user_id}")
            return success
        except Exception as e:
            logger.exception(f"Error adding message to MongoDB for user {user_id}: {e}")
            return False

    def clear_user(self, user_id: int) -> bool:
        """Clear user's conversation history"""
        try:
            success = self.mongo_store.clear_user_memory(user_id)
            if success:
                logger.info(f"Successfully cleared memory for user {user_id} from MongoDB")
            else:
                logger.warning(f"Failed to clear memory for user {user_id} from MongoDB")
            return success
        except Exception as e:
            logger.exception(f"Error clearing memory from MongoDB for user {user_id}: {e}")
            return False

    def remove_last_message(self, user_id: int) -> bool:
        """Remove the last message from user's conversation history"""
        try:
            success = self.mongo_store.remove_last_message(user_id)
            if success:
                logger.info(f"Successfully removed last message for user {user_id} from MongoDB")
            else:
                logger.warning(f"Failed to remove last message for user {user_id} from MongoDB")
            return success
        except Exception as e:
            logger.exception(f"Error removing last message from MongoDB for user {user_id}: {e}")
            return False

    def get_message_count(self, user_id: int) -> int:
        """Get the number of messages for a user"""
        if self.use_mongodb:
            messages = self.get_user_messages(user_id)
            return len(messages)
        else:
            return len(self._cache.get(user_id, []))

    def get_token_count(self, user_id: int) -> int:
        """Get approximate token count for user's messages"""
        if self.use_mongodb:
            messages = self.get_user_messages(user_id)
            return sum(len(TOKENIZER.encode(msg.get("content", ""))) for msg in messages)
        else:
            return self._token_cnt.get(user_id, 0)