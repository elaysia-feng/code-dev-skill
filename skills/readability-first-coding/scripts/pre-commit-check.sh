#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Pre-commit check: scan staged Java/Python files for abstraction smells.
#
# Default behavior is advisory: smells are printed but do not block commits.
# Set READABILITY_FIRST_STRICT=1 to make smell warnings/errors block the commit.
#
# Install:
#   cp scripts/pre-commit-check.sh .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit
# ---------------------------------------------------------------------------

set -u

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
STRICT="${READABILITY_FIRST_STRICT:-0}"
CHECKER=""

if [ -n "${BASH_SOURCE[0]:-}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    SKILL_DIR="$(dirname "$SCRIPT_DIR")"
    CANDIDATE="$SKILL_DIR/scripts/check-abstraction-smell.py"
    if [ -f "$CANDIDATE" ]; then
        CHECKER="$CANDIDATE"
    fi
fi

if [ -z "$CHECKER" ]; then
    for candidate in \
        "$PROJECT_ROOT/.claude/skills/readability-first-coding/scripts/check-abstraction-smell.py" \
        "$PROJECT_ROOT/skills/readability-first-coding/scripts/check-abstraction-smell.py" \
        ; do
        if [ -f "$candidate" ]; then
            CHECKER="$candidate"
            break
        fi
    done
fi

if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
    echo "[readability-first] Python not found; skipping advisory smell check."
    exit 0
fi

PYTHON=$(command -v python3 || command -v python)
CHANGED=$(git diff --cached --name-only --diff-filter=ACMR 2>/dev/null | grep -E '\.(java|py)$' || true)

if [ -z "$CHANGED" ]; then
    exit 0
fi

if [ -z "$CHECKER" ] || [ ! -f "$CHECKER" ]; then
    echo "[readability-first] Checker not found; skipping smell check."
    if [ "$STRICT" = "1" ]; then
        echo "[readability-first] READABILITY_FIRST_STRICT=1, so missing checker blocks commit."
        exit 1
    fi
    exit 0
fi

FILE_COUNT=$(printf '%s\n' "$CHANGED" | wc -l)
FILE_COUNT="${FILE_COUNT//[[:space:]]/}"
echo "[readability-first] Reviewing $FILE_COUNT staged Java/Python file(s)..."

CHECK_RESULT=0
"$PYTHON" "$CHECKER" "$PROJECT_ROOT" --lang auto --files "$CHANGED" || CHECK_RESULT=$?

case "$CHECK_RESULT" in
    0)
        echo "[readability-first] No abstraction smells detected."
        exit 0
        ;;
    1)
        echo ""
        echo "[readability-first] Smells detected. Treat these as review prompts, not proof of a bad architecture."
        echo "[readability-first] Existing project conventions and explicitly requested abstractions may be valid."
        if [ "$STRICT" = "1" ]; then
            echo "[readability-first] Strict mode enabled; blocking commit."
            exit 1
        fi
        echo "[readability-first] Advisory mode; commit is allowed."
        exit 0
        ;;
    *)
        echo ""
        echo "[readability-first] Checker failed with exit code $CHECK_RESULT."
        if [ "$STRICT" = "1" ]; then
            echo "[readability-first] Strict mode enabled; blocking commit."
            exit 1
        fi
        echo "[readability-first] Advisory mode; skipping failed check."
        exit 0
        ;;
esac
