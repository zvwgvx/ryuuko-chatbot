#!/usr/bin/env python3
# coding: utf-8
# mongodb_store.py - REFACTORED for ryuuko_user_id

import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from pymongo import MongoClient, WriteConcern
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import tiktoken
import time

logger = logging.getLogger("Storage.Database")


class MongoDBStore:
    """MongoDB storage manager for Discord OpenAI proxy"""

    def __init__(self, connection_string: str, database_name: str = "polydevsdb"):
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[MongoClient] = None
        self.db = None

        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        except:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

        self.COLLECTIONS = {
            'users': 'users',  # Central user collection
            'user_config': 'user_configs',
            'memory': 'user_memory',
            'authorized': 'authorized_users',
            'models': 'supported_models'
        }

        self._connect()
        self._initialize_default_models()

    def _connect(self):
        """Establish MongoDB connection"""
        try:
            if "?" in self.connection_string:
                connection_string = f"{self.connection_string}&retryWrites=false"
            else:
                connection_string = f"{self.connection_string}?retryWrites=false"

            self.client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000,
                w=1,
                journal=True
            )
            self.client.admin.command('ping')
            self.db = self.client[self.database_name]
            self._create_indexes()
            logger.info(f"Successfully connected to MongoDB: {self.database_name}")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def _create_indexes(self):
        """Create necessary indexes"""
        try:
            self.db[self.COLLECTIONS['user_config']].create_index("ryuuko_user_id", unique=True)
            self.db[self.COLLECTIONS['memory']].create_index("ryuuko_user_id", unique=True)
            self.db[self.COLLECTIONS['memory']].create_index([("ryuuko_user_id", 1), ("updated_at", -1)])
            self.db[self.COLLECTIONS['authorized']].create_index("user_id", unique=True)
            self.db[self.COLLECTIONS['models']].create_index("model_name", unique=True)
            logger.info("MongoDB indexes created successfully")
        except Exception as e:
            logger.exception(f"Error creating indexes: {e}")

    def get_ryuuko_user_id_from_discord_id(self, discord_id: int) -> Optional[str]:
        """Find the ryuuko_user_id associated with a given Discord user ID."""
        try:
            user_doc = self.db[self.COLLECTIONS['users']].find_one(
                {"linked_accounts.discord.user_id": str(discord_id)}
            )
            if user_doc:
                return user_doc.get("ryuuko_user_id")
            return None
        except Exception as e:
            logger.exception(f"Error looking up ryuuko_user_id for discord_id {discord_id}: {e}")
            return None

    def _initialize_default_models(self):
        """Initialize default supported models if collection is empty"""
        try:
            if self.db[self.COLLECTIONS['models']].count_documents({}) == 0:
                default_models = [
                    {"model_name": "ryuuko-r1-vnm-mini", "created_at": datetime.utcnow(), "is_default": False, "credit_cost": 100, "access_level": 3},
                    {"model_name": "ryuuko-r1-eng-mini", "created_at": datetime.utcnow(), "is_default": False, "credit_cost": 100, "access_level": 3},
                ]
                self.db[self.COLLECTIONS['models']].insert_many(default_models)
                logger.info("Default models with credit system initialized in MongoDB")
        except Exception as e:
            logger.exception(f"Error initializing default models: {e}")

    # =====================================
    # MEMORY METHODS
    # =====================================

    def get_user_messages(self, ryuuko_user_id: str) -> List[Dict[str, str]]:
        try:
            result = self.db[self.COLLECTIONS['memory']].find_one({"ryuuko_user_id": ryuuko_user_id})
            if result and "messages" in result:
                return result["messages"]
            return []
        except Exception as e:
            logger.exception(f"Error getting messages for user {ryuuko_user_id}: {e}")
            return []

    def add_message(self, ryuuko_user_id: str, message: Dict[str, str], max_messages: int = 25, max_tokens: int = 4000):
        try:
            current_time = datetime.utcnow()
            current_doc = self.db[self.COLLECTIONS['memory']].find_one({"ryuuko_user_id": ryuuko_user_id})
            current_messages = current_doc.get("messages", []) if current_doc else []
            updated_messages = self._apply_memory_limits(current_messages + [message], max_messages, max_tokens)
            self.db[self.COLLECTIONS['memory']].find_one_and_update(
                {"ryuuko_user_id": ryuuko_user_id},
                {
                    "$set": {"messages": updated_messages, "updated_at": current_time, "message_count": len(updated_messages)},
                    "$setOnInsert": {"ryuuko_user_id": ryuuko_user_id, "created_at": current_time}
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.exception(f"Error adding message for user {ryuuko_user_id}: {e}")
            return False

    def _apply_memory_limits(self, messages: List[Dict[str, str]], max_messages: int, max_tokens: int) -> List[Dict[str, str]]:
        if len(messages) > max_messages:
            messages = messages[-max_messages:]

        total_tokens = sum(len(self.tokenizer.encode(msg.get("content", ""))) for msg in messages)

        while total_tokens > max_tokens and messages:
            removed_msg = messages.pop(0)
            total_tokens -= len(self.tokenizer.encode(removed_msg.get("content", "")))

        return messages

    def clear_user_memory(self, ryuuko_user_id: str) -> bool:
        try:
            result = self.db[self.COLLECTIONS['memory']].delete_one({"ryuuko_user_id": ryuuko_user_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.exception(f"Error clearing memory for user {ryuuko_user_id}: {e}")
            return False

    # =====================================
    # USER CONFIG METHODS
    # =====================================

    def get_user_config(self, ryuuko_user_id: str) -> Dict[str, Any]:
        try:
            result = self.db[self.COLLECTIONS['user_config']].find_one({"ryuuko_user_id": ryuuko_user_id})
            if result:
                return {
                    "model": result.get("model", "ryuuko-r1-vnm-pro"),
                    "system_prompt": result.get("system_prompt", "Tên của bạn là Ryuuko (nữ), nói tiếng việt"),
                    "credit": result.get("credit", 0),
                    "access_level": result.get("access_level", 0)
                }
            return {
                "model": "ryuuko-r1-vnm-pro", "system_prompt": "Tên của bạn là Ryuuko (nữ), nói tiếng việt", "credit": 0, "access_level": 0
            }
        except Exception as e:
            logger.exception(f"Error getting user config for {ryuuko_user_id}: {e}")
            return {"model": "ryuuko-r1-vnm-pro", "system_prompt": "Tên của bạn là Ryuuko (nữ), nói tiếng việt", "credit": 0, "access_level": 0}

    def set_user_config(self, ryuuko_user_id: str, model: Optional[str] = None, system_prompt: Optional[str] = None) -> bool:
        try:
            update_data = {"updated_at": datetime.utcnow()}
            if model is not None:
                update_data["model"] = model
            if system_prompt is not None:
                update_data["system_prompt"] = system_prompt

            self.db[self.COLLECTIONS['user_config']].update_one(
                {"ryuuko_user_id": ryuuko_user_id},
                {"$set": update_data, "$setOnInsert": {"ryuuko_user_id": ryuuko_user_id, "created_at": datetime.utcnow()}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.exception(f"Error setting user config for {ryuuko_user_id}: {e}")
            return False

    def get_user_model(self, ryuuko_user_id: str) -> str:
        return self.get_user_config(ryuuko_user_id)["model"]

    def get_user_system_prompt(self, ryuuko_user_id: str) -> str:
        return self.get_user_config(ryuuko_user_id)["system_prompt"]

    def get_user_system_message(self, ryuuko_user_id: str) -> Dict[str, str]:
        return {"role": "system", "content": self.get_user_system_prompt(ryuuko_user_id)}

    # =====================================
    # SUPPORTED MODELS METHODS
    # =====================================

    def get_supported_models(self) -> Set[str]:
        try:
            results = self.db[self.COLLECTIONS['models']].find({}, {"model_name": 1})
            return {doc["model_name"] for doc in results}
        except Exception as e:
            logger.exception(f"Error getting supported models: {e}")
            return set()

    def model_exists(self, model_name: str) -> bool:
        try:
            return self.db[self.COLLECTIONS['models']].count_documents({"model_name": model_name}) > 0
        except Exception as e:
            logger.exception(f"Error checking if model {model_name} exists: {e}")
            return False

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        try:
            return self.db[self.COLLECTIONS['models']].find_one({"model_name": model_name})
        except Exception as e:
            logger.exception(f"Error getting model info for {model_name}: {e}")
            return None

    def list_all_models(self) -> List[Dict[str, Any]]:
        try:
            return list(self.db[self.COLLECTIONS['models']].find({}).sort("created_at", 1))
        except Exception as e:
            logger.exception(f"Error listing all models: {e}")
            return []

    # =====================================
    # AUTHORIZED USERS METHODS (Uses Discord ID)
    # =====================================

    def get_authorized_users(self) -> Set[int]:
        try:
            results = self.db[self.COLLECTIONS['authorized']].find({}, {"user_id": 1})
            return {doc["user_id"] for doc in results}
        except Exception as e:
            logger.exception(f"Error getting authorized users: {e}")
            return set()

    def add_authorized_user(self, user_id: int) -> bool:
        try:
            self.db[self.COLLECTIONS['authorized']].update_one(
                {"user_id": user_id},
                {"$setOnInsert": {"user_id": user_id, "created_at": datetime.utcnow()}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.exception(f"Error adding authorized user {user_id}: {e}")
            return False

    def remove_authorized_user(self, user_id: int) -> bool:
        try:
            result = self.db[self.COLLECTIONS['authorized']].delete_one({"user_id": user_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.exception(f"Error removing authorized user {user_id}: {e}")
            return False

    # =====================================
    # USER LEVEL AND CREDIT METHODS
    # =====================================

    def deduct_user_credit(self, ryuuko_user_id: str, amount: int) -> tuple[bool, int]:
        try:
            user_config = self.get_user_config(ryuuko_user_id)
            if user_config.get("credit", 0) < amount:
                return False, user_config.get("credit", 0)

            result = self.db[self.COLLECTIONS['user_config']].find_one_and_update(
                {"ryuuko_user_id": ryuuko_user_id, "credit": {"$gte": amount}},
                {"$inc": {"credit": -amount}, "$set": {"updated_at": datetime.utcnow()}},
                return_document=True
            )
            if result:
                return True, result.get("credit", 0)
            return False, user_config.get("credit", 0)
        except Exception as e:
            logger.exception(f"Error deducting credit for user {ryuuko_user_id}: {e}")
            return False, 0

    def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

# Singleton instance
_mongodb_store: Optional[MongoDBStore] = None

def get_mongodb_store() -> MongoDBStore:
    global _mongodb_store
    if _mongodb_store is None:
        raise RuntimeError("MongoDB store not initialized.")
    return _mongodb_store

def init_mongodb_store(connection_string: str, database_name: str = "discord_openai_proxy") -> MongoDBStore:
    global _mongodb_store
    if _mongodb_store is None:
        _mongodb_store = MongoDBStore(connection_string, database_name)
    return _mongodb_store

def close_mongodb_store():
    global _mongodb_store
    if _mongodb_store:
        _mongodb_store.close()
        _mongodb_store = None