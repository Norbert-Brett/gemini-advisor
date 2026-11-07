#!/usr/bin/env bash
# scripts/model_allocator.sh
# Dynamic Model Discovery, Check & Tier Allocation Engine wrapper for Gemini Advisor.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXEC="python3"

exec "$PYTHON_EXEC" "$SCRIPT_DIR/model_allocator.py" "$@"
