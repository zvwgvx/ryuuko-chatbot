# /packages/ryuuko-api/src/database.py

from . import config
from .storage import MongoDBStore

# Initialize the database store with the connection string from the config.
# This single instance will be imported and shared across the application.
db_store = MongoDBStore(config.MONGODB_CONNECTION_STRING, config.MONGODB_DATABASE_NAME)
