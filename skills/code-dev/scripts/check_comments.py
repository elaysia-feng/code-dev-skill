#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""代码注释规范静态检查脚本。

对 Java / Python 源文件做基于正则与 AST 的启发式检查，覆盖《代码注释规范》中
客观可验证的部分：

- public 方法/函数缺少 Javadoc / Docstring          -> WARNING
- TODO 未标注负责人                                 -> ERROR
- 有参数但文档缺 @param / Args:                      -> WARNING
- 有返回值但文档缺 @return / Returns:                -> WARNING
- 复杂方法缺少主要步骤编号 / 需要人工复核可读性        -> WARNING

用法::

    python3 check_comments.py <文件或目录> [<文件或目录> ...]

退出码::

    0  没有 ERROR（可能仍有 WARNING）
    1  存在 ERROR
    2  没有任何可检查的文件（targets 没匹配到 .java / .py）

这是启发式检查而非完整语法分析，Java 部分对复杂泛型、内部类等场景可能误判，
结果仅作自查辅助。
"""

import argparse
import ast
import io
import re
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Tuple

ERROR = "ERROR"
WARNING = "WARNING"

#: 步骤编号注释，如 ``// 1. 参数校验`` 或 ``# 1.1 校验手机号``
STEP_COMMENT_RE = re.compile(r"^\s*(?://|#)\s*\d+(?:\.\d+)*[.、．]?\s+\S")

#: 区分待办标记与完整格式；括号、负责人、冒号和说明均须存在。
TODO_RE = re.compile(r"\btodo\b", re.IGNORECASE)
TODO_FORMAT_RE = re.compile(r"TODO\s*\([^()\r\n]*[^()\s][^()\r\n]*\)\s*:\s*\S", re.IGNORECASE)

#: 复杂方法判定阈值
COMPLEX_LINE_THRESHOLD = 20
COMPLEX_BRANCH_THRESHOLD = 3
#: 短方法不自动触发复杂度提示；短小但确有多阶段逻辑时仍应按规范编号。
SIMPLE_LINE_THRESHOLD = 10

#: 递归目录时跳过的目录名
SKIP_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode", "__pycache__",
    "node_modules", "venv", ".venv", "build", "dist", "target", ".tox",
}

JAVA_KEYWORD_NAMES = {
    "if", "for", "while", "switch", "catch", "synchronized", "return", "new",
    "do", "else", "try", "assert", "throw",
}
JAVA_TYPE_DECL_KEYWORDS = {"class", "interface", "enum", "record", "@interface"}

JAVA_METHOD_RE = re.compile(
    r"^\s*(?P<mods>(?:(?:public|protected|private|static|final|abstract|"
    r"synchronized|native|default|strictfp|transient|volatile)\s+)+)"
    r"(?:<[^>]+>\s*)?"                       # 泛型方法声明，如 <T>
    r"(?:(?P<type>[\w$.<>\[\],?\s]+?)\s+)?"  # 返回类型，构造方法没有
    r"(?P<name>[\w$]+)\s*\("
)

JAVA_BRANCH_RE = re.compile(r"\b(?:if|for|while|switch|try|catch|do)\b")
JAVA_LOCAL_TYPE_RE = re.compile(r"\b(?:class|interface|enum|record)\s+[\w$]+\b")
JAVA_ANONYMOUS_TYPE_RE = re.compile(
    r"\bnew\s+[\w$.<>?,\[\]\s]+\s*\([^;{}]*\)\s*$"
)


@dataclass
class Issue:
    """一条检查结果。

    Attributes:
        path: 问题所在文件。
        line: 1 起始的行号。
        level: ERROR 或 WARNING。
        code: 规则标识，便于按类型过滤。
        message: 面向人的说明。
    """

    path: Path
    line: int
    level: str
    code: str
    message: str

    def format(self) -> str:
        """渲染成 ``路径:行号: 级别 [规则] 说明`` 形式的一行文本。

        Returns:
            可直接打印的字符串。
        """
        return f"{self.path}:{self.line}: {self.level} [{self.code}] {self.message}"


# --------------------------------------------------------------------------
# 通用检查
# --------------------------------------------------------------------------

def check_todo(path: Path, comment_view: List[str]) -> List[Issue]:
    """检查注释中是否存在没有标注负责人的待办标记。

    Args:
        path: 文件路径，仅用于生成问题报告。
        comment_view: 与源文件等长的"仅注释"行列表，代码与字符串已被抹成空白。

    Returns:
        无负责人待办标记的 ERROR 列表。
    """
    issues: List[Issue] = []
    for lineno, line in enumerate(comment_view, start=1):
        for match in TODO_RE.finditer(line):
            if TODO_FORMAT_RE.match(line, match.start()):
                continue
            issues.append(Issue(
                path, lineno, ERROR, "todo-no-owner",
                "待办格式不完整，应写成 TODO(负责人): 说明，负责人和说明不能为空",
            ))
    return issues


def has_step_comments(lines: List[str], start: int, end: int) -> bool:
    """判断给定行区间内是否出现了步骤编号注释。

    Args:
        lines: 文件的原始行列表。
        start: 起始行号（1 起始，包含）。
        end: 结束行号（1 起始，包含）。

    Returns:
        区间内至少出现 2 条编号注释时返回 True；只有一条说明没有真正拆解流程。
    """
    count = 0
    for line in lines[start - 1:end]:
        if STEP_COMMENT_RE.match(line):
            count += 1
            if count >= 2:
                return True
    return False


# --------------------------------------------------------------------------
# Python 检查
# --------------------------------------------------------------------------

def check_python_file(path: Path, source: str) -> List[Issue]:
    """检查单个 Python 文件的注释规范。

    Args:
        path: 文件路径，仅用于生成问题报告。
        source: 文件文本内容。

    Returns:
        发现的问题列表；文件无法解析时返回一条 ERROR。
    """
    # 1. 解析 AST，语法错误直接作为 ERROR 返回，不再继续分析
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [Issue(path, exc.lineno or 1, ERROR, "parse-error",
                      f"无法解析文件: {exc.msg}")]

    lines = source.splitlines()
    issues: List[Issue] = []

    # 2. 遍历模块顶层定义与类内方法，逐个校验文档与步骤注释
    for node, kind in _iter_python_definitions(tree):
        issues.extend(_check_python_node(path, node, kind, lines))

    # 3. 追加与语言无关的待办标记检查
    issues.extend(check_todo(path, _python_comment_view(source, len(lines))))
    return issues


def _python_comment_view(source: str, line_count: int) -> List[str]:
    """提取 Python 源码中的 ``#`` 注释文本，保持行号一一对应。

    只看注释可以避免把字符串常量、docstring 里出现的字样误判成待办标记。

    Args:
        source: 文件文本内容。
        line_count: 源文件行数。

    Returns:
        与源文件等长的行列表，非注释内容为空字符串。
    """
    view = [""] * line_count
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                row = token.start[0]
                if 1 <= row <= line_count:
                    view[row - 1] += token.string
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # 词法分析失败时返回空视图，宁可漏报也不误报
        return [""] * line_count
    return view


def _iter_python_definitions(tree: ast.Module) -> Iterator[Tuple[ast.AST, str]]:
    """产出需要检查的顶层函数、类以及类内方法（递归处理嵌套类）。

    嵌套在函数体内的内部函数属于实现细节，不在检查范围内；
    嵌套在类内的类需要继续下钻检查其内部方法。

    Args:
        tree: 已解析的模块 AST。

    Yields:
        ``(节点, 中文类型名)`` 二元组。
    """
    def walk(container: List[ast.stmt], in_class: bool) -> Iterator[Tuple[ast.AST, str]]:
        for node in container:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield node, "方法" if in_class else "函数"
            elif isinstance(node, ast.ClassDef):
                yield node, "类"
                # 嵌套类内部的成员也要检查
                yield from walk(node.body, in_class=True)
    yield from walk(tree.body, in_class=False)


def _check_python_node(path: Path, node: ast.AST, kind: str,
                       lines: List[str]) -> List[Issue]:
    """校验单个 Python 定义的 docstring 与步骤注释。

    Args:
        path: 文件路径，仅用于生成问题报告。
        node: 函数、异步函数或类节点。
        kind: 中文类型名，用于提示文案。
        lines: 文件的原始行列表。

    Returns:
        该定义上发现的问题列表。
    """
    name = node.name  # type: ignore[attr-defined]
    # 1. 下划线开头视为非 public，跳过
    if name.startswith("_"):
        return []

    # 2. 缺文档只提示人工判断，简单属性不必机械补注释
    doc = ast.get_docstring(node)
    line = node.lineno  # type: ignore[attr-defined]
    if not doc:
        return [Issue(path, line, WARNING, "missing-doc",
                      f"public {kind} `{name}` 缺少 docstring")]
    if kind == "类":
        # 类有 docstring 后，还要看是否有公共属性需要 Attributes: 小节
        if _python_class_has_attributes(node) and "Attributes:" not in doc:
            return [Issue(path, line, WARNING, "missing-attributes",
                           f"类 `{name}` 有公共属性但 docstring 缺少 Attributes: 小节")]
        return []

    issues: List[Issue] = []
    # 3. 有参数 / 有返回值时检查 Google Style 小节是否齐全
    if _python_has_params(node) and "Args:" not in doc:
        issues.append(Issue(path, line, WARNING, "missing-args",
                            f"`{name}` 有参数但 docstring 缺少 Args: 小节"))
    if _python_returns_value(node) and not any(tag in doc for tag in ("Returns:", "Yields:")):
        issues.append(Issue(path, line, WARNING, "missing-returns",
                            f"`{name}` 有返回值但 docstring 缺少 Returns: 小节"))

    # 4. 复杂方法缺少阶段编号时提示人工补充，并复核业务约束是否清楚
    if _is_complex_python(node):
        end_line = getattr(node, "end_lineno", line)
        if not has_step_comments(lines, line, end_line):
            issues.append(Issue(path, line, WARNING, "missing-step-comments",
                                f"`{name}` 多阶段流程需用 1.、1.1 等编号注释标出主要步骤"))
        issues.append(Issue(path, line, WARNING, "review-complexity",
                            f"`{name}` 流程较复杂，请复核步骤编号和业务约束是否清楚"))
    return issues


def _python_has_params(node: ast.AST) -> bool:
    """判断函数是否有除 self / cls 之外的参数。

    Args:
        node: 函数或异步函数节点。

    Returns:
        存在需要文档化的参数时返回 True。
    """
    args = node.args  # type: ignore[attr-defined]
    positional = list(getattr(args, "posonlyargs", [])) + list(args.args)
    # 实例方法与类方法的第一个参数不需要写进 Args
    if positional and positional[0].arg in ("self", "cls"):
        positional = positional[1:]
    return bool(positional or args.kwonlyargs or args.vararg or args.kwarg)


def _python_class_has_attributes(node: ast.AST) -> bool:
    """判断类是否声明了需要文档化的公共属性。

    只识别以下两类：
    - 带类型注解的赋值：``name: type`` 或 ``name: type = value``
    - 常量赋值：``NAME = <字面量>``（全大写视为模块常量）

    启发式避免把方法、嵌套类、``self.x = ...`` 之类的实例属性误算进来。

    Args:
        node: 类节点（ast.ClassDef）。

    Returns:
        存在需要 Attributes: 小节描述的公共属性时返回 True。
    """
    for stmt in node.body:  # type: ignore[attr-defined]
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            if not stmt.target.id.startswith("_"):
                return True
        elif isinstance(stmt, ast.Assign):
            # 仅当赋值目标是单个 Name 且值是字面量时算作"属性"
            if len(stmt.targets) != 1:
                continue
            target = stmt.targets[0]
            if not isinstance(target, ast.Name):
                continue
            if target.id.startswith("_"):
                continue
            if isinstance(stmt.value, (ast.Constant,)):
                return True
    return False


def _python_returns_value(node: ast.AST) -> bool:
    """判断函数是否会返回有意义的值。

    Args:
        node: 函数或异步函数节点。

    Returns:
        存在带值的 return、yield 或非 None 的返回注解时返回 True。
    """
    # 1. 返回注解显式写了非 None 类型；同时兼容字符串形式的 "None"
    #    其他字符串前向引用（如 "User"）都代表有返回值
    annotation = getattr(node, "returns", None)
    if annotation is not None:
        is_none = isinstance(annotation, ast.Constant) and annotation.value in (None, "None")
        if not is_none:
            return True

    # 2. 否则看函数体内是否有 return <值> 或 yield
    body = node.body  # type: ignore[attr-defined]
    for stmt in body:
        for child in _walk_skip_nested(stmt):
            if child is stmt and isinstance(
                    child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(child, ast.Return) and child.value is not None:
                return True
            if isinstance(child, (ast.Yield, ast.YieldFrom)):
                return True
    return False


def _is_complex_python(node: ast.AST) -> bool:
    """按方法体行数与分支数判断 Python 函数是否属于复杂方法。

    docstring 不计入方法长度，短方法按规范 3.1 一律豁免。
    嵌套在方法体内的内部函数/类不计入外层分支数。

    Args:
        node: 函数或异步函数节点。

    Returns:
        行数或分支数达到阈值时返回 True。
    """
    # 1. 计算不含 docstring 的方法体行数
    body = node.body  # type: ignore[attr-defined]
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str) and len(body) > 1:
        body = body[1:]
    if not body:
        return False
    start = body[0].lineno
    end = getattr(node, "end_lineno", None) or start
    length = end - start + 1

    # 2. 短方法直接豁免，长方法直接判定为复杂
    if length < SIMPLE_LINE_THRESHOLD:
        return False
    if length >= COMPLEX_LINE_THRESHOLD:
        return True

    # 3. 中等长度的方法看分支/循环/try 的数量
    #    嵌套 def/class 属于实现细节，其分支不计入外层
    branch_types = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try)
    branches = sum(1 for stmt in body for child in _walk_skip_nested(stmt)
                   if isinstance(child, branch_types))
    return branches >= COMPLEX_BRANCH_THRESHOLD


def _walk_skip_nested(node: ast.AST) -> Iterator[ast.AST]:
    """遍历 AST，但不进入嵌套的函数/类定义。

    内部函数、嵌套类属于实现细节，其分支不应计入外层方法的复杂度。
    遇到嵌套 def/class 时，节点本身仍然 yield，但**不**继续下钻。

    Args:
        node: 任意 AST 节点。

    Yields:
        节点自身；非嵌套 def/class 时还包括其后代。
    """
    yield node
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        # 嵌套 def/class 的 body 属于实现细节，不向下遍历
        return
    for child in ast.iter_child_nodes(node):
        yield from _walk_skip_nested(child)


# --------------------------------------------------------------------------
# Java 检查
# --------------------------------------------------------------------------

def check_java_file(path: Path, source: str) -> List[Issue]:
    """检查单个 Java 文件的注释规范。

    Args:
        path: 文件路径，仅用于生成问题报告。
        source: 文件文本内容。

    Returns:
        发现的问题列表。
    """
    lines = source.splitlines()
    # 1. 先拆出"纯代码"与"纯注释"两个视图，避免注释里的伪声明被当成方法
    code, comments = _split_java_views(lines)

    issues: List[Issue] = []
    # 2. 逐行寻找 public / protected 方法声明并校验
    for index, code_line in enumerate(code):
        match = JAVA_METHOD_RE.match(code_line)
        if not match or not _is_java_method_decl(match, code_line):
            continue
        issues.extend(_check_java_method(path, match, index, lines, code))

    # 3. 追加与语言无关的待办标记检查
    issues.extend(check_todo(path, comments))
    return issues


def _split_java_views(lines: List[str]) -> Tuple[List[str], List[str]]:
    """把每行拆成"纯代码"与"纯注释"两个视图。

    两个视图与原文件等长、等宽：代码视图抹掉注释与字符串字面量，注释视图只保留
    注释文本。列宽不变，方便用同一套行号/下标定位。

    关键边界条件：
    - Javadoc 内的 ``{@code /* foo */}`` 不应关闭块注释
    - Java 文本块（``\"\"\"...\"\"\"``）整体作为字符串处理
    - 普通字符串/字符字面量内的 ``/* */`` 不作为注释起止

    Args:
        lines: 文件的原始行列表。

    Returns:
        ``(代码视图, 注释视图)``。
    """
    code_lines: List[str] = []
    comment_lines: List[str] = []
    in_block = False        # 是否处于 /* ... */ 块注释内
    in_javadoc = False      # 块注释是否由 /** 开头
    tag_depth = 0           # Javadoc 内 {@...} 内联标签的嵌套深度
    in_text_block = False   # 是否处于 """...""" 文本块内（跨行）
    for line in lines:
        code: List[str] = []
        comment: List[str] = []
        i = 0

        # 1. 跨行的文本块：先把当前行收尾到匹配的 """ 之前
        if in_text_block:
            close = line.find('"""')
            if close < 0:
                code.append(" " * len(line))
                comment.append(" " * len(line))
                code_lines.append("".join(code))
                comment_lines.append("".join(comment))
                continue
            code.append(" " * (close + 3))
            comment.append(" " * (close + 3))
            i = close + 3
            in_text_block = False

        while i < len(line):
            three = line[i:i + 3]
            two = line[i:i + 2]
            # 1. 块注释内部
            if in_block:
                if tag_depth > 0:
                    # {@code ...} 等内联标签内：字符按字面量处理
                    if line[i] == "}":
                        tag_depth -= 1
                        code.append("}")
                        comment.append("}")
                        i += 1
                    elif two == "{@":
                        # 嵌套的内联标签
                        tag_depth += 1
                        code.append("  ")
                        comment.append("  ")
                        i += 2
                    else:
                        code.append(" ")
                        comment.append(line[i])
                        i += 1
                else:
                    if two == "*/":
                        in_block = False
                        in_javadoc = False
                        code.append("  ")
                        comment.append("  ")
                        i += 2
                    elif in_javadoc and two == "{@":
                        tag_depth += 1
                        code.append("  ")
                        comment.append("  ")
                        i += 2
                    else:
                        code.append(" ")
                        comment.append(line[i])
                        i += 1
            # 2. Java 文本块 """（不在 """ 开头或紧跟第四个 " 时）
            elif three == '"""' and (i + 3 >= len(line) or line[i + 3] != '"'):
                in_text_block = True
                code.append("   ")
                comment.append("   ")
                i += 3
            # 3. 块注释起始
            elif two == "/*":
                in_block = True
                in_javadoc = (i + 2 < len(line) and line[i + 2] == "*")
                code.append("  ")
                comment.append("  ")
                i += 2
            elif two == "//":
                rest = line[i:]
                code.append(" " * len(rest))
                comment.append(rest)
                break
            # 4. 字符串/字符字面量：两个视图都抹成空白
            elif line[i] in "\"'":
                quote = line[i]
                code.append(" ")
                comment.append(" ")
                i += 1
                while i < len(line):
                    if line[i] == "\\":
                        code.append("  ")
                        comment.append("  ")
                        i += 2
                        continue
                    code.append(" ")
                    comment.append(" ")
                    if line[i] == quote:
                        i += 1
                        break
                    i += 1
            # 5. 普通代码字符
            else:
                code.append(line[i])
                comment.append(" ")
                i += 1
        code_lines.append("".join(code))
        comment_lines.append("".join(comment))
    return code_lines, comment_lines


