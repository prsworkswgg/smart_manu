"""Data Quality Engine for the Smart Manufacturing AI Operations Platform."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

# Allow direct execution: python backend-python/src/data/data_quality.py
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database import repository
from data.validator import QualityIssue, validate_production_events, validate_sensor_readings


def run_data_quality_checks(db_path: str | Path | None = None, save_issues: bool = True) -> dict[str, Any]:
    """Read SQLite tables, run validation rules, optionally persist issues."""
    repository.initialize_database(db_path)

    sensor_df = repository.read_sensor_readings(db_path)
    production_df = repository.read_production_events(db_path)

    issues: list[QualityIssue] = []
    issues.extend(validate_sensor_readings(sensor_df))
    issues.extend(validate_production_events(production_df))

    inserted = 0
    if save_issues and issues:
        inserted = repository.insert_data_quality_issues([issue.to_db_dict() for issue in issues], db_path)

    summary = {
        "sensor_rows": int(len(sensor_df)),
        "production_rows": int(len(production_df)),
        "issue_count": int(len(issues)),
        "issues_inserted": int(inserted),
        "issue_type_counts": {},
    }

    for issue in issues:
        summary["issue_type_counts"][issue.issue_type] = summary["issue_type_counts"].get(issue.issue_type, 0) + 1

    return summary


def main() -> None:
    """CLI entrypoint for running the data quality engine."""
    parser = argparse.ArgumentParser(description="Run data quality checks against SQLite.")
    parser.add_argument("--db-path", default=None, help="SQLite database path. Defaults to SMOP_DB_PATH or database/smart_manufacturing.db.")
    parser.add_argument("--no-save", action="store_true", help="Run checks without inserting issues into data_quality_issues.")
    args = parser.parse_args()

    summary = run_data_quality_checks(db_path=args.db_path, save_issues=not args.no_save)
    print("Data quality summary")
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
