#!/usr/bin/env python3
"""
Ryuuko Discord Bot - Entry Point
"""

import sys
import os

# Add src to path if needed
current_dir = os.path.dirname(__file__)
src_path = os.path.join(current_dir, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if __name__ == "__main__":
    from src.core.bot import main
    main()