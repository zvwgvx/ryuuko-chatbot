# /packages/core/src/config.py
import os

# This file now acts as a clean accessor for environment variables,
# which are loaded by the application's entry point (__main__.py).

# --- Core Service ---
CORE_API_KEY = os.getenv("CORE_API_KEY")

# --- Database ---
MONGODB_CONNECTION_STRING = os.getenv("MONGODB_CONNECTION_STRING")
MONGODB_DATABASE_NAME = "polydevsdb"

# --- LLM API Keys ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
POLYDEVS_API_KEY = os.getenv("POLYDEVS_API_KEY")
PROXYVN_API_KEY = os.getenv("PROXYVN_API_KEY")
