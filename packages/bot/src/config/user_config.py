# src/config/user_config.py
"""
Manages user-specific configurations, such as preferred models and system prompts.
This module is refactored to use ryuuko_user_id as the primary identifier.
"""
import logging
from typing import Dict, Any, Optional, Set

logger = logging.getLogger("Config.UserConfig")

# --- Default Configuration Values ---
DEFAULT_SYSTEM_PROMPT = "Your name is Ryuuko (female), and you speak Vietnamese."
DEFAULT_MODEL = "ryuuko-r1-vnm-pro"
FALLBACK_SUPPORTED_MODELS = {
    "gemini-2.5-flash", "gemini-2.5-pro", "gpt-4o-mini", "gpt-3.5-turbo", "ryuuko-r1-vnm-mini"
}

class UserConfigManager:
    """
    Handles all user configuration logic by interacting with the database using ryuuko_user_id.
    """

    def __init__(self):
        """
        Initializes the UserConfigManager and secures a connection to the MongoDB store.
        """
        try:
            from src.storage.database import get_mongodb_store
            self.mongo_store = get_mongodb_store()
            logger.info("UserConfigManager initialized successfully with MongoDB.")
        except Exception as e:
            logger.error("Failed to acquire MongoDB store for UserConfigManager: %s", e)
            raise RuntimeError(f"MongoDB is required for UserConfigManager but is not available: {e}")

    # --- Model Management (no change needed) ---
    def get_supported_models(self) -> Set[str]:
        models = self.mongo_store.get_supported_models()
        return models if models else FALLBACK_SUPPORTED_MODELS

    def list_all_models_detailed(self) -> list:
        return self.mongo_store.list_all_models()

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        return self.mongo_store.get_model_info(model_name)

    # --- User Config Methods (Refactored to use ryuuko_user_id: str) ---

    def get_user_config(self, ryuuko_user_id: str) -> Dict[str, Any]:
        """Retrieves the entire configuration dictionary for a given user."""
        return self.mongo_store.get_user_config(ryuuko_user_id)

    def get_user_model(self, ryuuko_user_id: str) -> str:
        """Gets a user's currently selected model."""
        return self.mongo_store.get_user_model(ryuuko_user_id)

    def get_user_system_prompt(self, ryuuko_user_id: str) -> str:
        """Gets a user's custom system prompt."""
        return self.mongo_store.get_user_system_prompt(ryuuko_user_id)

    def get_user_system_message(self, ryuuko_user_id: str) -> Dict[str, str]:
        """Constructs the system message dictionary for a user."""
        return self.mongo_store.get_user_system_message(ryuuko_user_id)

    def get_user_credit(self, ryuuko_user_id: str) -> int:
        """Retrieves a user's current credit balance."""
        config = self.get_user_config(ryuuko_user_id)
        return config.get("credit", 0)

    def get_user_access_level(self, ryuuko_user_id: str) -> int:
        """Retrieves a user's access level."""
        config = self.get_user_config(ryuuko_user_id)
        return config.get("access_level", 0)

    def set_user_model(self, ryuuko_user_id: str, model: str) -> tuple[bool, str]:
        """Sets the preferred model for a user."""
        if model not in self.get_supported_models():
            return False, f"Model '{model}' is not supported."

        success = self.mongo_store.set_user_config(ryuuko_user_id, model=model)
        return (True, f"Model successfully set to '{model}'.") if success else (False, "Failed to save configuration.")

    def set_user_system_prompt(self, ryuuko_user_id: str, prompt: str) -> tuple[bool, str]:
        """Sets the custom system prompt for a user."""
        if not prompt.strip():
            return False, "System prompt cannot be empty."
        if len(prompt) > 10000:
            return False, "System prompt is too long (max 10,000 characters)."

        success = self.mongo_store.set_user_config(ryuuko_user_id, system_prompt=prompt.strip())
        return (True, "System prompt updated successfully.") if success else (False, "Failed to save configuration.")

    def reset_user_config(self, ryuuko_user_id: str) -> str:
        """Resets a user's configuration to defaults."""
        success = self.mongo_store.set_user_config(
            ryuuko_user_id,
            model=DEFAULT_MODEL,
            system_prompt=DEFAULT_SYSTEM_PROMPT
        )
        return "Configuration has been reset to defaults." if success else "An error occurred."


# --- Singleton Instance ---
_user_config_manager: Optional[UserConfigManager] = None

def get_user_config_manager() -> UserConfigManager:
    """Provides access to the singleton UserConfigManager instance."""
    global _user_config_manager
    if _user_config_manager is None:
        _user_config_manager = UserConfigManager()
    return _user_config_manager