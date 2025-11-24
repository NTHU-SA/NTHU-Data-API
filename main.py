"""
Application entry point - delegates to new structure.

Run with: python main.py
Or use: python -m data_api.api.main
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import and run from new structure
if __name__ == "__main__":
    from data_api.api import main

    # Entry point is in data_api.api.main module
