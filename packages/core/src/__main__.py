# /packages/core/src/__main__.py
import uvicorn
import os
from pathlib import Path
from dotenv import load_dotenv

# Import the logger setup function
from .utils.logger import setup_logger

def main():
    """Entry point to configure and run the Core Service."""
    
    # --- SỬA LỖI: Tải biến môi trường và thiết lập logger ngay từ đầu ---
    dotenv_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=dotenv_path)
    
    # Setup logging before anything else
    setup_logger()
    # ------------------------------------------------------------------

    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run("core.main:app", host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    main()
