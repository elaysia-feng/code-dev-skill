#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Pre-commit check: scan staged Java/Python files for unwanted abstractions.
#
# This runs check-abstraction-smell.py against the project root and blocks
# the commit if new abstraction smells are detected (warning level only).
#
# Install:
#   cp scripts/pre-commit-check.sh .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit
#
# Or use with your existing pre-commit framework (husky, pre-commit, etc.)
# ---------------------------------------------------------------------------

set -euo pipefail

# Compute PROJECT_ROOT once at the top (reused throughout)
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

# Resolve the skill directory: try BASH_SOURCE first, then search from repo root.
# BASH_SOURCE works when the script is bash-run from its original location;
# after "cp" into .git/hooks/ or when invoked via sh, we fall back to searching.
if [ -n "${BASH_SOURCE[0]:-}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    SKILL_DIR="$(dirname "$SCRIPT_DIR")"
    CHECKER="$SKILL_DIR/scripts/check-abstraction-smell.py"
else
    CHECKER=""
fi

if [ ! -f "$CHECKER" ]; then
    # Fallback: search from repo root for the skill directory.
    # Look for the checker relative to common install locations.
    # When installed as a git hook, BASH_SOURCE resolves to .git/hooks/,
    # so the primary path is the new top-level location.
    for candidate in \
        "$PROJECT_ROOT/skills/readability-first-coding/scripts/check-abstraction-smell.py" \
        "$PROJECT_ROOT/.omc/skills/readability-first-coding/scripts/check-abstraction-smell.py" \
        ; do
        if [ -f "$candidate" ]; then
            CHECKER="$candidate"
            break
        fi
    done
fi

# Only run if we have Python available
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    echo "[readability-first] Python not found, skipping abstraction smell check."
    exit 0
fi

PYTHON=$(command -v python3 || command -v python)

# Get changed Java/Python files in this commit.
# ACMR = Added, Copied, Modified, Renamed. Renamed files may contain
# abstraction smells that should be checked (pre-rename code was recently
# touched and could have introduced unnecessary indirection).
CHANGED=$(git diff --cached --name-only --diff-filter=ACMR 2>/dev/null | grep -E '\.(java|py)$' || true)

if [ -z "$CHANGED" ]; then
    echo "[readability-first] No Java/Python files staged, skipping."
    exit 0
fi

FILE_COUNT=$(echo "$CHANGED" | wc -l)
FILE_COUNT="${FILE_COUNT//[[:space:]]/}"
echo "[readability-first] Checking staged files for abstraction smells..."
if [ "$FILE_COUNT" -eq 1 ]; then
    echo "[readability-first] Files: 1 staged Java/Python file"
else
    echo "[readability-first] Files: $FILE_COUNT staged Java/Python files"
fi

# Run the checker.
# Known exit codes from check-abstraction-smell.py:
#   0 - no smells found (pass)
#   1 - smells/warnings found (block commit)
#   2 - runtime error (bad args, missing files, etc.)
#   * - unexpected error (treat as blocker for safety)
if [ -f "$CHECKER" ]; then
    CHECK_RESULT=0
    "$PYTHON" "$CHECKER" "$PROJECT_ROOT" --lang auto || CHECK_RESULT=$?

    if [ "$CHECK_RESULT" -eq 0 ]; then
        echo "[readability-first] Passed - no abstraction smells detected."
        exit 0
    elif [ "$CHECK_RESULT" -eq 2 ]; then
        echo ""
        echo "[readability-first] ERROR: abstraction smell checker failed (exit code 2)."
        echo "[readability-first] The checker encountered a runtime error. Check that the"
        echo "[readability-first] project root is valid and Python is configured correctly."
        exit 1
    elif [ "$CHECK_RESULT" -eq 1 ]; then
        echo ""
        echo "[readability-first] Abstraction smells found!"
        echo "[readability-first] Review the warnings above. If these abstractions were"
        echo "[readability-first] explicitly requested, you can ignore this warning and"
        echo "[readability-first] commit with: git commit --no-verify"
        echo ""
        echo "[readability-first] If they were NOT requested, consider inlining the code"
        echo "[readability-first] before committing."
        exit 1
    else
        echo ""
        echo "[readability-first] ERROR: checker exited with unexpected code $CHECK_RESULT."
        echo "[readability-first] This may indicate a crash or unhandled error in the checker."
        exit 1
    fi
else
    echo "[readability-first] WARNING: check-abstraction-smell.py not found at: $CHECKER"
    echo "[readability-first] Skipping abstraction smell check."
    exit 0
fi