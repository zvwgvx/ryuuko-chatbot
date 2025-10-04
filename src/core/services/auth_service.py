# src/core/services/auth_service.py
"""
Handles loading and managing authorized users from storage.
"""
import json
import logging
from pathlib import Path
from typing import Set

logger = logging.getLogger("AuthService")

# This is a module-level state, managed by the setup function.
_authorized_users: Set[int] = set()

def load_authorized_users(config, mongodb_store) -> Set[int]:
    """Loads authorized users from the configured storage backend."""
    global _authorized_users
    if config.USE_MONGODB and mongodb_store:
        _authorized_users = mongodb_store.get_authorized_users()
        logger.info(f"Loaded {len(_authorized_users)} authorized users from MongoDB.")
    else:
        path = config.AUTHORIZED_STORE
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                _authorized_users = set(int(x) for x in data.get("authorized", []))
                logger.info(f"Loaded {len(_authorized_users)} authorized users from {path.name}.")
            except Exception:
                logger.exception(f"Failed to load {path.name}, returning empty set.")
                _authorized_users = set()
        else:
             _authorized_users = set()
    return _authorized_users

def add_authorized_user(user_id: int, config, mongodb_store) -> bool:
    """Adds a user to the authorized list and saves it."""
    global _authorized_users
    _authorized_users.add(user_id)
    if config.USE_MONGODB and mongodb_store:
        return mongodb_store.add_authorized_user(user_id)
    else:
        try:
            path = config.AUTHORIZED_STORE
            path.write_text(json.dumps({"authorized": sorted(list(_authorized_users))}, indent=2), encoding="utf-8")
            return True
        except Exception:
            logger.exception("Failed to save authorized.json")
            return False

def remove_authorized_user(user_id: int, config, mongodb_store) -> bool:
    """Removes a user from the authorized list and saves it."""
    global _authorized_users
    if user_id in _authorized_users:
        _authorized_users.discard(user_id)
        if config.USE_MONGODB and mongodb_store:
            return mongodb_store.remove_authorized_user(user_id)
        else:
            try:
                path = config.AUTHORIZED_STORE
                path.write_text(json.dumps({"authorized": sorted(list(_authorized_users))}, indent=2), encoding="utf-8")
                return True
            except Exception:
                logger.exception("Failed to save authorized.json")
                return False
    return False

def get_authorized_users_set() -> Set[int]:
    """Returns the currently loaded set of authorized users."""
    global _authorized_users
    return _authorized_users