def _is_java_method_decl(match: "re.Match[str]", code_line: str) -> bool:
    """排除字段、类型声明、控制语句等误匹配。

    Args:
        match: JAVA_METHOD_RE 的匹配结果。
        code_line: 去噪后的整行代码。

    Returns:
        判定为 public/protected 方法或构造方法声明时返回 True。
    """
    mods = match.group("mods")
    # 1. 只关心对外可见的方法
    if "public" not in mods and "protected" not in mods:
        return False
    # 2. 排除控制语句与 class / interface / enum / record 声明
    name = match.group("name")
    type_token = (match.group("type") or "").strip().split()
    if name in JAVA_KEYWORD_NAMES:
        return False
    if any(token in JAVA_TYPE_DECL_KEYWORDS for token in type_token):
        return False
    # 3. 排除带初始化表达式的字段，如 public Foo bar = new Foo();
    head = code_line[:match.end()]
    return "=" not in head


def _check_java_method(path: Path, match: "re.Match[str]", index: int,
                       lines: List[str], code: List[str]) -> List[Issue]:
    """校验单个 Java 方法的 Javadoc 与步骤注释。

    Args:
        path: 文件路径，仅用于生成问题报告。
        match: 方法声明行的匹配结果。
        index: 声明行在列表中的 0 起始下标。
        lines: 文件的原始行列表。
        code: 去噪后的代码行列表。

    Returns:
        该方法上发现的问题列表。
    """
    name = match.group("name")
    lineno = index + 1

    # 1. 缺 Javadoc 只提示人工判断，缺失时跳过标签检查
    javadoc = _find_javadoc(lines, index)
    if javadoc is None:
        return [Issue(path, lineno, WARNING, "missing-doc",
                      f"public/protected 方法 `{name}` 缺少 Javadoc 文档注释")]

    issues: List[Issue] = []
    # 2. 有参数 / 有返回值时检查 @param 与 @return
    if _java_has_params(code, index, match.end()) and "@param" not in javadoc:
        issues.append(Issue(path, lineno, WARNING, "missing-param",
                            f"`{name}` 有参数但 Javadoc 缺少 @param"))
    return_type = (match.group("type") or "").strip()
    if return_type and return_type != "void" and "@return" not in javadoc:
        issues.append(Issue(path, lineno, WARNING, "missing-return",
                            f"`{name}` 有返回值但 Javadoc 缺少 @return"))

    # 3. 复杂方法缺少阶段编号时提示人工补充，抽象或接口方法没有方法体时跳过
    body = _find_java_body(code, index)
    if body is not None:
        start, end = body
        if _is_complex_java(code, start, end):
            if not has_step_comments(lines, start + 1, end + 1):
                issues.append(Issue(path, lineno, WARNING, "missing-step-comments",
                                    f"`{name}` 多阶段流程需用 1.、1.1 等编号注释标出主要步骤"))
            issues.append(Issue(path, lineno, WARNING, "review-complexity",
                                f"`{name}` 流程较复杂，请复核步骤编号和业务约束是否清楚"))
    return issues


