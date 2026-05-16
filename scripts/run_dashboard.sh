#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DASHBOARD_FILE="$ROOT_DIR/dashboard/app.py"
BACKEND_DIR="$ROOT_DIR/backend-python"

export SMOP_DB_PATH="${SMOP_DB_PATH:-$ROOT_DIR/database/smart_manufacturing.db}"
export SMOP_API_BASE_URL="${SMOP_API_BASE_URL:-http://127.0.0.1:8000}"
export SMOP_PROFILE_PATH="${SMOP_PROFILE_PATH:-$ROOT_DIR/configs/precision_electronics_profile.yaml}"
export PYTHONPATH="$BACKEND_DIR/src:$BACKEND_DIR:${PYTHONPATH:-}"

mkdir -p "$ROOT_DIR/reports" "$ROOT_DIR/assets/screenshots"

exec python -m streamlit run "$DASHBOARD_FILE" --server.address "${SMOP_DASHBOARD_HOST:-127.0.0.1}" --server.port "${SMOP_DASHBOARD_PORT:-8501}"
