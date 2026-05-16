#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend-python"
TRAIN_FILE="$BACKEND_DIR/src/models/train_all.py"

export SMOP_DB_PATH="${SMOP_DB_PATH:-$ROOT_DIR/database/smart_manufacturing.db}"
export SMOP_PROFILE_PATH="${SMOP_PROFILE_PATH:-$ROOT_DIR/configs/precision_electronics_profile.yaml}"
export SMOP_MODEL_DIR="${SMOP_MODEL_DIR:-$ROOT_DIR/models}"
export PYTHONPATH="$BACKEND_DIR/src:$BACKEND_DIR:${PYTHONPATH:-}"

mkdir -p "$ROOT_DIR/models" "$ROOT_DIR/reports" "$ROOT_DIR/data/processed"

exec python "$TRAIN_FILE" "$@"
