"""
Direct entry point for Streamlit multipage router: Simulator.
"""

import sys
from pathlib import Path

# Ensure frontend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pages.simulator import render_simulator

render_simulator()
