import sys
import os

# Add the backend directory to the path so we can import from it
# This allows us to keep the original backend structure
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import app

# Vercel needs the app object to be named 'app'
# Since we import 'app' from main, it is already available as 'app'
