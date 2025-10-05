# src/config/user_config.py
import logging
from typing import Dict, Any, Optional, Set
from src.config import loader  # <-- Dòng này vẫn hoạt động đúng vì loader giờ là một module

logger = logging.getLogger("Config.UserConfig")

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
    """User configuration manager - MongoDB ONLY"""

    def __init__(self):
        # Logic kiểm tra USE_MONGODB đã được chuyển vào loader.py
        # Nếu code chạy đến đây, có nghĩa là MongoDB đã được yêu cầu.
        try:
            from src.storage.database import get_mongodb_store
            self.mongo_store = get_mongodb_store()
            logger.info("UserConfigManager initialized with MongoDB.")
        except Exception as e:
            logger.error("Failed to get MongoDB store: %s", e)
            raise RuntimeError(f"MongoDB is MANDATORY but not available: {e}")

    # ... (Toàn bộ các phương thức còn lại của class UserConfigManager giữ nguyên) ...
    # Vui lòng copy toàn bộ các phương thức từ file user.py cũ của bạn vào đây.
    # Ví dụ:
    def get_supported_models(self) -> Set[str]:
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
        supported_models = self.get_supported_models()
        if model not in supported_models:
            supported_list = ", ".join(sorted(supported_models))
            return False, f"Model '{model}' not supported. Available models: {supported_list}"
        success = self.mongo_store.set_user_config(user_id, model=model)
        return (True, f"Model set to '{model}'") if success else (False, "Error saving configuration to MongoDB")

    def set_user_system_prompt(self, user_id: int, prompt: str) -> tuple[bool, str]:
        if not prompt.strip():
            return False, "System prompt cannot be empty"
        if len(prompt) > 10000:
            return False, "System prompt too long (max 10,000 characters)"
        success = self.mongo_store.set_user_config(user_id, system_prompt=prompt.strip())
        return (True, "System prompt updated") if success else (False, "Error saving configuration to MongoDB")

    def reset_user_config(self, user_id: int) -> str:
        success = self.mongo_store.set_user_config(
            user_id,
            model=DEFAULT_MODEL,
            system_prompt=DEFAULT_SYSTEM_PROMPT
        )
        return "Configuration reset to defaults" if success else "Error resetting configuration in MongoDB"


# Singleton instance
_user_config_manager = None

def get_user_config_manager() -> UserConfigManager:
    """Get UserConfigManager instance (singleton pattern)"""
    global _user_config_manager
    if _user_config_manager is None:
        _user_config_manager = UserConfigManager()
    return _user_config_manager