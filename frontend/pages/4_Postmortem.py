"""Multipage entry point for Post-Mortem Studio — delegates to pages/postmortem.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pages.postmortem import render_postmortem
render_postmortem()
