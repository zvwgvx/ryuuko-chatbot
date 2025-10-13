# /packages/ryuuko-api/src/runner.py
import uvicorn
import os
from pathlib import Path
from dotenv import load_dotenv

from .utils.logger import setup_logger

def main():
    """The main entry point for running the Uvicorn server."""
    # 1. Setup logging first
    setup_logger()

    # 2. Load environment variables from the .env file
    dotenv_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=dotenv_path)

    # 3. Get port from environment or use a default
    port = int(os.getenv("PORT", 8000))

    # 4. Run the Uvicorn server
    # We now point to the factory function, which is more robust for reloading.
    uvicorn.run("ryuuko_api.main:app", host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    main()
