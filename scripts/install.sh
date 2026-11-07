#!/usr/bin/env bash
# scripts/install.sh
# Installs or links the Gemini Advisor plugin into Antigravity discovery paths.
#
# Usage:
#   sh scripts/install.sh [--global | --workspace] [--check]
#
# Options:
#   --global     Install to ~/.gemini/config/plugins/gemini-advisor (Default)
#   --workspace  Install to current workspace at .agents/plugins/gemini-advisor
#   --check      Verify installation without making changes

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

TARGET_SCOPE="global"
CHECK_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --global)
            TARGET_SCOPE="global"
            ;;
        --workspace)
            TARGET_SCOPE="workspace"
            ;;
        --check)
            CHECK_ONLY=true
            ;;
        -h|--help)
            echo "Usage: $0 [--global | --workspace] [--check]"
            echo ""
            echo "Options:"
            echo "  --global     Install to ~/.gemini/config/plugins/gemini-advisor (Default)"
            echo "  --workspace  Install to .agents/plugins/gemini-advisor in current workspace"
            echo "  --check      Verify installation without making any changes"
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Run '$0 --help' for usage."
            exit 1
            ;;
    esac
done

if [ "$TARGET_SCOPE" = "global" ]; then
    INSTALL_DIR="${HOME}/.gemini/config/plugins/gemini-advisor"
else
    INSTALL_DIR="${REPO_ROOT}/.agents/plugins/gemini-advisor"
fi

echo "==> Gemini Advisor Plugin Installer"
echo "    Source: $REPO_ROOT"
echo "    Target: $INSTALL_DIR (Scope: $TARGET_SCOPE)"
echo ""

if [ "$CHECK_ONLY" = true ]; then
    echo "Running preflight check..."
    if [ -d "$INSTALL_DIR" ] || [ -L "$INSTALL_DIR" ]; then
        if [ -f "$INSTALL_DIR/plugin.json" ] && [ -f "$INSTALL_DIR/skills/gemini-advisor/SKILL.md" ]; then
            echo "✓ Installation verified: Plugin is properly linked and valid at $INSTALL_DIR"
            echo ""
            echo "Checking active model allocation:"
            bash "$REPO_ROOT/scripts/model_allocator.sh" --check
            exit 0
        else
            echo "✗ Warning: Directory exists at $INSTALL_DIR, but required files are missing."
            exit 1
        fi
    else
        echo "✗ Not installed: Target path $INSTALL_DIR does not exist."
        exit 1
    fi
fi

# Ensure parent directory exists
PARENT_DIR="$(dirname "$INSTALL_DIR")"
mkdir -p "$PARENT_DIR"

# If destination exists and is already a symlink to this repo, report success
if [ -L "$INSTALL_DIR" ]; then
    CURRENT_LINK="$(readlink "$INSTALL_DIR")"
    if [ "$CURRENT_LINK" = "$REPO_ROOT" ]; then
        echo "✓ Already installed: $INSTALL_DIR is already linked to $REPO_ROOT"
        echo ""
        echo "Checking active model allocation:"
        bash "$REPO_ROOT/scripts/model_allocator.sh" --check
        exit 0
    else
        echo "Updating existing symlink from $CURRENT_LINK to $REPO_ROOT..."
        rm "$INSTALL_DIR"
    fi
elif [ -d "$INSTALL_DIR" ]; then
    echo "Warning: Existing non-symlink directory found at $INSTALL_DIR"
    echo "Backing up to ${INSTALL_DIR}.bak-$(date +%s)..."
    mv "$INSTALL_DIR" "${INSTALL_DIR}.bak-$(date +%s)"
fi

echo "Creating symlink to plugin..."
ln -s "$REPO_ROOT" "$INSTALL_DIR"

echo "Verifying installation..."
if [ -f "$INSTALL_DIR/plugin.json" ] && [ -f "$INSTALL_DIR/skills/gemini-advisor/SKILL.md" ]; then
    echo ""
    echo "✓ Success! Gemini Advisor is installed at:"
    echo "  $INSTALL_DIR"
    echo ""
    echo "Antigravity will now automatically discover the 'gemini-advisor' skill and rules."
    echo ""
    echo "Checking active model allocation:"
    bash "$REPO_ROOT/scripts/model_allocator.sh" --check
else
    echo "✗ Error: Installation failed to verify target files."
    exit 1
fi
