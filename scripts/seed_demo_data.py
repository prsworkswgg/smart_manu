#!/usr/bin/env python3
"""Seed demo SQLite data for dashboard development."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cmd = [
    sys.executable, str(ROOT / "scripts" / "generate_synthetic_factory_data.py"),
    "--start-date", "2026-05-01T06:00:00",
    "--hours", "72",
    "--interval-minutes", "10",
    "--lines", "3",
    "--machines-per-line", "4",
    "--profile", "high_load_stress",
    "--seed", "42",
    "--output-db", "data/demo_smart_factory.db",
    "--output-csv-dir", "data/generated",
    "--reset",
]
raise SystemExit(subprocess.call(cmd, cwd=ROOT))
