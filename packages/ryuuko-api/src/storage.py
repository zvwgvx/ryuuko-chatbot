#!/usr/bin/env python3
# coding: utf-8

import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, DuplicateKeyError, OperationFailure
from bson import ObjectId

logger = logging.getLogger("RyuukoAPI.Storage")

class MongoDBStore:
    """Manages all database interactions for the Ryuuko ecosystem."""
    def __init__(self, connection_string: str, database_name: str = "ryuukodb"):
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[MongoClient] = None
        self.db = None
        
        self.COLLECTIONS = {
            'dashboard_users': 'dashboard_users',
            'linked_accounts': 'linked_accounts',
            'link_codes': 'temp_link_codes',
            'user_memory': 'user_memory',
            'supported_models': 'supported_models'
        }
        self._connect()
        self._initialize_indexes()

    def _connect(self):
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

    def _initialize_indexes(self):
        """Creates necessary indexes for the collections, handling potential conflicts."""
        try:
            self.db[self.COLLECTIONS['link_codes']].create_index("created_at", expireAfterSeconds=300)
            self.db[self.COLLECTIONS['dashboard_users']].create_index("username", unique=True)
            self.db[self.COLLECTIONS['dashboard_users']].create_index("email", unique=True)
            self.db[self.COLLECTIONS['linked_accounts']].create_index([("platform", 1), ("platform_user_id", 1)], unique=True)
            self.db[self.COLLECTIONS['user_memory']].create_index("user_id", unique=True)
            logger.info("All database indexes ensured.")
        except OperationFailure as e:
            logger.warning(f"Could not create an index, it may already exist with different options: {e}")
        except Exception as e:
            logger.exception(f"An unexpected error occurred during index initialization: {e}")

    # --- User Management ---
    def create_dashboard_user(self, username: str, email: str, hashed_password: str, access_level: int = 0) -> Optional[str]:
        try:
            result = self.db[self.COLLECTIONS['dashboard_users']].insert_one({
                "username": username, "email": email, "hashed_password": hashed_password,
                "credit": 0, "access_level": access_level,
                "system_prompt": None, "model": None,
                "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()
            })
            return str(result.inserted_id)
        except DuplicateKeyError: return None

    def create_or_update_admin_user(self, hashed_password: str):
        """Ensures the admin user exists with correct credentials and permissions."""
        admin_defaults = {
            "username": "zvwgvx",
            "email": "zvwgvx@polydevs.uk",
            "hashed_password": hashed_password,
            "credit": 999999,
            "access_level": 3, # Highest access level
            "updated_at": datetime.utcnow()
        }
        self.db[self.COLLECTIONS['dashboard_users']].update_one(
            {"username": "zvwgvx"},
            {
                "$set": admin_defaults,
                "$setOnInsert": {"created_at": datetime.utcnow()}
            },
            upsert=True
        )
        logger.info("Default admin user (zvwgvx) checked and ensured.")

    def get_dashboard_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        return self.db[self.COLLECTIONS['dashboard_users']].find_one({"username": username})

    def get_dashboard_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        try: return self.db[self.COLLECTIONS['dashboard_users']].find_one({"_id": ObjectId(user_id)})
        except Exception: return None

    # --- Account Linking ---
    def create_link_code(self, user_id: str) -> str:
        import random, string
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        self.db[self.COLLECTIONS['link_codes']].insert_one({"code": code, "user_id": user_id, "created_at": datetime.utcnow()})
        return code

    def validate_link_code(self, code: str) -> Optional[str]:
        doc = self.db[self.COLLECTIONS['link_codes']].find_one_and_delete({"code": code.upper()})
        return str(doc["user_id"]) if doc else None

    def create_linked_account(self, user_id: str, platform: str, platform_user_id: str, platform_display_name: str) -> tuple[bool, str]:
        try:
            self.db[self.COLLECTIONS['linked_accounts']].update_one(
                {"user_id": ObjectId(user_id), "platform": platform},
                {"$set": {"platform_user_id": platform_user_id, "platform_display_name": platform_display_name, "updated_at": datetime.utcnow()}},
                upsert=True
            )
            return True, "Account linked successfully."
        except DuplicateKeyError: return False, "This platform account is already linked to another user."
        except Exception as e: return False, f"An internal error occurred: {e}"

    def find_linked_account(self, platform: str, platform_user_id: str) -> Optional[Dict[str, Any]]:
        return self.db[self.COLLECTIONS['linked_accounts']].find_one({"platform": platform, "platform_user_id": platform_user_id})

    def get_linked_accounts_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            return list(self.db[self.COLLECTIONS['linked_accounts']].find({"user_id": ObjectId(user_id)}, {"_id": 0, "user_id": 0}))
        except Exception as e:
            logger.error(f"Error retrieving linked accounts for user {user_id}: {e}")
            return []

    def delete_linked_account(self, platform: str, platform_user_id: str) -> bool:
        """Deletes a linked account record. Returns True if an account was deleted."""
        result = self.db[self.COLLECTIONS['linked_accounts']].delete_one(
            {"platform": platform, "platform_user_id": platform_user_id}
        )
        return result.deleted_count > 0

    # --- Memory Management ---
    def get_user_memory(self, user_id: str) -> List[Dict[str, Any]]:
        result = self.db[self.COLLECTIONS['user_memory']].find_one({"user_id": ObjectId(user_id)})
        return result.get("messages", []) if result else []

    def add_message_to_memory(self, user_id: str, message: Dict[str, Any]):
        self.db[self.COLLECTIONS['user_memory']].update_one(
            {"user_id": ObjectId(user_id)},
            {"$push": {"messages": message}, "$set": {"updated_at": datetime.utcnow()}},
            upsert=True
        )

    def clear_user_memory(self, user_id: str) -> bool:
        result = self.db[self.COLLECTIONS['user_memory']].delete_one({"user_id": ObjectId(user_id)})
        return result.deleted_count > 0

    # --- User Config ---
    def update_user_config(self, user_id: str, model: Optional[str] = None, system_prompt: Optional[str] = None) -> bool:
        update_data = {"updated_at": datetime.utcnow()}
        if model is not None: update_data["model"] = model
        if system_prompt is not None: update_data["system_prompt"] = system_prompt
        result = self.db[self.COLLECTIONS['dashboard_users']].update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
        return result.modified_count > 0

    # --- Admin-specific Methods ---
    def admin_add_user_credit(self, user_id: str, amount: int) -> tuple[bool, int]:
        result = self.db[self.COLLECTIONS['dashboard_users']].find_one_and_update(
            {"_id": ObjectId(user_id)}, {"$inc": {"credit": amount}, "$set": {"updated_at": datetime.utcnow()}},
            return_document=ReturnDocument.AFTER
        )
        return (True, result.get("credit", 0)) if result else (False, 0)

    def admin_set_user_credit(self, user_id: str, amount: int) -> bool:
        result = self.db[self.COLLECTIONS['dashboard_users']].update_one(
            {"_id": ObjectId(user_id)}, {"$set": {"credit": amount, "updated_at": datetime.utcnow()}})
        return result.modified_count > 0

    def admin_set_user_level(self, user_id: str, level: int) -> bool:
        result = self.db[self.COLLECTIONS['dashboard_users']].update_one(
            {"_id": ObjectId(user_id)}, {"$set": {"access_level": level, "updated_at": datetime.utcnow()}})
        return result.modified_count > 0

    def close(self):
        if self.client: self.client.close()
