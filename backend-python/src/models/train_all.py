"""Train all ML models for the Smart Manufacturing AI Operations Platform."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from data.preprocessing import default_output_path, run_preprocessing
from models.train_anomaly_model import train_anomaly_model
from models.train_failure_model import train_failure_model
from models.train_rul_model import train_rul_model


def train_all(
    db_path: str | Path | None = None,
    processed_csv: str | Path | None = None,
    rebuild_dataset: bool = True,
) -> dict[str, Any]:
    """Build dataset and train failure, RUL, and anomaly models."""
    output = Path(processed_csv) if processed_csv else default_output_path()

    preprocessing_summary = None
    if rebuild_dataset or not output.exists():
        preprocessing_summary = run_preprocessing(db_path=db_path, output_path=output)

    failure_result = train_failure_model(output, db_path=db_path)
    rul_result = train_rul_model(output, db_path=db_path)
    anomaly_result = train_anomaly_model(output, db_path=db_path)

    return {
        "processed_csv": str(output),
        "preprocessing_summary": preprocessing_summary,
        "failure": failure_result,
        "rul": rul_result,
        "anomaly": anomaly_result,
    }


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Train all models.")
    parser.add_argument("--db-path", default=None, help="SQLite database path.")
    parser.add_argument("--processed-csv", default=None, help="Processed dataset path.")
    parser.add_argument("--no-rebuild-dataset", action="store_true", help="Do not rerun preprocessing if CSV exists.")
    args = parser.parse_args()

    result = train_all(
        db_path=args.db_path,
        processed_csv=args.processed_csv,
        rebuild_dataset=not args.no_rebuild_dataset,
    )
    print("Training complete")
    print(result)


if __name__ == "__main__":
    main()
