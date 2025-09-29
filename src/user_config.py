#!/usr/bin/env python3
# coding: utf-8
# user_config.py - User configuration management with MongoDB support

import logging
from pathlib import Path
from typing import Dict, Any, Optional, Set
import load_config

logger = logging.getLogger("Config")

# User config file path (fallback for file mode)
BASE_DIR = Path(__file__).resolve().parent.parent
CONF_DIR = BASE_DIR / "config"

# Supported models (FALLBACK - will be fetched from database in MongoDB mode)
FALLBACK_SUPPORTED_MODELS = {
    "ryuuko-r1-vnm-mini",
}

DEFAULT_SYSTEM_PROMPT = (
    "Tên của bạn là Ryuuko (nữ), nói tiếng việt"
)

# Default model
DEFAULT_MODEL = "gemini-2.5-flash"

class UserConfigManager:
    def __init__(self):
        self.use_mongodb = load_config.USE_MONGODB

        # MongoDB mode
        from database import get_mongodb_store
        self.mongo_store = get_mongodb_store()
        logger.info("UserConfigManager initialized with MongoDB")

    def get_supported_models(self) -> Set[str]:
        return self.mongo_store.get_supported_models()

    def add_supported_model(self, model_name: str, credit_cost: int = 1, access_level: int = 0) -> tuple[bool, str]:
        return self.mongo_store.add_supported_model(model_name, credit_cost, access_level)

    def remove_supported_model(self, model_name: str) -> tuple[bool, str]:
        return self.mongo_store.remove_supported_model(model_name)

    def edit_supported_model(self, model_name: str, credit_cost: int = None, access_level: int = None) -> tuple[bool, str]:
        return self.mongo_store.edit_supported_model(model_name, credit_cost, access_level)

    def list_all_models_detailed(self) -> list:
        return self.mongo_store.list_all_models()

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        return self.mongo_store.get_model_info(model_name)

    def get_user_config(self, user_id: int) -> Dict[str, Any]:
        return self.mongo_store.get_user_config(user_id)

    def get_user_model(self, user_id: int) -> str:
        return self.mongo_store.get_user_model(user_id)

    def get_user_system_prompt(self, user_id: int) -> str:
        return self.mongo_store.get_user_system_prompt(user_id)

    def get_user_system_message(self, user_id: int) -> Dict[str, str]:
        return self.mongo_store.get_user_system_message(user_id)

    def get_user_credit(self, user_id: int) -> int:
        config = self.get_user_config(user_id)
        return config.get("credit", 0)

    def get_user_access_level(self, user_id: int) -> int:
        config = self.get_user_config(user_id)
        return config.get("access_level", 0)

    def set_user_model(self, user_id: int, model: str) -> tuple[bool, str]:
        """
        Set user's model
        Returns: (success: bool, message: str)
        """
        # Check if model is supported
        supported_models = self.get_supported_models()
        if model not in supported_models:
            supported_list = ", ".join(sorted(supported_models))
            return False, f"Model '{model}' not supported. Available models: {supported_list}"

        success = self.mongo_store.set_user_config(user_id, model=model)
        if success:
            return True, f"Model set to '{model}'"
        else:
            return False, "Error saving configuration to database"

    def set_user_system_prompt(self, user_id: int, prompt: str) -> tuple[bool, str]:
        """
        Set user's system prompt
        Returns: (success: bool, message: str)
        """
        if not prompt.strip():
            return False, "System prompt cannot be empty"

        if len(prompt) > 10000:  # Length limit
            return False, "System prompt too long (max 10,000 characters)"

        success = self.mongo_store.set_user_config(user_id, system_prompt=prompt.strip())
        if success:
            return True, "System prompt updated"
        else:
            return False, "Error saving configuration to database"

    def reset_user_config(self, user_id: int) -> str:
        # Reset config in MongoDB
        success = self.mongo_store.set_user_config(
            user_id,
            model=DEFAULT_MODEL,
            system_prompt=DEFAULT_SYSTEM_PROMPT
        )
        if success:
            return "Configuration reset to defaults"
        else:
            return "Error resetting configuration"


# Singleton instance
_user_config_manager = None


def get_user_config_manager() -> UserConfigManager:
    """Get UserConfigManager instance (singleton pattern)"""
    global _user_config_manager
    if _user_config_manager is None:
        _user_config_manager = UserConfigManager()
    return _user_config_manager


# Legacy functions for backward compatibility (DEPRECATED)
def get_supported_models() -> Set[str]:
    """DEPRECATED: Use get_user_config_manager().get_supported_models() instead"""
    logger.warning("get_supported_models() is deprecated. Use get_user_config_manager().get_supported_models()")
    return get_user_config_manager().get_supported_models()


# Make supported models available as module variable for backward compatibility
SUPPORTED_MODELS = FALLBACK_SUPPORTED_MODELS  # This will be updated dynamically