def _find_javadoc(lines: List[str], index: int) -> Optional[str]:
    """向上查找方法声明对应的 Javadoc 块。

    Args:
        lines: 文件的原始行列表。
        index: 方法声明行的 0 起始下标。

    Returns:
        Javadoc 文本；没有 Javadoc 时返回 None。
    """
    # 1. 跳过注解与空行，定位到紧邻的上一段非空内容
    i = index - 1
    while i >= 0:
        stripped = lines[i].strip()
        if not stripped or stripped.startswith("@") or stripped.startswith("//"):
            i -= 1
            continue
        break
    if i < 0 or not stripped.endswith("*/"):
        return None

    # 2. 继续向上找 /** 起始行
    #    Javadoc 内容里可能出现 /*（如 {@code /* foo */}），所以不要在
    #    第一个含 /* 的行停下；一直走到含 /** 的行才是真正的开头。
    end = i
    while i >= 0 and "/**" not in lines[i]:
        i -= 1
    if i < 0:
        return None
    return "\n".join(lines[i:end + 1])


def _java_has_params(code: List[str], index: int, paren_pos: int) -> bool:
    """判断方法参数列表是否非空。

    Args:
        code: 去噪后的代码行列表。
        index: 方法声明行的 0 起始下标。
        paren_pos: 声明行中左括号之后的位置。

    Returns:
        参数列表有内容时返回 True。
    """
    # 参数列表可能跨行，向后拼接若干行后按括号配对截取
    text = " ".join([code[index][paren_pos:]] + code[index + 1:index + 20])
    depth = 1
    params: List[str] = []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                break
        params.append(ch)
    return bool("".join(params).strip())


