"""
Storage package for Ryuuko Chatbot
Provides database and memory management functionality
"""

# Import from database.py
from .database import (
    # Main class
    MongoDBStore,

    # Singleton functions
    get_mongodb_store,
    init_mongodb_store,
    close_mongodb_store,
)

# Import from memory.py
from .memory import (
    # Main class
    MemoryStore,

    # Type definitions
    Msg,
)

__all__ = [
    # Database management
    'MongoDBStore',
    'get_mongodb_store',
    'init_mongodb_store',
    'close_mongodb_store',

    # Memory management
    'MemoryStore',
    'Msg',
]