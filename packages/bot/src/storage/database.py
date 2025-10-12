#!/usr/bin/env python3
# coding: utf-8

import logging
import os
import json
import base64
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger("Storage.Database")

class MongoDBStore:
    def __init__(self, connection_string: str, database_name: str = "polydevsdb"):
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[MongoClient] = None
        self.db = None

        self.genai_model = None
        if genai:
            try:
                api_key = os.getenv("GEMINI_API_KEY") or os.getenv("AISTUDIO_API_KEY")
                if api_key:
                    genai.configure(api_key=api_key)
                    # SỬA LỖI: Cập nhật phiên bản model
                    self.genai_model = genai.GenerativeModel('gemini-2.5-flash')
                    logger.info("Initialized genai model for token counting.")
                else:
                    logger.warning("GEMINI_API_KEY not found. Token counting will use estimations.")
            except Exception as e:
                logger.error(f"Failed to initialize genai for token counting: {e}")
        else:
            logger.warning("google-generativeai SDK not found. Token counting will use estimations.")

        self.COLLECTIONS = {
            'user_config': 'user_configs',
            'memory': 'user_memory',
            'authorized': 'authorized_users',
            'models': 'supported_models'
        }
        self._connect()
        self._initialize_default_models()

    def _connect(self):
        try:
            conn_str = self.connection_string
            if "retryWrites" not in conn_str:
                conn_str += "&retryWrites=false" if "?" in conn_str else "?retryWrites=false"
            self.client = MongoClient(conn_str, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client[self.database_name]
            self._create_indexes()
            logger.info(f"Successfully connected to MongoDB: {self.database_name}")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def _create_indexes(self):
        try:
            self.db[self.COLLECTIONS['user_config']].create_index("user_id", unique=True)
            self.db[self.COLLECTIONS['memory']].create_index("user_id", unique=True)
            self.db[self.COLLECTIONS['authorized']].create_index("user_id", unique=True)
            self.db[self.COLLECTIONS['models']].create_index("model_name", unique=True)
        except Exception:
            pass

    def _initialize_default_models(self):
        try:
            if self.db[self.COLLECTIONS['models']].count_documents({}) == 0:
                default_models = [
                    {"model_name": "ryuuko-r1-vnm-mini", "created_at": datetime.utcnow(), "credit_cost": 100, "access_level": 3},
                    {"model_name": "ryuuko-r1-eng-mini", "created_at": datetime.utcnow(), "credit_cost": 100, "access_level": 3},
                ]
                self.db[self.COLLECTIONS['models']].insert_many(default_models)
                logger.info("Default models initialized in MongoDB")
        except Exception as e:
            logger.exception(f"Error initializing default models: {e}")

    def get_user_messages(self, user_id: int) -> List[Dict[str, Any]]:
        try:
            result = self.db[self.COLLECTIONS['memory']].find_one({"user_id": user_id})
            return result.get("messages", []) if result else []
        except Exception as e:
            logger.exception(f"Error getting messages for user {user_id}: {e}")
            return []

    def add_message(self, user_id: int, message: Dict[str, Any], max_messages: int = 25, max_tokens: int = 8000):
        try:
            current_doc = self.db[self.COLLECTIONS['memory']].find_one({"user_id": user_id})
            current_messages = current_doc.get("messages", []) if current_doc else []
            updated_messages = self._apply_memory_limits(current_messages + [message], max_messages, max_tokens)
            self.db[self.COLLECTIONS['memory']].update_one(
                {"user_id": user_id},
                {"$set": {"messages": updated_messages, "updated_at": datetime.utcnow(), "message_count": len(updated_messages)}},
                upsert=True
            )
            logger.info(f"Successfully added message for user {user_id}. Total messages: {len(updated_messages)}")
        except Exception as e:
            logger.exception(f"Error adding message for user {user_id}: {e}")

    def _count_tokens_for_message(self, msg: Dict[str, Any]) -> int:
        content = msg.get("content")
        if not content: return 0
        if not self.genai_model: return len(json.dumps(content)) // 4
        try:
            if isinstance(content, str):
                return self.genai_model.count_tokens(content).total_tokens
            if isinstance(content, list):
                genai_parts = []
                for part in content:
                    if part.get("type") == "text":
                        genai_parts.append(part.get("text", ""))
                    elif part.get("type") == "image_url":
                        image_url = part.get("image_url", {}).get("url", "")
                        if image_url.startswith("data:"):
                            header, b64_data = image_url.split(",", 1)
                            mime_type = header.split(":")[1].split(";")[0]
                            genai_parts.append({'inline_data': {'mime_type': mime_type, 'data': b64_data}})
                return self.genai_model.count_tokens(genai_parts).total_tokens
        except Exception as e:
            logger.error(f"Failed to count tokens with genai, falling back to estimation. Error: {e}")
        return len(json.dumps(content)) // 4

    def _apply_memory_limits(self, messages: List[Dict[str, Any]], max_messages: int, max_tokens: int) -> List[Dict[str, Any]]:
        if len(messages) > max_messages:
            messages = messages[-max_messages:]
        token_counts = [self._count_tokens_for_message(msg) for msg in messages]
        total_tokens = sum(token_counts)
        if total_tokens > max_tokens:
            final_messages = []
            current_tokens = 0
            for i in range(len(messages) - 1, -1, -1):
                if current_tokens + token_counts[i] <= max_tokens:
                    final_messages.insert(0, messages[i])
                    current_tokens += token_counts[i]
                else:
                    break
            logger.debug(f"Trimmed messages from {len(messages)} to {len(final_messages)} due to token limit")
            return final_messages
        return messages

    def clear_user_memory(self, user_id: int) -> bool:
        try:
            result = self.db[self.COLLECTIONS['memory']].delete_one({"user_id": user_id})
            logger.info(f"Cleared memory for user {user_id}")
            return result.deleted_count > 0
        except Exception as e:
            logger.exception(f"Error clearing memory for user {user_id}: {e}")
            return False

    def get_user_config(self, user_id: int) -> Dict[str, Any]:
        try:
            result = self.db[self.COLLECTIONS['user_config']].find_one({"user_id": user_id})
            if result:
                return {
                    "model": result.get("model", "gemini-2.5-flash"),
                    "system_prompt": result.get("system_prompt", "Tên của bạn là Ryuuko (nữ), nói tiếng việt"),
                    "credit": result.get("credit", 0),
                    "access_level": result.get("access_level", 0)
                }
            else:
                return {
                    "model": "gemini-2.5-flash",
                    "system_prompt": "Tên của bạn là Ryuuko (nữ), nói tiếng việt",
                    "credit": 0,
                    "access_level": 0
                }
        except Exception as e:
            logger.exception(f"Error getting user config for {user_id}: {e}")
            return {"model": "gemini-2.5-flash", "system_prompt": "Tên của bạn là Ryuuko (nữ), nói tiếng việt", "credit": 0, "access_level": 0}

    def set_user_config(self, user_id: int, model: Optional[str] = None, system_prompt: Optional[str] = None) -> bool:
        try:
            update_data = {"updated_at": datetime.utcnow()}
            if model is not None: update_data["model"] = model
            if system_prompt is not None: update_data["system_prompt"] = system_prompt
            self.db[self.COLLECTIONS['user_config']].update_one(
                {"user_id": user_id},
                {"$set": update_data, "$setOnInsert": {"user_id": user_id, "created_at": datetime.utcnow()}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.exception(f"Error setting user config for {user_id}: {e}")
            return False

    def get_user_model(self, user_id: int) -> str:
        return self.get_user_config(user_id)["model"]

    def get_user_system_prompt(self, user_id: int) -> str:
        return self.get_user_config(user_id)["system_prompt"]

    def get_user_system_message(self, user_id: int) -> Dict[str, str]:
        return {"role": "system", "content": self.get_user_system_prompt(user_id)}

    def get_supported_models(self) -> Set[str]:
        try:
            return {doc["model_name"] for doc in self.db[self.COLLECTIONS['models']].find({}, {"model_name": 1})}
        except Exception as e:
            logger.exception(f"Error getting supported models: {e}")
            return {"gemini-2.5-flash"}

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

    def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

_mongodb_store: Optional[MongoDBStore] = None

def get_mongodb_store() -> MongoDBStore:
    global _mongodb_store
    if _mongodb_store is None: raise RuntimeError("MongoDB store not initialized.")
    return _mongodb_store

def init_mongodb_store(connection_string: str, database_name: str = "discord_openai_proxy") -> MongoDBStore:
    global _mongodb_store
    if _mongodb_store is None: _mongodb_store = MongoDBStore(connection_string, database_name)
    return _mongodb_store

def close_mongodb_store():
    global _mongodb_store
    if _mongodb_store:
        _mongodb_store.close()
        _mongodb_store = None
