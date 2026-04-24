#!/usr/bin/env python3
"""
run_notebooks.py — Execute, clean, and export all SchemaGuard notebooks.

Usage:
    python3 scripts/run_notebooks.py

Actions per notebook:
  1. Execute in-place with nbconvert (timeout 300s per cell)
  2. Clear execution counts -> reset to sequential 1..N
  3. Strip noisy stderr outputs (logging warnings, deprecation notices)
  4. Copy plot images to outputs/plots/
  5. Save notebook in-place
"""

import json, sys, os, shutil, logging, subprocess, re
from pathlib import Path
from datetime import datetime

ROOT     = Path(__file__).parent.parent
NB_DIR   = ROOT / 'notebooks'
PLOT_OUT = ROOT / 'outputs' / 'plots'
PLOT_OUT.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(levelname)s  %(message)s')
log = logging.getLogger(__name__)
