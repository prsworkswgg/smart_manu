"""Streamlit Community Cloud entrypoint for the portfolio demo."""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def configure_portfolio_environment() -> None:
    """Configure a free-hosting friendly dashboard profile."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    backend_src = ROOT / "backend-python" / "src"
    if backend_src.exists() and str(backend_src) not in sys.path:
        sys.path.insert(0, str(backend_src))

    os.environ.setdefault("SMOP_PORTFOLIO_MODE", "1")
    os.environ.setdefault("SMOP_AUTO_SEED_DEMO", "1")
    os.environ.setdefault("SMOP_DB_PATH", str(ROOT / "data" / "portfolio_demo.db"))


def main() -> None:
    """Seed demo data when needed and launch the dashboard."""
    configure_portfolio_environment()

    from dashboard.app import main as dashboard_main
    from dashboard.portfolio_bootstrap import ensure_portfolio_demo_data

    ensure_portfolio_demo_data(Path(os.environ["SMOP_DB_PATH"]))
    dashboard_main()


if __name__ == "__main__":
    main()
