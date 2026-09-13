#!/usr/bin/env bash
# scripts/verify.sh
# Verification and test suite for the Gemini Advisor plugin.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==> Verifying Gemini Advisor Plugin at: $REPO_ROOT"
ERRORS=0

# 1. Verify JSON manifests
echo "1. Checking JSON manifests..."
for json_file in "$REPO_ROOT/plugin.json" "$REPO_ROOT/plugins/gemini-advisor/plugin.json"; do
    if [ -f "$json_file" ]; then
        if python3 -m json.tool "$json_file" > /dev/null 2>&1; then
            echo "  ✓ Valid JSON: ${json_file#$REPO_ROOT/}"
        else
            echo "  ✗ INVALID JSON: ${json_file#$REPO_ROOT/}"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo "  ✗ Missing JSON file: ${json_file#$REPO_ROOT/}"
        ERRORS=$((ERRORS + 1))
    fi
done

# 2. Verify Skill and Frontmatter
echo "2. Checking skills and frontmatter..."
SKILL_FILE="$REPO_ROOT/skills/gemini-advisor/SKILL.md"
if [ -f "$SKILL_FILE" ]; then
    if grep -q "^name: gemini-advisor" "$SKILL_FILE" && grep -q "^description:" "$SKILL_FILE"; then
        echo "  ✓ Valid frontmatter in skills/gemini-advisor/SKILL.md"
    else
        echo "  ✗ Missing required YAML frontmatter fields in skills/gemini-advisor/SKILL.md"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "  ✗ Missing skills/gemini-advisor/SKILL.md"
    ERRORS=$((ERRORS + 1))
fi

# 3. Verify References
echo "3. Checking documentation references..."
REQUIRED_REFS=(
    "skills/gemini-advisor/references/role_contracts.md"
    "skills/gemini-advisor/references/routing_matrix.md"
    "skills/gemini-advisor/references/review_protocol.md"
    "skills/gemini-advisor/references/token_optimization.md"
    "rules/AGENTS.md"
    "rules/GEMINI.md"
    "README.md"
    "LICENSE"
)

for ref in "${REQUIRED_REFS[@]}"; do
    if [ -f "$REPO_ROOT/$ref" ]; then
        echo "  ✓ Exists: $ref"
    else
        echo "  ✗ Missing reference file: $ref"
        ERRORS=$((ERRORS + 1))
    fi
done

# 4. Verify Shell Scripts syntax and executability
echo "4. Checking shell scripts syntax..."
SCRIPTS=(
    "scripts/diff_summary.sh"
    "scripts/install.sh"
    "scripts/verify.sh"
)

for scr in "${SCRIPTS[@]}"; do
    if [ -f "$REPO_ROOT/$scr" ]; then
        if bash -n "$REPO_ROOT/$scr"; then
            echo "  ✓ Bash syntax clean: $scr"
        else
            echo "  ✗ Bash syntax errors in $scr"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo "  ✗ Missing script: $scr"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""
if [ "$ERRORS" -eq 0 ]; then
    echo "==> ALL CHECKS PASSED! Gemini Advisor plugin is healthy."
    exit 0
else
    echo "==> FAILED with $ERRORS error(s)."
    exit 1
fi
