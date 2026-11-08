"""Compatibility entry point for the portable renderer.

Usage: python engine/render.py video AUDIO DURATION OUTPUT
"""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('render2.py')), run_name='__main__')