def _find_java_body(code: List[str], index: int) -> Optional[Tuple[int, int]]:
    """定位方法体的起止行下标。

    Args:
        code: 去噪后的代码行列表。
        index: 方法声明行的 0 起始下标。

    Returns:
        ``(起始行下标, 结束行下标)``；抽象方法或括号不配对时返回 None。
    """
    # 1. 先找到方法体左花括号，若先遇到分号说明是抽象/接口方法
    start = None
    for i in range(index, min(index + 20, len(code))):
        line = code[i]
        if "{" in line:
            start = i
            break
        if ";" in line:
            return None
    if start is None:
        return None

    # 2. 从左花括号开始配对计数，找到方法体结束行
    depth = 0
    for i in range(start, len(code)):
        depth += code[i].count("{") - code[i].count("}")
        if i >= start and depth <= 0:
            return start, i
    return None


def _is_complex_java(code: List[str], start: int, end: int) -> bool:
    """按行数与分支数判断 Java 方法是否属于复杂方法。

    短方法按规范 3.1 一律豁免。

    Args:
        code: 去噪后的代码行列表。
        start: 方法体起始行下标。
        end: 方法体结束行下标。

    Returns:
        行数或分支数达到阈值时返回 True。
    """
    outer_code, included_lines = _java_outer_method_view(code, start, end)
    length = sum(included_lines)
    if length < SIMPLE_LINE_THRESHOLD:
        return False
    if length >= COMPLEX_LINE_THRESHOLD:
        return True
    branches = sum(len(JAVA_BRANCH_RE.findall(line)) for line in outer_code)
    return branches >= COMPLEX_BRANCH_THRESHOLD


