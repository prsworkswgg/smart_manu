#!/usr/bin/env python3
"""Capture Streamlit dashboard screenshots when Playwright is available.

This script does not create fake screenshots. If Playwright/browser support is
not available, it writes clear manual capture instructions.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PAGES = [
    ("Executive Overview", "01_executive_overview.png"),
    ("Data Acquisition Status", "02_data_acquisition.png"),
    ("Line Monitoring", "03_line_monitoring.png"),
    ("Equipment Health", "04_equipment_health.png"),
    ("Process Anomaly", "05_anomaly_detection.png"),
    ("Data Quality", "06_data_quality.png"),
    ("Model Training & Registry", "07_model_registry.png"),
    ("Reports / Edge Deployment", "08_reports.png"),
]


def write_manual(out_dir: Path, url: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    manual = out_dir / "MANUAL_SCREENSHOT_INSTRUCTIONS.md"
    manual.write_text(
        "# Manual Dashboard Screenshot Instructions\n\n"
        "Automated capture requires Playwright and a running Streamlit dashboard.\n\n"
        f"1. Run `bash scripts/run_full_demo.sh` to seed demo data.\n"
        f"2. Run `bash scripts/run_dashboard.sh`.\n"
        f"3. Open `{url}`.\n"
        "4. Capture each sidebar page and save as:\n\n"
        + "\n".join(f"- `{name}` -> `{filename}`" for name, filename in PAGES)
        + "\n\nDo not use fake screenshots. Images must come from the real dashboard.\n",
        encoding="utf-8",
    )
    print(f"Manual instructions written: {manual}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8501")
    parser.add_argument("--output-dir", default="assets/screenshots")
    args = parser.parse_args()
    out_dir = Path(args.output_dir)

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        print(f"SKIPPED: Playwright unavailable ({exc}).")
        write_manual(out_dir, args.url)
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.goto(args.url, wait_until="networkidle", timeout=30000)
            for page_name, file_name in PAGES:
                try:
                    page.get_by_text(page_name, exact=True).click(timeout=4000)
                    page.wait_for_timeout(1200)
                except Exception:
                    pass
                page.screenshot(path=str(out_dir / file_name), full_page=True)
                print(f"captured: {out_dir / file_name}")
            browser.close()
    except Exception as exc:
        print(f"SKIPPED: automated screenshot capture failed ({exc}).")
        write_manual(out_dir, args.url)


if __name__ == "__main__":
    main()
