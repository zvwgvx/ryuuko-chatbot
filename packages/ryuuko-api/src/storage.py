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
            'supported_models': 'supported_models',
            'memory_nodes': 'memory_nodes',
            'memory_summaries': 'memory_summaries'
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
            self.db[self.COLLECTIONS['supported_models']].create_index("model_name", unique=True)
            # New indexes for hierarchical memory system
            self.db[self.COLLECTIONS['memory_nodes']].create_index([("user_id", 1), ("timestamp", -1)])
            self.db[self.COLLECTIONS['memory_summaries']].create_index("user_id", unique=True)
            logger.info("All database indexes ensured.")
        except OperationFailure as e:
            logger.warning(f"Could not create an index, it may already exist with different options: {e}")
        except Exception as e:
            logger.exception(f"An unexpected error occurred during index initialization: {e}")

    # --- User Management ---
    def create_dashboard_user(self, username: str, email: str, hashed_password: str, first_name: str, last_name: str, dob: datetime, access_level: int = 0) -> Optional[str]:
        """Creates a new user for the dashboard with expanded profile information."""
        try:
            result = self.db[self.COLLECTIONS['dashboard_users']].insert_one({
                "username": username,
                "email": email,
                "hashed_password": hashed_password,
                "first_name": first_name,
                "last_name": last_name,
                "date_of_birth": dob,
                "credit": 0,
                "access_level": access_level,
                "system_prompt": None,
                "model": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            return str(result.inserted_id)
        except DuplicateKeyError:
            return None

    def create_or_update_owner_user(self, username: str, email: str, hashed_password: str, first_name: str, last_name: str):
        """Ensures the owner user, defined by config, exists with correct credentials and permissions."""
        owner_defaults = {
            "username": username,
            "email": email,
            "hashed_password": hashed_password,
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": datetime(1970, 1, 1),
            "credit": 999999,
            "access_level": 3,
            "updated_at": datetime.utcnow()
        }
        self.db[self.COLLECTIONS['dashboard_users']].update_one(
            {"username": username},
            {
                "$set": owner_defaults,
                "$setOnInsert": {"created_at": datetime.utcnow()}
            },
            upsert=True
        )
        logger.info(f"Default owner user ({username}) checked and ensured.")

    def get_dashboard_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        return self.db[self.COLLECTIONS['dashboard_users']].find_one({"username": username})

    def get_dashboard_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        try: return self.db[self.COLLECTIONS['dashboard_users']].find_one({"_id": ObjectId(user_id)})
        except Exception: return None

    # --- Model Management ---
    def get_all_models(self) -> List[Dict[str, Any]]:
        """Retrieves a list of all supported models from the database."""
        return list(self.db[self.COLLECTIONS['supported_models']].find({}, {"_id": 0}))

    def get_model_by_name(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single model's details by its name."""
        return self.db[self.COLLECTIONS['supported_models']].find_one({"model_name": model_name}, {"_id": 0})

    # --- Account Linking ---
    def create_link_code(self, user_id: str) -> str:
        import random, string
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        self.db[self.COLLECTIONS['link_codes']].insert_one({"code": code, "user_id": user_id, "created_at": datetime.utcnow()})
        return code

    def validate_link_code(self, code: str) -> Optional[str]:
        doc = self.db[self.COLLECTIONS['link_codes']].find_one_and_delete({"code": code.upper()})
        return str(doc["user_id"]) if doc else None

    def create_linked_account(self, user_id: str, platform: str, platform_user_id: str, platform_display_name: str, platform_avatar_url: Optional[str] = None) -> tuple[bool, str]:
        try:
            self.db[self.COLLECTIONS['linked_accounts']].update_one(
                {"user_id": ObjectId(user_id), "platform": platform},
                {
                    "$set": {
                        "platform_user_id": platform_user_id, 
                        "platform_display_name": platform_display_name, 
                        "platform_avatar_url": platform_avatar_url,
                        "updated_at": datetime.utcnow()
                    },
                    "$setOnInsert": {"created_at": datetime.utcnow()}
                },
                upsert=True
            )
            return True, "Account linked successfully."
        except DuplicateKeyError: return False, "This platform account is already linked to another user."
        except Exception as e: return False, f"An internal error occurred: {e}"

    def find_linked_account(self, platform: str, platform_user_id: str) -> Optional[Dict[str, Any]]:
        return self.db[self.COLLECTIONS['linked_accounts']].find_one({"platform": platform, "platform_user_id": platform_user_id})

    def get_linked_accounts_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            accounts = list(self.db[self.COLLECTIONS['linked_accounts']].find({"user_id": ObjectId(user_id)}))
            for acc in accounts:
                acc['_id'] = str(acc['_id'])
                acc['user_id'] = str(acc['user_id'])
            return accounts
        except Exception as e:
            logger.error(f"Error retrieving linked accounts for user {user_id}: {e}")
            return []

    def delete_linked_account(self, platform: str, platform_user_id: str) -> bool:
        """Deletes a linked account record. Returns True if an account was deleted."""
        result = self.db[self.COLLECTIONS['linked_accounts']].delete_one(
            {"platform": platform, "platform_user_id": platform_user_id}
        )
        return result.deleted_count > 0

    # --- DEPRECATED: Legacy Memory Management (DO NOT USE) ---
    # These methods are kept for backward compatibility only.
    # Use hierarchical memory system (memory_nodes + memory_summaries) instead.

    def get_user_memory(self, user_id: str) -> List[Dict[str, Any]]:
        """
        DEPRECATED: Use memory_manager.get_history() instead.
        This uses the old linear memory system.
        """
        logger.warning("get_user_memory() is DEPRECATED - use memory_manager.get_history()")
        result = self.db[self.COLLECTIONS['user_memory']].find_one({"user_id": ObjectId(user_id)})
        return result.get("messages", []) if result else []

    def add_message_to_memory(self, user_id: str, message: Dict[str, Any]):
        """
        DEPRECATED: Use memory_manager.add_message() instead.
        This uses the old linear memory system.
        """
        logger.warning("add_message_to_memory() is DEPRECATED - use memory_manager.add_message()")
        self.db[self.COLLECTIONS['user_memory']].update_one(
            {"user_id": ObjectId(user_id)},
            {"$push": {"messages": message}, "$set": {"updated_at": datetime.utcnow()}},
            upsert=True
        )

    def clear_user_memory(self, user_id: str) -> bool:
        """
        DEPRECATED: Use memory_manager.clear_history() instead.
        This uses the old linear memory system.
        """
        logger.warning("clear_user_memory() is DEPRECATED - use memory_manager.clear_history()")
        result = self.db[self.COLLECTIONS['user_memory']].delete_one({"user_id": ObjectId(user_id)})
        return result.deleted_count > 0

    # --- User Profile & Config ---
    def update_user_profile(self, user_id: str, update_data: Dict[str, Any]) -> tuple[bool, str]:
        """Updates a user's profile information."""
        if not update_data:
            return False, "No update data provided."

        update_data["updated_at"] = datetime.utcnow()

        try:
            result = self.db[self.COLLECTIONS['dashboard_users']].update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )
            if result.modified_count > 0:
                return True, "Profile updated successfully."
            return True, "Profile was not modified."
        except DuplicateKeyError:
            return False, "The specified email is already in use."
        except Exception as e:
            logger.error(f"Error updating profile for user {user_id}: {e}")
            return False, "An internal error occurred during profile update."

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

    # --- Hierarchical Memory System: Memory Nodes ---
    def add_memory_node(
        self,
        user_id: str,
        role: str,
        text_content: str,
        semantic_vector: List[float]
    ) -> str:
        """
        Add a new memory node with semantic embedding.

        Args:
            user_id: User ID
            role: Message role ('user' or 'assistant')
            text_content: Text content of the message
            semantic_vector: Embedding vector for the text

        Returns:
            Inserted document ID as string
        """
        try:
            result = self.db[self.COLLECTIONS['memory_nodes']].insert_one({
                "user_id": ObjectId(user_id),
                "timestamp": datetime.utcnow(),
                "role": role,
                "text_content": text_content,
                "semantic_vector": semantic_vector
            })
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error adding memory node for user {user_id}: {e}")
            raise

    def get_recent_memory_nodes(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get the most recent memory nodes for a user (sliding window).

        Args:
            user_id: User ID
            limit: Number of recent nodes to retrieve

        Returns:
            List of memory node documents
        """
        try:
            nodes = list(
                self.db[self.COLLECTIONS['memory_nodes']]
                .find({"user_id": ObjectId(user_id)})
                .sort("timestamp", -1)
                .limit(limit)
            )
            # Reverse to get chronological order
            nodes.reverse()
            return nodes
        except Exception as e:
            logger.error(f"Error retrieving recent memory nodes for user {user_id}: {e}")
            return []

    def search_similar_memory_nodes(
        self,
        user_id: str,
        query_vector: List[float],
        limit: int = 10,
        exclude_recent: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for similar memory nodes using cosine similarity (RAG retrieval).

        Args:
            user_id: User ID
            query_vector: Query embedding vector
            limit: Number of similar nodes to retrieve
            exclude_recent: Exclude this many most recent messages from search

        Returns:
            List of similar memory node documents with similarity scores
        """
        try:
            import numpy as np

            # Get all nodes except recent ones
            all_nodes = list(
                self.db[self.COLLECTIONS['memory_nodes']]
                .find({"user_id": ObjectId(user_id)})
                .sort("timestamp", -1)
                .skip(exclude_recent)
            )

            if not all_nodes:
                return []

            # Compute similarities
            query_vec = np.array(query_vector)
            similarities = []

            for node in all_nodes:
                node_vec = np.array(node['semantic_vector'])

                # Cosine similarity
                dot_product = np.dot(query_vec, node_vec)
                norm_query = np.linalg.norm(query_vec)
                norm_node = np.linalg.norm(node_vec)

                if norm_query == 0 or norm_node == 0:
                    similarity = 0.0
                else:
                    similarity = dot_product / (norm_query * norm_node)

                similarities.append({
                    'node': node,
                    'similarity': float(similarity)
                })

            # Sort by similarity (highest first) and return top N
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            top_similar = similarities[:limit]

            # Return just the nodes with their similarity scores
            return [
                {**item['node'], 'similarity_score': item['similarity']}
                for item in top_similar
            ]

        except Exception as e:
            logger.error(f"Error searching similar memory nodes for user {user_id}: {e}")
            return []

    def clear_memory_nodes(self, user_id: str) -> bool:
        """Clear all memory nodes for a user."""
        try:
            result = self.db[self.COLLECTIONS['memory_nodes']].delete_many(
                {"user_id": ObjectId(user_id)}
            )
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error clearing memory nodes for user {user_id}: {e}")
            return False

    # --- Hierarchical Memory System: Summaries ---
    def get_memory_summary(self, user_id: str) -> Optional[str]:
        """
        Get the contextual summary for a user.

        Args:
            user_id: User ID

        Returns:
            Summary text or None if not exists
        """
        try:
            result = self.db[self.COLLECTIONS['memory_summaries']].find_one(
                {"user_id": ObjectId(user_id)}
            )
            return result.get("summary_text") if result else None
        except Exception as e:
            logger.error(f"Error retrieving memory summary for user {user_id}: {e}")
            return None

    def update_memory_summary(self, user_id: str, summary_text: str) -> bool:
        """
        Update or create the contextual summary for a user.

        Args:
            user_id: User ID
            summary_text: New summary text

        Returns:
            True if successful
        """
        try:
            self.db[self.COLLECTIONS['memory_summaries']].update_one(
                {"user_id": ObjectId(user_id)},
                {
                    "$set": {
                        "summary_text": summary_text,
                        "updated_at": datetime.utcnow()
                    },
                    "$setOnInsert": {"created_at": datetime.utcnow()}
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error updating memory summary for user {user_id}: {e}")
            return False

    def clear_memory_summary(self, user_id: str) -> bool:
        """Clear the memory summary for a user."""
        try:
            result = self.db[self.COLLECTIONS['memory_summaries']].delete_one(
                {"user_id": ObjectId(user_id)}
            )
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error clearing memory summary for user {user_id}: {e}")
            return False

    def close(self):
        if self.client: self.client.close()
