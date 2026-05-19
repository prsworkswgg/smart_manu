"""Portfolio deployment bootstrap helpers for the Streamlit dashboard."""

from __future__ import annotations

import argparse
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def has_dashboard_rows(db_path: Path) -> bool:
    """Return True when the dashboard database already has core demo rows."""
    if not db_path.exists():
        return False
    try:
        with sqlite3.connect(db_path) as conn:
            sensor_count = conn.execute("SELECT COUNT(*) FROM sensor_readings").fetchone()[0]
            production_count = conn.execute("SELECT COUNT(*) FROM production_events").fetchone()[0]
        return sensor_count > 0 and production_count > 0
    except sqlite3.Error:
        return False


def _load_generator() -> Any:
    generator_path = ROOT / "scripts" / "generate_synthetic_factory_data.py"
    spec = importlib.util.spec_from_file_location("smop_synthetic_generator", generator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load synthetic data generator: {generator_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def ensure_portfolio_demo_data(db_path: Path | None = None, *, force: bool = False) -> dict[str, Any]:
    """Seed a small synthetic demo database for free portfolio hosting.

    The function is intentionally opt-in through ``SMOP_AUTO_SEED_DEMO`` unless
    ``force`` is passed. Local development keeps using the explicit demo scripts.
    """
    enabled = os.environ.get("SMOP_AUTO_SEED_DEMO", "").lower() in {"1", "true", "yes"}
    if not enabled and not force:
        return {"seeded": False, "reason": "disabled"}

    target_db = db_path or Path(os.environ.get("SMOP_DB_PATH", ROOT / "data" / "portfolio_demo.db"))
    target_db = target_db.resolve()
    if has_dashboard_rows(target_db) and not force:
        return {"seeded": False, "reason": "already_seeded", "db_path": str(target_db)}

    target_db.parent.mkdir(parents=True, exist_ok=True)
    generator = _load_generator()
    args = argparse.Namespace(
        start_date=os.environ.get("SMOP_PORTFOLIO_START_DATE", "2026-05-01T06:00:00"),
        hours=int(os.environ.get("SMOP_PORTFOLIO_HOURS", "96")),
        interval_minutes=int(os.environ.get("SMOP_PORTFOLIO_INTERVAL_MINUTES", "10")),
        machines_per_line=int(os.environ.get("SMOP_PORTFOLIO_MACHINES_PER_LINE", "4")),
        lines=int(os.environ.get("SMOP_PORTFOLIO_LINES", "3")),
        profile=os.environ.get("SMOP_PORTFOLIO_PROFILE", "high_load_stress"),
        seed=int(os.environ.get("SMOP_PORTFOLIO_SEED", "42")),
        output_db=str(target_db),
        output_csv_dir=None,
        reset=True,
    )
    summary = generator.generate(args)
    return {"seeded": True, "db_path": str(target_db), **summary}
