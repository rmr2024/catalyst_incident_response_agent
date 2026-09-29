"""Multipage entry point for Operational Analytics — delegates to pages/analytics.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pages.analytics import render_analytics
render_analytics()
