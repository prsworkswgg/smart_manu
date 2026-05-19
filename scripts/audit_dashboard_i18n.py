#!/usr/bin/env python3
"""Audit dashboard translation strings for unexpected English tokens."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


def load_dashboard_app(root: Path):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location("dashboard_app", root / "dashboard" / "app.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", default="th")
    parser.add_argument("--max-findings", type=int, default=30)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    app = load_dashboard_app(root)
    findings = app.audit_language_strings(app.TEXT, args.lang)
    if findings:
        print(f"FAIL: {len(findings)} {args.lang} strings contain unexpected English-looking tokens.")
        for key, tokens in findings[: args.max_findings]:
            print(f"- {key}: {', '.join(tokens)}")
        return 1
    print(f"PASS: dashboard {args.lang} strings passed the i18n audit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
