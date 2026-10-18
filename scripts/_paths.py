"""Puts src/ and every scripts/ folder on sys.path, so scripts import each other by module name."""
import os
import sys

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPTS)
SRC = os.path.join(ROOT, "src")
DOCS = os.path.join(ROOT, "docs")
OUT = os.path.join(SCRIPTS, "out")
PIXSIM_OUT = os.path.join(OUT, "pixsim")
FOLDERS = ("analysis", "feedback", "models", "pixsim", "calibration", "backtest", "fixture")

for path in [SRC, *(os.path.join(SCRIPTS, folder) for folder in FOLDERS)][::-1]:
    if path not in sys.path:
        sys.path.insert(0, path)
