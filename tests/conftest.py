import sys
from pathlib import Path
import os

# Ensure the application package is importable when running tests without installation
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Provide required defaults for settings instantiation during module import
os.environ.setdefault("SECRET_KEY", "test-secret-key")
