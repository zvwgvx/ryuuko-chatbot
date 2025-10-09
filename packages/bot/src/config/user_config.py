# src/config/user_config.py
"""
Manages user-specific configurations...
"""
import logging
from typing import Dict, Any, Optional, Set

logger = logging.getLogger("Config.UserConfig")

# --- Default Configuration Values ---
DEFAULT_SYSTEM_PROMPT = "Your name is Ryuuko (female), and you speak Vietnamese."
DEFAULT_MODEL = "gemini-2.5-flash"
FALLBACK_SUPPORTED_MODELS = {
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gpt-4o-mini",
    "gpt-3.5-turbo",
    "ryuuko-r1-vnm-mini"
}

class UserConfigManager:
    """
    Handles all user configuration logic by interacting with the database.
    ...
    """

    def __init__(self):
        """
        Initializes the UserConfigManager...
        """
        try:
            # Dynamically import to ensure MongoDB is confirmed to be in use.
            # [THAY ĐỔI] Sửa đường dẫn import
            from ..storage.database import get_mongodb_store
            self.mongo_store = get_mongodb_store()
            logger.info("UserConfigManager initialized successfully with MongoDB.")
        except Exception as e:
            logger.error("Failed to acquire MongoDB store for UserConfigManager: %s", e)
            raise RuntimeError(f"MongoDB is required for UserConfigManager but is not available: {e}")

    # ... (phần còn lại của file không thay đổi) ...
    def get_supported_models(self) -> Set[str]:
        """
        Retrieves the set of currently supported models from the database.

        Returns:
            A set of model name strings. Returns a fallback list if the database is empty.
        """
        try:
            models = self.mongo_store.get_supported_models()
            if not models:
                logger.warning("No models found in the database. Using hardcoded fallback list.")
                return FALLBACK_SUPPORTED_MODELS
            return models
        except Exception as e:
            logger.error("Error retrieving supported models from MongoDB: %s", e)
            raise

    def add_supported_model(self, model_name: str, credit_cost: int = 1, access_level: int = 0) -> tuple[bool, str]:
        """Adds a new model to the list of supported models in the database."""
        return self.mongo_store.add_supported_model(model_name, credit_cost, access_level)

    def remove_supported_model(self, model_name: str) -> tuple[bool, str]:
        """Removes a model from the list of supported models in the database."""
        return self.mongo_store.remove_supported_model(model_name)

    def edit_supported_model(self, model_name: str, credit_cost: int = None, access_level: int = None) -> tuple[bool, str]:
        """Edits the attributes of an existing supported model."""
        return self.mongo_store.edit_supported_model(model_name, credit_cost, access_level)

    def list_all_models_detailed(self) -> list:
        """Retrieves a detailed list of all supported models from the database."""
        return self.mongo_store.list_all_models()

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves detailed information for a specific model."""
        return self.mongo_store.get_model_info(model_name)

    def get_user_config(self, user_id: int) -> Dict[str, Any]:
        """Retrieves the entire configuration dictionary for a given user."""
        return self.mongo_store.get_user_config(user_id)

    def get_user_model(self, user_id: int) -> str:
        """Gets a user's currently selected model."""
        return self.mongo_store.get_user_model(user_id)

    def get_user_system_prompt(self, user_id: int) -> str:
        """Gets a user's custom system prompt."""
        return self.mongo_store.get_user_system_prompt(user_id)

    def get_user_system_message(self, user_id: int) -> Dict[str, str]:
        """Constructs the system message dictionary for a user."""
        return self.mongo_store.get_user_system_message(user_id)

    def get_user_credit(self, user_id: int) -> int:
        """Retrieves a user's current credit balance."""
        config = self.get_user_config(user_id)
        return config.get("credit", 0)

    def get_user_access_level(self, user_id: int) -> int:
        """Retrieves a user's access level."""
        config = self.get_user_config(user_id)
        return config.get("access_level", 0)

    def set_user_model(self, user_id: int, model: str) -> tuple[bool, str]:
        """
        Sets the preferred model for a user after validating it against the supported list.
        """
        supported_models = self.get_supported_models()
        if model not in supported_models:
            supported_list = ", ".join(sorted(supported_models))
            return False, f"Model '{model}' is not supported. Available models: {supported_list}"

        success = self.mongo_store.set_user_config(user_id, model=model)
        return (True, f"Model successfully set to '{model}'.") if success else (False, "Failed to save configuration to the database.")

    def set_user_system_prompt(self, user_id: int, prompt: str) -> tuple[bool, str]:
        """
        Sets the custom system prompt for a user after basic validation.
        """
        if not prompt.strip():
            return False, "System prompt cannot be empty."
        if len(prompt) > 10000:
            return False, "System prompt is too long (max 10,000 characters)."

        success = self.mongo_store.set_user_config(user_id, system_prompt=prompt.strip())
        return (True, "System prompt updated successfully.") if success else (False, "Failed to save configuration to the database.")

    def reset_user_config(self, user_id: int) -> str:
        """
        Resets a user's configuration to the default model and system prompt.
        """
        success = self.mongo_store.set_user_config(
            user_id,
            model=DEFAULT_MODEL,
            system_prompt=DEFAULT_SYSTEM_PROMPT
        )
        return "Configuration has been reset to defaults." if success else "An error occurred while resetting the configuration."

# --- Singleton Instance ---
_user_config_manager: Optional[UserConfigManager] = None

def get_user_config_manager() -> UserConfigManager:
    """
    Provides access to the singleton UserConfigManager instance.
    ...
    """
    global _user_config_manager
    if _user_config_manager is None:
        _user_config_manager = UserConfigManager()
    return _user_config_manager