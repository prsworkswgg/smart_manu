#!/usr/bin/env python3
"""Capture Streamlit dashboard screenshots for visual regression review.

This script does not create fake screenshots. If Playwright/browser support is
not available, it writes clear manual capture instructions.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PAGES = [
    ("Command center", "01_command_center.png"),
    ("Operations workflow", "02_operations_workflow.png"),
    ("Data collection", "03_data_collection.png"),
    ("Line monitoring", "04_line_monitoring.png"),
    ("Machine investigation", "05_machine_investigation.png"),
    ("Anomaly investigation", "06_anomaly_investigation.png"),
    ("Data quality", "07_data_quality.png"),
    ("Model training", "08_model_training.png"),
    ("Reports and edge setup", "09_reports_edge_setup.png"),
]

VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1100},
    "mobile": {"width": 390, "height": 844},
}


def write_manual(out_dir: Path, url: str, viewports: list[str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    manual = out_dir / "MANUAL_SCREENSHOT_INSTRUCTIONS.md"
    manual.write_text(
        "# Manual Dashboard Screenshot Instructions\n\n"
        "Automated capture requires Playwright and a running Streamlit dashboard.\n\n"
        f"1. Run `bash scripts/run_full_demo.sh` to seed demo data.\n"
        f"2. Run `bash scripts/run_dashboard.sh`.\n"
        f"3. Open `{url}`.\n"
        "4. Capture each sidebar page at each viewport and save as:\n\n"
        + "\n".join(
            f"- `{viewport}` / `{name}` -> `{viewport}/{filename}`"
            for viewport in viewports
            for name, filename in PAGES
        )
        + "\n\nDo not use fake screenshots. Images must come from the real dashboard.\n",
        encoding="utf-8",
    )
    print(f"Manual instructions written: {manual}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8501")
    parser.add_argument("--output-dir", default="assets/screenshots")
    parser.add_argument("--viewports", default="desktop,mobile", help="Comma-separated viewport names: desktop,mobile")
    args = parser.parse_args()
    out_dir = Path(args.output_dir)
    selected_viewports = [name.strip() for name in args.viewports.split(",") if name.strip()]
    unknown = [name for name in selected_viewports if name not in VIEWPORTS]
    if unknown:
        raise SystemExit(f"Unknown viewport(s): {', '.join(unknown)}")

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        print(f"SKIPPED: Playwright unavailable ({exc}).")
        write_manual(out_dir, args.url, selected_viewports)
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for viewport_name in selected_viewports:
                viewport_dir = out_dir / viewport_name
                viewport_dir.mkdir(parents=True, exist_ok=True)
                page = browser.new_page(viewport=VIEWPORTS[viewport_name])
                page.goto(args.url, wait_until="networkidle", timeout=30000)
                for page_name, file_name in PAGES:
                    try:
                        page.get_by_text(page_name, exact=True).click(timeout=4000)
                        page.wait_for_timeout(1200)
                    except Exception:
                        pass
                    path = viewport_dir / file_name
                    page.screenshot(path=str(path), full_page=True)
                    print(f"captured: {path}")
                page.close()
            browser.close()
    except Exception as exc:
        print(f"SKIPPED: automated screenshot capture failed ({exc}).")
        write_manual(out_dir, args.url, selected_viewports)


if __name__ == "__main__":
    main()