def _java_outer_method_view(code: List[str], start: int,
                            end: int) -> Tuple[List[str], List[bool]]:
    """移除 Java 方法内局部类与匿名类的实现，只保留外层方法代码。

    Args:
        code: 去噪后的代码行列表。
        start: 方法体起始行下标。
        end: 方法体结束行下标。

    Returns:
        外层代码行与每个原始行是否仍属于外层方法的标记。
    """
    outer_lines: List[str] = []
    included_lines: List[bool] = []
    depth = 0
    skipped_depth: Optional[int] = None
    header = ""

    for line in code[start:end + 1]:
        output = [" "] * len(line)
        outside_nested = skipped_depth is None
        for index, char in enumerate(line):
            if skipped_depth is not None:
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth < skipped_depth:
                        skipped_depth = None
                        outside_nested = True
                        output[index] = char
                        header = ""
                continue

            outside_nested = True
            if char == "{":
                is_nested_type = depth >= 1 and (
                    JAVA_LOCAL_TYPE_RE.search(header) is not None
                    or JAVA_ANONYMOUS_TYPE_RE.search(header) is not None
                )
                depth += 1
                if is_nested_type:
                    skipped_depth = depth
                else:
                    output[index] = char
                header = ""
            elif char == "}":
                depth -= 1
                output[index] = char
                header = ""
            else:
                output[index] = char
                if char == ";":
                    header = ""
                else:
                    header = (header + char)[-1000:]

        outer_lines.append("".join(output))
        included_lines.append(outside_nested)

    return outer_lines, included_lines


