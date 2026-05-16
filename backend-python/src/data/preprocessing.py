"""Preprocessing pipeline: data quality, join, feature engineering, CSV export."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

# Allow direct execution: python backend-python/src/data/preprocessing.py
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database import repository
from data.data_quality import run_data_quality_checks
from features.feature_engineering import add_engineered_features, save_processed_dataset
from features.join_sensor_production import join_sensor_production


def default_output_path() -> Path:
    """Default processed CSV path."""
    return repository.project_root() / "data" / "processed" / "processed_ml_dataset.csv"


def run_preprocessing(
    db_path: str | Path | None = None,
    output_path: str | Path | None = None,
    join_tolerance_minutes: int = 5,
    save_quality_issues: bool = True,
) -> dict[str, Any]:
    """Run the full preprocessing pipeline and save a processed dataset."""
    repository.initialize_database(db_path)

    quality_summary = run_data_quality_checks(db_path=db_path, save_issues=save_quality_issues)
    sensor_df = repository.read_sensor_readings(db_path)
    production_df = repository.read_production_events(db_path)

    joined = join_sensor_production(
        sensor_df=sensor_df,
        production_df=production_df,
        tolerance=f"{join_tolerance_minutes}min",
    )
    processed = add_engineered_features(joined)

    output = Path(output_path) if output_path else default_output_path()
    save_processed_dataset(processed, output)

    return {
        "sensor_rows": int(len(sensor_df)),
        "production_rows": int(len(production_df)),
        "joined_rows": int(len(joined)),
        "processed_rows": int(len(processed)),
        "processed_columns": list(processed.columns),
        "output_path": str(output),
        "quality_summary": quality_summary,
    }


def main() -> None:
    """CLI entrypoint for preprocessing."""
    parser = argparse.ArgumentParser(description="Build processed ML dataset from SQLite.")
    parser.add_argument("--db-path", default=None, help="SQLite database path.")
    parser.add_argument("--output", default=None, help="Output CSV path.")
    parser.add_argument("--join-tolerance-minutes", type=int, default=5, help="Max sensor->production join lag in minutes.")
    parser.add_argument("--no-save-quality-issues", action="store_true", help="Do not insert data quality issues into SQLite.")
    args = parser.parse_args()

    summary = run_preprocessing(
        db_path=args.db_path,
        output_path=args.output,
        join_tolerance_minutes=args.join_tolerance_minutes,
        save_quality_issues=not args.no_save_quality_issues,
    )

    print("Preprocessing complete")
    print(f"sensor_rows: {summary['sensor_rows']}")
    print(f"production_rows: {summary['production_rows']}")
    print(f"joined_rows: {summary['joined_rows']}")
    print(f"processed_rows: {summary['processed_rows']}")
    print(f"output_path: {summary['output_path']}")
    print(f"quality_summary: {summary['quality_summary']}")


if __name__ == "__main__":
    main()
