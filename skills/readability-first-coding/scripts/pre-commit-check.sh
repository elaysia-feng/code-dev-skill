#!/usr/bin/env bash
# 检查暂存版本；默认提示，READABILITY_FAIL_ON=warning 时才阻断 warning。
set -euo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECKER="${READABILITY_CHECKER:-$SCRIPT_DIR/check-abstraction-smell.py}"
STRICT="${READABILITY_FIRST_STRICT:-0}"

if [ ! -f "$CHECKER" ]; then
    for candidate in \
        "$PROJECT_ROOT/.claude/skills/readability-first-coding/scripts/check-abstraction-smell.py" \
        "$PROJECT_ROOT/.agents/skills/readability-first-coding/scripts/check-abstraction-smell.py" \
        "$PROJECT_ROOT/.omc/skills/readability-first-coding/scripts/check-abstraction-smell.py" \
        "$PROJECT_ROOT/skills/readability-first-coding/scripts/check-abstraction-smell.py" \
        "$HOME/.claude/skills/readability-first-coding/scripts/check-abstraction-smell.py" \
        "$HOME/.codex/skills/readability-first-coding/scripts/check-abstraction-smell.py"; do
        if [ -f "$candidate" ]; then
            CHECKER="$candidate"
            break
        fi
    done
fi

if [ ! -f "$CHECKER" ]; then
    echo '[readability-first] 找不到检查器，跳过 advisory smell check。'
    [ "$STRICT" = "1" ] && exit 1
    exit 0
fi

PYTHON_BIN="${READABILITY_PYTHON:-}"
if [ -z "$PYTHON_BIN" ]; then
    PYTHON_BIN="$(command -v python3 || command -v python || true)"
fi
if [ -z "$PYTHON_BIN" ]; then
    echo '[readability-first] 找不到 Python，跳过 advisory smell check。'
    [ "$STRICT" = "1" ] && exit 1
    exit 0
fi

FAIL_ON="${READABILITY_FAIL_ON:-none}"
if [ "$STRICT" = "1" ] && [ "$FAIL_ON" = "none" ]; then
    FAIL_ON=warning
fi
exec "$PYTHON_BIN" "$CHECKER" "$PROJECT_ROOT" --staged --fail-on "$FAIL_ON"