# --------------------------------------------------------------------------
# 入口
# --------------------------------------------------------------------------

def iter_source_files(targets: Iterable[str]) -> Iterator[Path]:
    """展开命令行参数，产出待检查的 .java / .py 文件。

    Args:
        targets: 命令行传入的文件或目录路径。

    Yields:
        待检查的文件路径。
    """
    for target in targets:
        path = Path(target)
        # 1. 显式文件和目录使用相同的语言边界，避免非源码被统计为已检查。
        if path.is_file():
            if path.suffix in (".java", ".py"):
                yield path
        # 2. 目录递归展开，跳过构建产物与虚拟环境
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.suffix in (".java", ".py") and child.is_file():
                    if not any(part in SKIP_DIRS for part in child.parts):
                        yield child
        # 3. 路径不存在时提示但不中断整体检查
        else:
            print(f"跳过不存在的路径: {target}", file=sys.stderr)


def check_file(path: Path) -> List[Issue]:
    """按扩展名分发到对应语言的检查器。

    Args:
        path: 待检查的文件路径。

    Returns:
        该文件的问题列表；读取失败时返回一条 ERROR。
    """
    # 1. 读取源码，编码或权限问题直接作为 ERROR 上报
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [Issue(path, 1, ERROR, "read-error", f"无法读取文件: {exc}")]

    # 2. 按扩展名分发，其他类型文件不检查
    if path.suffix == ".py":
        return check_python_file(path, source)
    if path.suffix == ".java":
        return check_java_file(path, source)
    return []


