#!/usr/bin/env bash
# scripts/jev_router.sh
# Convenient Bash CLI wrapper for the JEV Deterministic Micro-Router.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$(command -v python3 || echo "python")"

exec "$PYTHON_BIN" "$SCRIPT_DIR/jev_router.py" "$@"
