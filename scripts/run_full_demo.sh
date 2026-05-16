#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DB_PATH="${SMOP_DEMO_DB_PATH:-data/demo_smart_factory.db}"
PROCESSED_CSV="${SMOP_DEMO_PROCESSED_CSV:-data/processed/demo_processed_ml_dataset.csv}"
MODEL_DIR="${SMOP_MODEL_DIR:-models}"
CSV_DIR="${SMOP_DEMO_CSV_DIR:-data/generated}"

export SMOP_DB_PATH="$DB_PATH"
export DATABASE_PATH="$DB_PATH"
export SMOP_MODEL_DIR="$MODEL_DIR"
export ARTIFACTS_DIR="$MODEL_DIR"
export PYTHONPATH="$ROOT_DIR/backend-python/src:$ROOT_DIR/backend-python:${PYTHONPATH:-}"

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; exit 1; }
skip() { echo "SKIPPED: $1"; }

python - <<'PY' || fail "Python version check failed"
import sys
assert sys.version_info >= (3, 10), sys.version
print(f"Python {sys.version.split()[0]}")
PY
pass "Python version supported"

python - <<'PY' || fail "required Python core package check failed"
import fastapi, pandas, numpy, sklearn, joblib
print("core packages import OK")
try:
    import streamlit  # noqa: F401
    print("streamlit import OK")
except Exception as exc:
    print(f"SKIPPED: Streamlit package not importable in this environment ({exc}). Dashboard data validation continues.")
PY
pass "required Python core packages available"

if command -v dotnet >/dev/null 2>&1; then
  (cd acquisition-csharp/SensorCollector && dotnet restore && dotnet build --no-restore) && pass ".NET restore/build succeeded" || fail ".NET restore/build failed"
else
  skip ".NET SDK not found. Python demo continues."
fi

rm -f "$DB_PATH"
mkdir -p data/processed "$CSV_DIR" "$MODEL_DIR" reports
python scripts/generate_synthetic_factory_data.py \
  --start-date 2026-05-01T06:00:00 \
  --hours "${SMOP_DEMO_HOURS:-24}" \
  --interval-minutes "${SMOP_DEMO_INTERVAL_MINUTES:-10}" \
  --lines "${SMOP_DEMO_LINES:-2}" \
  --machines-per-line "${SMOP_DEMO_MACHINES_PER_LINE:-3}" \
  --profile "${SMOP_DEMO_PROFILE:-high_load_stress}" \
  --seed "${SMOP_DEMO_SEED:-42}" \
  --output-db "$DB_PATH" \
  --output-csv-dir "$CSV_DIR" \
  --reset || fail "synthetic factory data generation failed"
pass "synthetic factory data generated"

python backend-python/src/data/preprocessing.py --db-path "$DB_PATH" --output "$PROCESSED_CSV" --join-tolerance-minutes 30 || fail "preprocessing failed"
pass "preprocessing completed"
pass "feature engineering completed"

python - <<'PY' || fail "leakage checks failed"
from features.feature_engineering import FEATURE_COLUMNS, assert_no_leakage
assert_no_leakage(FEATURE_COLUMNS)
print("feature leakage checks OK")
PY
pass "leakage checks passed"

python backend-python/src/models/train_all.py --db-path "$DB_PATH" --processed-csv "$PROCESSED_CSV" --no-rebuild-dataset || fail "model training failed"
pass "models trained"

python scripts/validate_demo_outputs.py --db-path "$DB_PATH" --processed-csv "$PROCESSED_CSV" --model-dir "$MODEL_DIR" || fail "demo output validation failed"
pass "prediction executed"
pass "dashboard data available"
pass "reports generated"

echo "PASS: full demo complete"
echo "See DEMO_VALIDATION.md and reports/demo_report.md"
