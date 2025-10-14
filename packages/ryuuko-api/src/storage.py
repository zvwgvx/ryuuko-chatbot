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

logger = logging.getLogger("RyuukoAPI.Storage")

class MongoDBStore:
    """Manages all database interactions for the Ryuuko ecosystem."""
    def __init__(self, connection_string: str, database_name: str = "polydevsdb"):
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[MongoClient] = None
        self.db = None

        # Initialize the genai model for token counting
        self.genai_model = None
        if genai:
            try:
                api_key = os.getenv("GEMINI_API_KEY") or os.getenv("AISTUDIO_API_KEY")
                if api_key:
                    genai.configure(api_key=api_key)
                    self.genai_model = genai.GenerativeModel('gemini-2.5-flash')
                else:
                    logger.warning("GEMINI_API_KEY not found. Token counting will use estimations.")
            except Exception as e:
                logger.error(f"Failed to initialize genai for token counting: {e}")
        
        self.COLLECTIONS = {'user_config': 'user_configs', 'memory': 'user_memory', 'authorized': 'authorized_users', 'models': 'supported_models'}
        self._connect()
        self._initialize_default_models()

    def _connect(self):
        """Establishes the MongoDB connection."""
        try:
            conn_str = self.connection_string
            if "retryWrites" not in conn_str:
                conn_str += "&retryWrites=false" if "?" in conn_str else "?retryWrites=false"
            self.client = MongoClient(conn_str, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client[self.database_name]
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def _initialize_default_models(self):
        """Initializes the database with default models if the collection is empty."""
        try:
            if self.db[self.COLLECTIONS['models']].count_documents({}) == 0:
                self.db[self.COLLECTIONS['models']].insert_many([
                    {"model_name": "ryuuko-r1-vnm-mini", "created_at": datetime.utcnow(), "credit_cost": 100, "access_level": 3},
                    {"model_name": "ryuuko-r1-eng-mini", "created_at": datetime.utcnow(), "credit_cost": 100, "access_level": 3},
                ])
        except Exception as e:
            logger.exception(f"Error initializing default models: {e}")

    def get_user_messages(self, user_id: int) -> List[Dict[str, Any]]:
        """Retrieves the conversation history for a user."""
        result = self.db[self.COLLECTIONS['memory']].find_one({"user_id": user_id})
        return result.get("messages", []) if result else []

    def add_message(self, user_id: int, message: Dict[str, Any], max_messages: int = 25, max_tokens: int = 8000):
        """Adds a message to a user's history and applies memory limits."""
        current_doc = self.db[self.COLLECTIONS['memory']].find_one({"user_id": user_id})
        current_messages = current_doc.get("messages", []) if current_doc else []
        updated_messages = self._apply_memory_limits(current_messages + [message], max_messages, max_tokens)
        self.db[self.COLLECTIONS['memory']].update_one(
            {"user_id": user_id},
            {"$set": {"messages": updated_messages, "updated_at": datetime.utcnow()}},
            upsert=True
        )

    def _count_tokens_for_message(self, msg: Dict[str, Any]) -> int:
        """Calculates the token count for a single message, handling multimodal content."""
        content = msg.get("content")
        if not content: return 0
        if not self.genai_model:
            return len(json.dumps(content)) // 4 # Fallback estimation
        try:
            if isinstance(content, str):
                return self.genai_model.count_tokens(content).total_tokens
            if isinstance(content, list):
                genai_parts = []
                for part in content:
                    if part.get("type") == "text": genai_parts.append(part.get("text", ""))
                    elif part.get("type") == "image_url":
                        image_url = part.get("image_url", {}).get("url", "")
                        if image_url.startswith("data:"):
                            header, b64_data = image_url.split(",", 1)
                            mime_type = header.split(":")[1].split(";")[0]
                            genai_parts.append({'inline_data': {'mime_type': mime_type, 'data': b64_data}})
                return self.genai_model.count_tokens(genai_parts).total_tokens
        except Exception as e:
            logger.error(f"Token count failed, falling back to estimation: {e}")
        return len(json.dumps(content)) // 4 # Fallback estimation

    def _apply_memory_limits(self, messages: List[Dict[str, Any]], max_messages: int, max_tokens: int) -> List[Dict[str, Any]]:
        """Trims conversation history based on message count and token limits."""
        if len(messages) > max_messages: messages = messages[-max_messages:]
        token_counts = [self._count_tokens_for_message(msg) for msg in messages]
        total_tokens = sum(token_counts)
        if total_tokens > max_tokens:
            final_messages = []
            current_tokens = 0
            for i in range(len(messages) - 1, -1, -1):
                if current_tokens + token_counts[i] <= max_tokens:
                    final_messages.insert(0, messages[i])
                    current_tokens += token_counts[i]
                else: break
            return final_messages
        return messages

    def clear_user_memory(self, user_id: int) -> bool:
        """Clears a user's conversation history by setting the messages array to empty."""
        self.db[self.COLLECTIONS['memory']].update_one(
            {"user_id": user_id},
            {"$set": {"messages": [], "updated_at": datetime.utcnow()}},
            upsert=True
        )
        return True

    def get_user_config(self, user_id: int) -> Dict[str, Any]:
        """Retrieves a user's configuration, providing defaults if none exists."""
        result = self.db[self.COLLECTIONS['user_config']].find_one({"user_id": user_id}) or {}
        return {
            "model": result.get("model", "gemini-2.5-flash"),
            "system_prompt": result.get("system_prompt", "Your name is Ryuuko, a helpful and friendly female AI assistant."),
            "credit": result.get("credit", 0),
            "access_level": result.get("access_level", 0)
        }

    def set_user_config(self, user_id: int, model: Optional[str] = None, system_prompt: Optional[str] = None) -> bool:
        """Updates a user's configuration (model and/or system prompt)."""
        update_data = {"updated_at": datetime.utcnow()}
        if model is not None: update_data["model"] = model
        if system_prompt is not None: update_data["system_prompt"] = system_prompt
        self.db[self.COLLECTIONS['user_config']].update_one(
            {"user_id": user_id},
            {"$set": update_data, "$setOnInsert": {"user_id": user_id, "created_at": datetime.utcnow()}},
            upsert=True
        )
        return True

    def list_all_models(self) -> List[Dict[str, Any]]:
        """Returns a list of all supported models."""
        return list(self.db[self.COLLECTIONS['models']].find({}))

    def add_supported_model(self, model_name: str, credit_cost: int, access_level: int) -> tuple[bool, str]:
        """Adds a new model to the list of supported models."""
        try:
            self.db[self.COLLECTIONS['models']].insert_one({
                "model_name": model_name, "credit_cost": credit_cost, "access_level": access_level, "created_at": datetime.utcnow()
            })
            return True, f"Successfully added model '{model_name}'"
        except Exception as e: return False, str(e)

    def remove_supported_model(self, model_name: str) -> tuple[bool, str]:
        """Removes a model from the list of supported models."""
        try:
            result = self.db[self.COLLECTIONS['models']].delete_one({"model_name": model_name})
            if result.deleted_count > 0: return True, f"Successfully removed model '{model_name}'"
            return False, f"Model '{model_name}' not found."
        except Exception as e: return False, str(e)

    def add_user_credit(self, user_id: int, amount: int) -> tuple[bool, int]:
        """Adds credits to a user's balance."""
        result = self.db[self.COLLECTIONS['user_config']].find_one_and_update(
            {"user_id": user_id},
            {"$inc": {"credit": amount}, "$set": {"updated_at": datetime.utcnow()}},
            upsert=True, return_document=True
        )
        return True, result.get("credit", 0)

    def deduct_user_credit(self, user_id: int, amount: int) -> tuple[bool, int]:
        """Deducts credits from a user's balance, checking for sufficient funds first."""
        user_config = self.get_user_config(user_id)
        if user_config.get("credit", 0) < amount:
            return False, user_config.get("credit", 0)
        result = self.db[self.COLLECTIONS['user_config']].find_one_and_update(
            {"user_id": user_id},
            {"$inc": {"credit": -amount}, "$set": {"updated_at": datetime.utcnow()}},
            return_document=True
        )
        return True, result.get("credit", 0)

    def set_user_credit(self, user_id: int, amount: int) -> bool:
        """Sets a user's credit balance to a specific amount."""
        self.db[self.COLLECTIONS['user_config']].update_one(
            {"user_id": user_id},
            {"$set": {"credit": amount, "updated_at": datetime.utcnow()}},
            upsert=True
        )
        return True

    def set_user_level(self, user_id: int, level: int) -> bool:
        """Sets a user's access level."""
        self.db[self.COLLECTIONS['user_config']].update_one(
            {"user_id": user_id},
            {"$set": {"access_level": level, "updated_at": datetime.utcnow()}},
            upsert=True
        )
        return True

    def get_authorized_users(self) -> Set[int]:
        """Gets the set of all authorized user IDs."""
        return {doc["user_id"] for doc in self.db[self.COLLECTIONS['authorized']].find({}, {"user_id": 1})}

    def add_authorized_user(self, user_id: int) -> bool:
        """Adds a user to the authorized list."""
        self.db[self.COLLECTIONS['authorized']].update_one(
            {"user_id": user_id},
            {"$setOnInsert": {"user_id": user_id, "created_at": datetime.utcnow()}},
            upsert=True
        )
        return True

    def remove_authorized_user(self, user_id: int) -> bool:
        """Removes a user from the authorized list."""
        result = self.db[self.COLLECTIONS['authorized']].delete_one({"user_id": user_id})
        return result.deleted_count > 0

    def close(self):
        """Closes the MongoDB connection."""
        if self.client: self.client.close()
