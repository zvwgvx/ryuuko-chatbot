python -c "from src.config import DISCORD_TOKEN, get_user_config_manager; print('✅ Config imports work')"
python -c "from src.core import setup, call_openai_proxy; print('✅ Core imports work')"
python -c "from src.storage import MongoDBStore, MemoryStore; print('✅ Storage imports work')"
python -c "from src.utils import RateLimiter, get_request_queue; print('✅ Utils imports work')"

python -c "import src; print('✅ Full package imports work')"