import os
from dotenv import load_dotenv
import secrets

# Load environment variables from a .env file if it exists.
load_dotenv()

# --- Core API Configuration ---
CORE_API_KEY = os.getenv("CORE_API_KEY")
if not CORE_API_KEY:
    raise ValueError("CORE_API_KEY environment variable not set!")

# --- Database Configuration ---
MONGODB_CONNECTION_STRING = os.getenv("MONGODB_CONNECTION_STRING")
if not MONGODB_CONNECTION_STRING:
    raise ValueError("MONGODB_CONNECTION_STRING environment variable not set!")
MONGODB_DATABASE_NAME = os.getenv("MONGODB_DATABASE_NAME", "ryuukodb")

# --- Security & JWT Configuration ---
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    print("Warning: JWT_SECRET_KEY not set in .env, using a temporary secret. Please set a permanent key for production.")
    JWT_SECRET_KEY = secrets.token_hex(32)

# --- Bot API Key ---
BOT_API_KEY = os.getenv("BOT_API_KEY")
if not BOT_API_KEY:
    print("Warning: BOT_API_KEY not set in .env, using a temporary secret. Please set a permanent key for production.")
    BOT_API_KEY = f"bot_{secrets.token_hex(24)}"

# --- Default Owner Account Configuration ---
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "owner")
OWNER_PASSWORD = os.getenv("OWNER_PASSWORD", "owner")
OWNER_EMAIL = os.getenv("OWNER_EMAIL", "owner@example.com")
OWNER_FIRST_NAME = os.getenv("OWNER_FIRST_NAME", "Owner")
OWNER_LAST_NAME = os.getenv("OWNER_LAST_NAME", "Admin")

# --- Cloudflare Turnstile Configuration ---
CLOUDFLARE_TURNSTILE_SECRET_KEY = os.getenv("CLOUDFLARE_TURNSTILE_SECRET_KEY")
if not CLOUDFLARE_TURNSTILE_SECRET_KEY:
    print("Warning: CLOUDFLARE_TURNSTILE_SECRET_KEY not set. User registration will fail if captcha is enabled on the frontend.")

# --- Provider API Keys (Optional) ---
POLYDEVS_API_KEY = os.getenv("POLYDEVS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("AISTUDIO_API_KEY")
PROXYVN_API_KEY = os.getenv("PROXYVN_API_KEY")
