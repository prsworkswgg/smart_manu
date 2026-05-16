#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend-python"
API_FILE="$BACKEND_DIR/api/main.py"

export SMOP_DB_PATH="${SMOP_DB_PATH:-$ROOT_DIR/database/smart_manufacturing.db}"
export SMOP_PROFILE_PATH="${SMOP_PROFILE_PATH:-$ROOT_DIR/configs/precision_electronics_profile.yaml}"
export PYTHONPATH="$BACKEND_DIR/src:$BACKEND_DIR:${PYTHONPATH:-}"

mkdir -p "$ROOT_DIR/database" "$ROOT_DIR/models" "$ROOT_DIR/reports" "$ROOT_DIR/data/processed"

if [[ ! -f "$API_FILE" ]]; then
  echo "FastAPI entrypoint not found: $API_FILE"
  exit 2
fi

cd "$BACKEND_DIR"
exec python -m uvicorn api.main:app --host "${SMOP_API_HOST:-127.0.0.1}" --port "${SMOP_API_PORT:-8000}" --reload
