# /packages/core/src/__main__.py
import uvicorn
import os
from pathlib import Path
from dotenv import load_dotenv

def main():
    """Entry point to configure and run the Core Service."""
    
    # --- SỬA LỖI: Tải biến môi trường ngay tại đây, trước khi mọi thứ khác được import ---
    # This ensures that all environment variables are loaded before any other module
    # (like main.py or storage.py) needs them.
    dotenv_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=dotenv_path)
    # ----------------------------------------------------------------------------------

    # Default to port 8000 if not specified in environment
    port = int(os.getenv("PORT", 8000))
    
    # Now, run the uvicorn server. Uvicorn will import `core.main` which will
    # then import `core.config`, and at that point, the environment variables
    # will already be loaded and available.
    uvicorn.run("core.main:app", host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    main()
