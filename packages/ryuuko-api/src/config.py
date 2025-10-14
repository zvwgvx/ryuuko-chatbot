import os
from dotenv import load_dotenv
import secrets

# Load environment variables from a .env file if it exists.
load_dotenv()

# --- Core API Configuration ---
# This key is used for general inter-service communication.
CORE_API_KEY = os.getenv("CORE_API_KEY")
if not CORE_API_KEY:
    raise ValueError("CORE_API_KEY environment variable not set!")

# --- Database Configuration ---
# Connection string for the primary MongoDB database.
MONGODB_CONNECTION_STRING = os.getenv("MONGODB_CONNECTION_STRING")
if not MONGODB_CONNECTION_STRING:
    raise ValueError("MONGODB_CONNECTION_STRING environment variable not set!")

MONGODB_DATABASE_NAME = os.getenv("MONGODB_DATABASE_NAME", "ryuukodb")

# --- Provider API Keys ---
# Keys for external AI model providers.
POLYDEVS_API_KEY = os.getenv("POLYDEVS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("AISTUDIO_API_KEY")
PROXYVN_API_KEY = os.getenv("PROXYVN_API_KEY")

# --- NEW: Security & JWT Configuration for Dashboard Auth ---

# A strong, secret key for signing JWT tokens. 
# It's recommended to set this in your .env file. If not, a temporary one is generated.
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    print("Warning: JWT_SECRET_KEY not set in .env, using a temporary secret. Please set a permanent key for production.")
    JWT_SECRET_KEY = secrets.token_hex(32)

# --- NEW: Bot API Key ---

# A dedicated API key for the Discord bot to authenticate with the link/verify endpoint.
# It's recommended to set this in your .env file. If not, a temporary one is generated.
BOT_API_KEY = os.getenv("BOT_API_KEY")
if not BOT_API_KEY:
    print("Warning: BOT_API_KEY not set in .env, using a temporary secret. Please set a permanent key for production.")
    BOT_API_KEY = f"bot_{secrets.token_hex(24)}"
