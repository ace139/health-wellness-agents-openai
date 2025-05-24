#!/usr/bin/env python3
"""Initialize the database with sample data."""
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.db.init_db import main  # noqa: E402

if __name__ == "__main__":
    print("Initializing database with sample data...")
    main()
    print("✅ Database initialization complete!")
