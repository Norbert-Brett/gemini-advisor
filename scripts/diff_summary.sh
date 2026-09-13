#!/usr/bin/env bash
# scripts/diff_summary.sh
# Generates a compact, token-efficient git diff and status report
# for feeding to the Gemini Advisor Reviewer.

set -euo pipefail

MAX_DIFF_LINES=${MAX_DIFF_LINES:-300}
TARGET_PATH="${1:-.}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "=== DIRECTORY STATUS ==="
    echo "(Not inside a git repository. Listing files in $TARGET_PATH:)"
    find "$TARGET_PATH" -maxdepth 2 -not -path '*/.*'
    exit 0
fi

echo "=== GIT STATUS ==="
git status --short "$TARGET_PATH" || true
echo ""

echo "=== CHANGED FILES (STAT) ==="
git diff --stat "$TARGET_PATH" || true
echo ""

echo "=== UNIFIED DIFF (UP TO $MAX_DIFF_LINES LINES) ==="
DIFF_OUTPUT=$(git diff -U3 "$TARGET_PATH" 2>/dev/null || true)

if [ -z "$DIFF_OUTPUT" ]; then
    # Check if there are staged files
    STAGED_DIFF=$(git diff --cached -U3 "$TARGET_PATH" 2>/dev/null || true)
    if [ -n "$STAGED_DIFF" ]; then
        echo "$STAGED_DIFF" | head -n "$MAX_DIFF_LINES"
    else
        echo "(No uncommitted git changes detected in $TARGET_PATH)"
    fi
else
    TOTAL_LINES=$(echo "$DIFF_OUTPUT" | wc -l | tr -d ' ')
    echo "$DIFF_OUTPUT" | head -n "$MAX_DIFF_LINES"
    if [ "$TOTAL_LINES" -gt "$MAX_DIFF_LINES" ]; then
        echo ""
        echo "... [Diff truncated at $MAX_DIFF_LINES lines. Total lines: $TOTAL_LINES. To inspect full diff, run git diff] ..."
    fi
fi
