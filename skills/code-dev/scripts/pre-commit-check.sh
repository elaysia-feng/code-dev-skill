#!/usr/bin/env bash
# code-dev 提交钩子：检查本次暂存的 Java / Python 代码。
#
# 默认只提示不阻断。两种情况始终阻断，因为它们不是"风格问题"，
# 而是"检查根本没做完"，放过等于给出一个假的绿灯：
#   - 源文件不是 UTF-8，两个检查器都读不了它
#   - check_comments.py 报出 ERROR（语法错误 / 读取失败 / 待办缺负责人）
#
# 两个检查器都读**索引**内容而不是工作区。传工作区路径是行不通的：
# "暂存违规内容后再把工作区改干净"能绕过门禁，而"暂存干净内容但还在编辑"
# 会误拦一个本来干净的提交。
#
# READABILITY_FAIL_ON=warning 或 READABILITY_FIRST_STRICT=1 时，
# 抽象检查器的 WARNING 也会阻断。
set -euo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 在若干已知安装位置查找某个检查器脚本。
find_checker() {
  local script="$1"
  local candidate
  for candidate in \
    "$SCRIPT_DIR/$script" \
    "$PROJECT_ROOT/.claude/skills/code-dev/scripts/$script" \
    "$PROJECT_ROOT/.agents/skills/code-dev/scripts/$script" \
    "$PROJECT_ROOT/.omc/skills/code-dev/scripts/$script" \
    "$PROJECT_ROOT/skills/code-dev/scripts/$script" \
    "$HOME/.claude/skills/code-dev/scripts/$script" \
    "$HOME/.agents/skills/code-dev/scripts/$script" \
    "$HOME/.codex/skills/code-dev/scripts/$script"; do
    if [ -f "$candidate" ]; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

# 1. 解析解释器，缺省时跳过检查（STRICT 模式下直接失败）
PYTHON_BIN="${READABILITY_PYTHON:-}"
if [ -z "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3 || command -v python || true)"
fi
if [ -z "$PYTHON_BIN" ]; then
  echo '[code-dev] 找不到 Python，跳过检查。Windows 上请设置 READABILITY_PYTHON。'
  [ "${READABILITY_FIRST_STRICT:-0}" = "1" ] && exit 1
  exit 0
fi

FAIL_ON="${READABILITY_FAIL_ON:-none}"
if [ "${READABILITY_FIRST_STRICT:-0}" = "1" ] && [ "$FAIL_ON" = "none" ]; then
  FAIL_ON=warning
fi

STATUS=0

# 2. 抽象检查器：读暂存区内容，按 FAIL_ON 决定是否阻断
SMELL="${READABILITY_CHECKER:-}"
if [ -z "$SMELL" ] || [ ! -f "$SMELL" ]; then
  if ! SMELL="$(find_checker check-abstraction-smell.py)"; then
    SMELL=""
  fi
fi
if [ -z "$SMELL" ]; then
  echo '[code-dev] 找不到 check-abstraction-smell.py，跳过抽象检查。'
  [ "${READABILITY_FIRST_STRICT:-0}" = "1" ] && exit 1
else
  echo '[code-dev] 抽象检查（暂存区）：'
  "$PYTHON_BIN" "$SMELL" "$PROJECT_ROOT" --staged --fail-on "$FAIL_ON" || STATUS=$?
fi

# 3. 注释检查器：读暂存区内容。
#    早先这里既没跑注释检查器、又是按工作区路径跑的，所以注释规范在提交
#    卡点上先是无覆盖、后是可绕过 —— 而它恰恰是唯一带 ERROR 语义的检查器。
COMMENT=""
if ! COMMENT="$(find_checker check_comments.py)"; then
  COMMENT=""
fi
if [ -z "$COMMENT" ]; then
  echo '[code-dev] 找不到 check_comments.py，跳过注释检查。'
  [ "${READABILITY_FIRST_STRICT:-0}" = "1" ] && exit 1
else
  STAGED=()
  while IFS= read -r -d '' f; do
    case "$f" in
      *.java|*.py) STAGED+=("$f") ;;
    esac
  done < <(git diff --cached --name-only --diff-filter=ACMR -z)

  if [ ${#STAGED[@]} -eq 0 ]; then
    echo '[code-dev] 注释检查：本次没有暂存 Java/Python 文件，跳过。'
  else
    echo "[code-dev] 注释检查（暂存区，${#STAGED[@]} 个文件）："
    "$PYTHON_BIN" "$COMMENT" --staged || {
      rc=$?
      # 注释检查器只有 ERROR 才非零，那属于"检查未完成"或硬性违规，一律阻断
      STATUS=$rc
    }
  fi
fi

exit "$STATUS"