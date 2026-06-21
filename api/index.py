import os
import sys

# Add backend directory to sys.path so that 'app' can be found
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Import the FastAPI app instance from backend/app/main.py
from app.main import app
