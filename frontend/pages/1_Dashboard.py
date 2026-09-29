"""
Direct entry point for Streamlit multipage router: Dashboard.
"""

import sys
from pathlib import Path

# Ensure frontend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pages.dashboard import render_dashboard

render_dashboard()