def main(argv: Optional[List[str]] = None) -> int:
    """脚本入口：检查指定文件或目录并打印结果。

    Args:
        argv: 命令行参数列表，默认取 sys.argv[1:]。

    Returns:
        存在 ERROR 时返回 1，否则返回 0。
    """
    # 1. 解析参数并展开待检查文件
    parser = argparse.ArgumentParser(description="代码注释规范静态检查（Java / Python）")
    parser.add_argument("targets", nargs="+", help="待检查的文件或目录")
    args = parser.parse_args(argv)

    files = list(iter_source_files(args.targets))
    if not files:
        # 没有匹配到文件 ≠ 没有问题；用退出码 2 与 stderr 提示区分
        print("没有找到可检查的 .java / .py 文件（退出码 2）", file=sys.stderr)
        return 2

    # 2. 逐文件检查并按文件、行号排序输出
    issues: List[Issue] = []
    for path in files:
        issues.extend(check_file(path))
    for issue in sorted(issues, key=lambda item: (str(item.path), item.line)):
        print(issue.format())

    # 3. 汇总统计，有 ERROR 时以非 0 退出码结束
    errors = sum(1 for issue in issues if issue.level == ERROR)
    warnings = len(issues) - errors
    print(f"\n检查 {len(files)} 个文件，发现 {errors} 个 ERROR，{warnings} 个 WARNING")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
