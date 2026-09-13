#!/usr/bin/env bash
# scripts/token_counter.sh
# Convenient wrapper around token_counter.py

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXEC="python3"

exec "$PYTHON_EXEC" "$SCRIPT_DIR/token_counter.py" "$@"
