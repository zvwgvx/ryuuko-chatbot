#!/usr/bin/env python3
# coding: utf-8
# user.py - User configuration management with MANDATORY MongoDB

import logging
from typing import Dict, Any, Optional, Set
from src.config import loader

logger = logging.getLogger("Config.User")

# Default values
DEFAULT_SYSTEM_PROMPT = "Tên của bạn là Ryuuko (nữ), nói tiếng việt"
DEFAULT_MODEL = "gemini-2.5-flash"

# Fallback models list (used only if MongoDB has no models)
FALLBACK_SUPPORTED_MODELS = {
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gpt-4o-mini",
    "gpt-3.5-turbo",
    "ryuuko-r1-vnm-mini"
}


class UserConfigManager:
    """User configuration manager - MongoDB ONLY, NO FALLBACK"""

    def __init__(self):
        # MANDATORY MongoDB check
        if not loader.USE_MONGODB:
            raise RuntimeError("❌ MongoDB is MANDATORY for UserConfigManager")  # Keep emoji for user error

        # Initialize MongoDB store
        try:
            from src.storage.database import get_mongodb_store
            self.mongo_store = get_mongodb_store()
            logger.info("[OK] UserConfigManager initialized with MongoDB")  # Changed: log only
        except Exception as e:
            logger.error("[ERROR] Failed to get MongoDB store: %s", e)  # Changed: log only
            raise RuntimeError(f"❌ MongoDB is MANDATORY but not available: {e}")  # Keep emoji for user error

    def get_supported_models(self) -> Set[str]:
        """Get supported models from MongoDB"""
        try:
            models = self.mongo_store.get_supported_models()
            if not models:
                logger.warning("No models in MongoDB, using fallback list")
                return FALLBACK_SUPPORTED_MODELS
            return models
        except Exception as e:
            logger.error(f"Error getting models from MongoDB: {e}")
            raise

    def add_supported_model(self, model_name: str, credit_cost: int = 1, access_level: int = 0) -> tuple[bool, str]:
        """Add a new supported model"""
        return self.mongo_store.add_supported_model(model_name, credit_cost, access_level)

    def remove_supported_model(self, model_name: str) -> tuple[bool, str]:
        """Remove a supported model"""
        return self.mongo_store.remove_supported_model(model_name)

    def edit_supported_model(self, model_name: str, credit_cost: int = None, access_level: int = None) -> tuple[
        bool, str]:
        """Edit model settings"""
        return self.mongo_store.edit_supported_model(model_name, credit_cost, access_level)

    def list_all_models_detailed(self) -> list:
        """Get detailed list of all models"""
        return self.mongo_store.list_all_models()

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed info for a specific model"""
        return self.mongo_store.get_model_info(model_name)

    def get_user_config(self, user_id: int) -> Dict[str, Any]:
        """Get user configuration from MongoDB"""
        return self.mongo_store.get_user_config(user_id)

    def get_user_model(self, user_id: int) -> str:
        """Get user's selected model"""
        return self.mongo_store.get_user_model(user_id)

    def get_user_system_prompt(self, user_id: int) -> str:
        """Get user's system prompt"""
        return self.mongo_store.get_user_system_prompt(user_id)

    def get_user_system_message(self, user_id: int) -> Dict[str, str]:
        """Get user's system message in OpenAI format"""
        return self.mongo_store.get_user_system_message(user_id)

    def get_user_credit(self, user_id: int) -> int:
        """Get user's credit balance"""
        config = self.get_user_config(user_id)
        return config.get("credit", 0)

    def get_user_access_level(self, user_id: int) -> int:
        """Get user's access level"""
        config = self.get_user_config(user_id)
        return config.get("access_level", 0)

    def set_user_model(self, user_id: int, model: str) -> tuple[bool, str]:
        """Set user's preferred model"""
        # Validate model exists
        supported_models = self.get_supported_models()
        if model not in supported_models:
            supported_list = ", ".join(sorted(supported_models))
            return False, f"Model '{model}' not supported. Available models: {supported_list}"

        # Save to MongoDB
        success = self.mongo_store.set_user_config(user_id, model=model)
        if success:
            return True, f"Model set to '{model}'"
        else:
            return False, "Error saving configuration to MongoDB"

    def set_user_system_prompt(self, user_id: int, prompt: str) -> tuple[bool, str]:
        """Set user's system prompt"""
        # Validate prompt
        if not prompt.strip():
            return False, "System prompt cannot be empty"

        if len(prompt) > 10000:
            return False, "System prompt too long (max 10,000 characters)"

        # Save to MongoDB
        success = self.mongo_store.set_user_config(user_id, system_prompt=prompt.strip())
        if success:
            return True, "System prompt updated"
        else:
            return False, "Error saving configuration to MongoDB"

    def reset_user_config(self, user_id: int) -> str:
        """Reset user configuration to defaults"""
        success = self.mongo_store.set_user_config(
            user_id,
            model=DEFAULT_MODEL,
            system_prompt=DEFAULT_SYSTEM_PROMPT
        )
        if success:
            return "Configuration reset to defaults"
        else:
            return "Error resetting configuration in MongoDB"


# Singleton instance
_user_config_manager = None


def get_user_config_manager() -> UserConfigManager:
    """Get UserConfigManager instance (singleton pattern)"""
    global _user_config_manager
    if _user_config_manager is None:
        _user_config_manager = UserConfigManager()
    return _user_config_manager


# Legacy function for backward compatibility
def get_supported_models() -> Set[str]:
    """DEPRECATED: Use get_user_config_manager().get_supported_models() instead"""
    logger.warning("get_supported_models() is deprecated. Use get_user_config_manager().get_supported_models()")
    return get_user_config_manager().get_supported_models()


# Module variable for backward compatibility
SUPPORTED_MODELS = FALLBACK_SUPPORTED_MODELS