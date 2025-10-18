# /packages/telegram-bot/src/config.py
import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# --- Bot Configuration ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")

# --- Core API Configuration ---
CORE_API_URL = os.getenv("CORE_API_URL", "http://127.0.0.1:8000")
CORE_API_KEY = os.getenv("CORE_API_KEY")
