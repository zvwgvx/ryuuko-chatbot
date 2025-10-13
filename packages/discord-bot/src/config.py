# /packages/discord-bot/src/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file in the parent directory (packages/discord-bot)
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# --- Discord Client --- 
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# --- Core Service --- 
CORE_API_URL = os.getenv("CORE_API_URL", "http://127.0.0.1:8000")
CORE_API_KEY = os.getenv("CORE_API_KEY")
