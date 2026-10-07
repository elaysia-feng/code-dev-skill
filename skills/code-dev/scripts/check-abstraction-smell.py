#!/usr/bin/env python3
"""
扫描 Java/Python 代码库中违反 code-dev skill 的抽象坏味道。

检测的坏味道：
  - 只有唯一实现类、且实现类不在 impl/ 子包中的接口（XxxService -> XxxServiceImpl）
  - 近乎空置或只含转发代码的 common/util/shared/base 包
  - 过多继承链（深度 > 2）
  - 转发包装方法
  - Python 中只有一个具体子类的 ABC

实现类位于 `impl/` 子包时**不**报警：规范要求 Java 业务组件一律 interface +
impl/，所以该布局本身就是合规结果，报警等于要求作者违反规范。

用法：
  python check-abstraction-smell.py <project-root>
      [--lang java|python|auto] [--json]
      [--fail-on none|warning|info] [--max-depth N] [--min-package-files N]
      [--files <路径列表>] [--staged]

  --files    只报告涉及所选文件的发现，但分析仍读取全部实现，
             以免把"未修改的实现"误判成不存在
  --staged   分析 Git 暂存区内容而非工作区
  --fail-on  达到该严重程度时以退出码 1 阻断；默认 none，只报告不阻断

退出码：
  0 - 未达到阻断阈值（默认只报告）
  1 - 达到 --fail-on 指定的阻断阈值
  2 - 存在无法按 UTF-8 解码的源文件，或执行检查时出错

源文件一律使用 UTF-8。无法解码的文件会被列在 UNREADABLE / unreadable 中并
让退出码变为 2 —— 它们根本没有进入分析，"没有报出坏味道"对它们不成立。
"""

import argparse
import json
import re
import sys
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

def _strip_generics(text: str) -> str:
    """去除泛型类型参数，含嵌套的尖括号。

    反复剥掉最内层的 <...> 直到没有为止，因此能处理
    class Foo<T extends Comparable<T>> extends Bar 这样的写法。
    同时支持带约束的泛型：T extends Foo & Bar。

    Args:
        text: 待处理的源码片段。

    Returns:
        去掉全部泛型类型参数后的文本。
    """
    while True:
        # 要求 < > 之间至少有一个单词字符，并拒绝含有逻辑运算符（&&、||）的内容：
        # && / || 出现在这里说明是比较表达式，而不是泛型类型参数。
        cleaned = re.sub(r'<(?=[^\s>]*\w)(?![^<>]*(?:&&|\|\|))[^<>]*>', '', text)
        if cleaned == text:
            break
        text = cleaned
    return text


def _split_comma_aware(text: str) -> list[str]:
    """按逗号切分文本，同时感知尖括号、方括号、圆括号的嵌套层级。

    因此 Generic[T, U]、Dict[str, int]、List[Tuple[int, str]] 不会被误切。

    Args:
        text: 待切分的文本。

    Returns:
        切分后的片段列表，末尾非空的残余片段也会计入。
    """
    parts = []
    depth = 0
    current = []
    for ch in text:
        if ch in ('<', '[', '('):
            depth += 1
            current.append(ch)
        elif ch in ('>', ']', ')'):
            depth -= 1
            current.append(ch)
        elif ch == ',' and depth == 0:
            parts.append(''.join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append(''.join(current))
    return parts


_DEPENDENCY_DIRS = frozenset({
    "node_modules", ".git", "__pycache__", "venv", ".venv",
    "target", "build", "dist", ".mvn", ".gradle", "egg-info",
})


def _rglob_filtered(root: Path, pattern: str) -> list[Path]:
    """递归匹配 *pattern* 对应的文件，跳过已知的依赖与缓存目录，避免误报和无谓的扫描开销。

    Args:
        root: 扫描根目录，匹配结果以其为基准计算相对路径。
        pattern: 传给 Path.rglob 的匹配模式。

    Returns:
        命中且路径中不含依赖/缓存目录的文件列表。
    """
    return [
        f for f in root.rglob(pattern)
        if not any(part in _DEPENDENCY_DIRS for part in f.relative_to(root).parts)
    ]


# ---------------------------------------------------------------------------
# 坏味道检测器
# ---------------------------------------------------------------------------

def find_single_impl_interfaces(root: Path, file_list: list[Path] | None = None) -> list[dict]:
    """查找只有唯一实现类的接口。

    Args:
        root: 项目根目录，用于生成相对路径。
        file_list: 已选定的 Java 文件；为 None 时自行扫描 root。

    Returns:
        single_impl_interface 类型的问题列表，含"唯一实现"与"无任何实现"两种。
    """
    results = []
    java_files = file_list if file_list is not None else _rglob_filtered(root, "*.java")
    interfaces = {}
    implementations = defaultdict(set)  # 用 set 去重

    # 1. 逐行扫描源码，同时登记接口声明与实现关系
    for f in java_files:
        try:
            content = f.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue

        # 1.1 逐行匹配声明：跨行的 `class ... implements` 用有限前瞻拼接。
        #     不用 re.DOTALL，避免误匹配注释和字符串字面量。
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # 先剥离行内块注释再做跳过判断，否则 `/* 注释 */ class Foo ...` 会被整行漏掉。
            line = re.sub(r'/\*.*?\*/', '', line).strip()
            # 跳过纯注释行
            if line.startswith('//') or line.startswith('/*') or line.startswith('*'):
                i += 1; continue
            # 跳过纯注解行：同一行里没有 class/interface 关键字
            if line.startswith('@') and not re.search(r'\b(class|interface)\b', line):
                i += 1; continue
            # 剥离剩余的单行注释（// ...）
            line = re.sub(r'//.*$', '', line)

            # 1.2 登记接口声明，排除 @interface 注解类型：只靠负向后顾拦不住
            #     `public @interface Foo`，因为该字符串里 interface 前是空格而不是 @。
            if '@interface' not in line:
                iface_match = re.search(r'(?<!\w)interface\s+(\w+)', line)
                if iface_match:
                    interfaces[iface_match.group(1)] = str(f.relative_to(root))

            # 1.3 匹配实现了接口的 class/record/enum 声明
            m = re.search(r'\b(?:class|record|enum)\s+(\w+)(?:(?!\b(?:class|record|enum|interface)\b).)*\bimplements\s+(.+)', line)
            if not m:
                # 1.3.1 当前行没有 implements，向后最多前瞻 4 行拼出跨行声明
                class_decl = re.search(r'\b(?:class|record|enum)\s+(\w+)', line)
                if class_decl:
                    j = i + 1
                    combined = line
                    while j < len(lines) and j < i + 5:   # 由 3 放宽到 5，以覆盖带多个注解的类
                        nl = lines[j].strip()
                        # 先剥离块注释，否则 `/* ... */ 代码` 会被当成注释行跳过
                        nl_nc = re.sub(r'/\*.*?\*/', '', nl).strip()
                        nl_nc = re.sub(r'//.*$', '', nl_nc).strip()
                        if nl_nc.startswith('/*') or nl_nc.startswith('*'):
                            j += 1; continue
                        if nl_nc.startswith('@'):
                            j += 1; continue
                        if nl_nc == '':
                            j += 1; continue   # 跳过空行而不是中断拼接
                        combined += ' ' + nl_nc
                        if 'implements' in nl_nc:
                            m = re.search(
                                r'\b(?:class|record|enum)\s+(\w+)(?:(?!\b(?:class|record|enum|interface)\b).)*\bimplements\s+(.+)',
                                combined
                            )
                            break
                        j += 1
                    # 跳过已被前瞻消耗的行
                    if m:
                        i = j
            if m:
                iface_list_raw = re.split(r'\s*[{;]', m.group(2))[0]
                # 先剥离泛型再按逗号切分，避免泛型实参里的逗号
                # （如 Bar<Map<String, Object>>）被当成接口列表分隔符。
                iface_list_raw = _strip_generics(iface_list_raw)
                for raw_name in iface_list_raw.split(','):
                    iface_name = raw_name.strip().split('.')[-1]  # 只取简单类名
                    iface_name = iface_name.rstrip('>')  # 去掉残留的 '>'
                    if iface_name:
                        rel_path = str(f.relative_to(root))
                        implementations[iface_name].add(rel_path)
            i += 1

    # 2. 实现类恰好一个且接口已声明时判为坏味道
    for iface_name, impl_set in implementations.items():
        impl_count = len(impl_set)
        if impl_count == 1 and iface_name in interfaces:
            impl_paths = sorted(impl_set)
            # 2.1 豁免"接口 + impl/ 子包"约定：项目采用该布局（接口在父包、实现在
            #     impl/ 子包）时，唯一实现是项目强制约定而非多余的抽象。
            #     依据 references/java-guidelines.md。
            if any("impl" in Path(p).parts for p in impl_paths):
                continue
            results.append({
                "type": "single_impl_interface",
                "severity": "warning",
                "interface": interfaces[iface_name],
                "implementations": impl_paths,
                "message": f"接口 '{iface_name}' 只有 1 个实现且未放在 impl/ 子包中。规范要求 Java 业务组件一律 interface + impl/：把实现移到同包的 impl/ 下，并让调用方依赖接口类型。"
            })

    # 3. 报告项目里声明了却从未被实现的接口
    for iface_name, file_path in interfaces.items():
        if iface_name not in implementations:
            results.append({
                "type": "single_impl_interface",
                "severity": "info",
                "interface": file_path,
                "implementations": [],
                "message": f"Interface '{iface_name}' has no implementations. This interface may be unused dead code."
            })

    return results


def find_suspect_packages(root: Path, min_files: int = 2) -> list[dict]:
    """查找近乎空置或只含转发代码的 common/util/shared/base 包。

    源文件数不超过 min_files 的包判定为可疑：这类小包往往并非用户明确要求，
    可能是多余的抽象。

    Args:
        root: 项目根目录。
        min_files: 仍算可疑的源文件数量上限（含边界）。

    Returns:
        suspect_package 类型的问题列表。
    """
    results = []
    # `core` 是有意排除的：FastAPI + LangGraph 项目约定用 `core/` 放基础设施
    # （config、llm、middleware、langgraph/ 等）。
    suspect_names = {"common", "util", "utils", "shared", "framework", "base"}
    # 排除项按完整路径分段精确匹配
    exclude_dirs = {"node_modules", ".git", "__pycache__", "venv", ".venv",
                    "target", "build", "dist", ".mvn", ".gradle", "egg-info"}

    # 1. 筛选名字可疑、且路径不在排除目录中的包
    for pkg_dir in root.rglob("*"):
        if not pkg_dir.is_dir():
            continue
        if pkg_dir.name not in suspect_names:
            continue
        # 1.1 逐段精确匹配排除项，而不是子串匹配
        if any(part in exclude_dirs for part in pkg_dir.relative_to(root).parts):
            continue

        files = [f for f in pkg_dir.rglob("*") if f.is_file() and f.suffix in (".java", ".py") and not any(p in exclude_dirs for p in f.relative_to(pkg_dir).parts)]
        # 2. 源文件数量未超过阈值时报告
        if len(files) <= min_files:
            results.append({
                "type": "suspect_package",
                "severity": "info",
                "path": str(pkg_dir.relative_to(root)),
                "file_count": len(files),
                "files": [str(f.relative_to(root)) for f in files],
                "message": f"Package '{pkg_dir.relative_to(root)}' has only {len(files)} file(s). Was this created without explicit user request?"
            })

    return results


def find_deep_inheritance(root: Path, max_depth: int = 2,
                           file_list_java: list[Path] | None = None,
                           file_list_py: list[Path] | None = None) -> list[dict]:
    """查找继承链深度超过 max_depth 的类（Java 与 Python）。

    Args:
        root: 项目根目录，用于生成相对路径。
        max_depth: 达到该深度即报告。
        file_list_java: 已选定的 Java 文件；为 None 时自行扫描 root。
        file_list_py: 已选定的 Python 文件；为 None 时自行扫描 root。

    Returns:
        deep_inheritance 类型的问题列表，含完整继承链文本。
    """
    results = []
    extends_graph = {}       # 类名 -> 父类名
    class_files = {}         # 类名 -> 文件路径

    # 1. Java 侧：登记类声明及其 extends 父类
    for f in (file_list_java if file_list_java is not None else _rglob_filtered(root, "*.java")):
        try:
            content = f.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue

        lines_j = content.split('\n')
        i = 0
        while i < len(lines_j):
            stripped = lines_j[i].strip()
            # 先剥离行内块注释再做跳过判断，否则 `/* 注释 */ class Foo extends Bar` 会被整行漏掉。
            stripped_nc = re.sub(r'/\*.*?\*/', '', stripped).strip()
            if stripped_nc == '' or stripped_nc.startswith('//') or stripped_nc.startswith('/*') or stripped_nc.startswith('*'):
                i += 1; continue
            # 跳过纯注解行：同一行里没有 class 关键字
            if stripped_nc.startswith('@') and not re.search(r'\bclass\b', stripped_nc):
                i += 1; continue
            clean_line = _strip_generics(stripped_nc)
            class_match = re.search(r'\bclass\s+(\w+)(?:\s+extends\s+([\w.]+))?', clean_line)
            if class_match:
                class_name = class_match.group(1)
                class_files[class_name] = str(f.relative_to(root))
                if class_match.group(2):
                    extends_graph[class_name] = class_match.group(2).split(".")[-1]
            else:
                # 1.1 跨行声明：本行只有 `class Name`，`extends Parent` 在后面的行
                class_decl = re.search(r'\bclass\s+(\w+)', clean_line)
                if class_decl:
                    class_name = class_decl.group(1)
                    class_files[class_name] = str(f.relative_to(root))
                    j = i + 1
                    combined = stripped_nc
                    while j < len(lines_j) and j < i + 4:
                        nl = lines_j[j].strip()
                        nl_nc = re.sub(r'/\*.*?\*/', '', nl).strip()
                        if nl_nc == '' or nl_nc.startswith('//') or nl_nc.startswith('/*') or nl_nc.startswith('*') or nl_nc.startswith('@'):
                            j += 1; continue
                        combined += ' ' + nl_nc
                        if 'extends' in combined:
                            clean_combined = _strip_generics(combined)
                            ext_match = re.search(r'\bclass\s+(\w+)(?:\s+extends\s+([\w.]+))?', clean_combined)
                            if ext_match and ext_match.group(2):
                                extends_graph[class_name] = ext_match.group(2).split(".")[-1]
                                break
                            # 已见 extends 关键字，但父类名可能还在下一行，继续前瞻
                        # 遇到左花括号、其他类型声明或 implements 就停止
                        if re.search(r'\{|\b(?:class|interface|enum|record)\b|\bimplements\b', nl_nc):
                            break
                        j += 1
            i += 1

    # 2. Python 侧：登记类声明与首个父类
    for f in (file_list_py if file_list_py is not None else _rglob_filtered(root, "*.py")):
        try:
            content = f.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue

        # 剥离 # 注释，避免注释与 docstring 里的文本被误判为代码。
        # 尽力而为：多行字符串内部的 # 无法完全正确处理。
        # 启发式：只有前导空白或行首的 # 才当作注释起始，
        # 以减少 x="#foo" 这类字符串字面量造成的误判。
        cleaned_py = []
        for raw_line in content.split('\n'):
            stripped_ln = raw_line.strip()
            if stripped_ln.startswith('#'):
                cleaned_py.append('')
                continue
            comment_pos = raw_line.find(' #')
            if comment_pos != -1:
                raw_line = raw_line[:comment_pos]
            cleaned_py.append(raw_line)
        content = '\n'.join(cleaned_py)

        for class_start in re.finditer(r'class\s+(\w+)\s*\(', content):
            class_name = class_start.group(1)
            paren_pos = class_start.end() - 1  # 左括号位置
            close_pos = _find_matching_paren(content, paren_pos)
            if close_pos == -1:
                continue
            parents_raw = content[class_start.end():close_pos]
            parents = [p.strip() for p in _split_comma_aware(parents_raw) if p.strip()]
            if parents:
                first_parent = re.sub(r'\[.*\]', '', parents[0]).strip()  # 首个父类即主基类，去掉下标参数
                class_files[class_name] = str(f.relative_to(root))
                extends_graph[class_name] = first_parent.split(".")[-1]

    # 3. 计算继承深度：遇到环形继承返回 -1，使其永远不会被判成"继承过深"
    def calc_depth(cls_name: str, visiting: set = None) -> int:
        if visiting is None:
            visiting = set()
        if cls_name in visiting:
            return -1  # 检测到环，不上报
        visiting.add(cls_name)
        parent = extends_graph.get(cls_name)
        if parent is None:
            return 0
        child_depth = calc_depth(parent, visiting)
        if child_depth == -1:
            return -1  # 向上传递环标记
        return 1 + child_depth

    # 4. 第二遍：报告深度达到 max_depth 的类（跳过环形链）
    for class_name, file_path in class_files.items():
        depth = calc_depth(class_name)
        if depth >= max_depth and depth != -1:
            # 拼出继承链文本，便于人工核对
            chain = [class_name]
            current = class_name
            visited_chain = {class_name}
            while current in extends_graph:
                parent = extends_graph[current]
                if parent in visited_chain:
                    break
                chain.append(parent)
                visited_chain.add(parent)
                current = parent
            results.append({
                "type": "deep_inheritance",
                "severity": "info",
                "file": file_path,
                "depth": depth,
                "chain": " -> ".join(chain),
                "message": f"Class '{class_name}' in {file_path} has inheritance depth {depth} (chain: {' -> '.join(chain)}). Verify this hierarchy was explicitly requested."
            })

    return results


def find_pass_through_methods(root: Path, file_list: list[Path] | None = None) -> list[dict]:
    """查找只做一次委托、几乎没有自身逻辑的方法（转发包装）。

    Args:
        root: 项目根目录，用于生成相对路径。
        file_list: 已选定的 Java 文件；为 None 时自行扫描 root。

    Returns:
        pass_through 类型的问题列表。
    """
    results = []
    for f in (file_list if file_list is not None else _rglob_filtered(root, "*.java")):
        try:
            content = f.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue

        # 1. 匹配 Java 方法签名，允许方法上方有若干注解
        # 1.1 逐行扫描：见到方法签名就转去检查它的方法体
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # 先剥离行内块注释，否则 `/* ... */ 代码` 会被当成注释行跳过
            line = re.sub(r'/\*.*?\*/', '', line).strip()
            # 跳过纯注释行
            if line.startswith('//') or line.startswith('/*') or line.startswith('*'):
                i += 1
                continue
            # 跳过纯注解行：同一行里没有任何方法特征关键字。
            # 下方把修饰符改成了可选，因此这里也必须放行"只有返回类型+方法名、
            # 没有修饰符"的行。
            if line.startswith('@') and not re.search(r'\b(public|private|protected|default|static|void|int|boolean|long|double|float|byte|short|char|String)\b', line):
                i += 1
                continue
            m = re.search(
                r'(?:(?:public|private|protected|default)\s+)?'  # 访问修饰符或 interface default（可选——包级私有方法没有修饰符）
                r'(?:static\s+)?'
                r'(?:<[^<>]*>\s+)?'            # 可选的泛型类型参数（简化处理，不支持嵌套泛型）
                r'(.+)'                     # 返回类型（贪婪匹配，可含带空格的泛型）
                r'\s+(\w+)\s*'               # 方法名
                r'\(([^)]*)\)',               # 形参列表
                line
            )
            if not m:
                i += 1
                continue
            method_name = m.group(2)
            # 2. 收集方法体（用花括号配对粗略计数）
            brace_count = 0
            open_pos = None
            # 启发式：只有前导空格的 // 才当作注释起始，
            # 以减少字符串里 URL 造成的误判。
            comment_pos = line.find(' //')
            clean = line[:comment_pos] if comment_pos != -1 else line
            if '{' in clean:
                brace_count = clean.count('{') - clean.count('}')
                open_pos = clean.index('{')
            else:
                # 2.1 另起一行的 Allman 风格左花括号：向后找若干行
                j = i + 1
                while j < len(lines):
                    ahead = lines[j].strip()
                    # 先剥离行内块注释
                    ahead_nc = re.sub(r'/\*.*?\*/', '', ahead).strip()
                    if ahead_nc == '' or ahead_nc.startswith('//') or ahead_nc.startswith('/*') or ahead_nc.startswith('*') or ahead_nc.startswith('@'):
                        j += 1
                        continue
                    comment_pos_a = ahead.find(' //')
                    clean_ahead = ahead[:comment_pos_a] if comment_pos_a != -1 else ahead
                    if '{' in clean_ahead:
                        clean = clean_ahead
                        open_pos = clean_ahead.index('{')
                        brace_count = clean_ahead.count('{') - clean_ahead.count('}')
                        line = ahead
                        i = j
                        break
                    else:
                        break  # 非空、非注释行却没有 '{'，无法解析
                if open_pos is None:
                    i += 1
                    continue
            if '}' in clean[open_pos:]:
                # 单行方法体：public void foo() { return bar.baz(); }
                body_content = clean[open_pos+1:clean.rindex('}')].strip()
                body_lines = [body_content] if body_content else []
            else:
                body_lines = [line[open_pos+1:]]
            i += 1
            while i < len(lines) and brace_count > 0:
                body_lines.append(lines[i])
                brace_count += lines[i].count('{') - lines[i].count('}')
                i += 1
            body = '\n'.join(body_lines).strip()
            stripped = [l.strip() for l in body.split('\n')
                        if l.strip() and not l.strip().startswith('//') and l.strip() not in ('}', '};')]
            # 3. 方法体只剩一条 return 委托语句时判为转发包装
            if len(stripped) == 1 and re.match(r'^return\s+(?:await\s+)?(?:new\s+)?\w+(?:\.\w+)+\(', stripped[0]):
                results.append({
                    "type": "pass_through",
                    "severity": "info",
                    "file": str(f.relative_to(root)),
                    "method": method_name,
                    "body": stripped[0],
                    "message": f"Method '{method_name}' in {f.relative_to(root)} appears to be a one-line pass-through. Consider inlining at the call site."
                })

    return results


# ---------------------------------------------------------------------------
# Python 专属检测器
# ---------------------------------------------------------------------------

def find_python_abc_smell(root: Path, file_list: list[Path] | None = None) -> list[dict]:
    """查找项目中至多只有一个具体子类的 ABC。

    只有一个实现的 ABC 就是 Java 单实现接口的 Python 版本，抽象很可能是多余的。

    Args:
        root: 项目根目录，用于生成相对路径。
        file_list: 已选定的 Python 文件；为 None 时自行扫描 root。

    Returns:
        python_single_impl_abc 类型的问题列表。
    """
    results = []
    abc_classes = {}          # ABC 名 -> 文件路径
    abc_subclasses = defaultdict(set)  # ABC 名 -> 子类文件路径集合

    # 1. 扫描每个文件，收集 ABC 定义与其子类
    for f in (file_list if file_list is not None else _rglob_filtered(root, "*.py")):
        try:
            content = f.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue

        rel = str(f.relative_to(root))

        # 1.1 抹掉纯注释行，避免 `# class Foo(ABC):` 被当成真实类定义
        content_no_comments = '\n'.join(
            '' if ln.strip().startswith('#') else ln
            for ln in content.split('\n')
        )

        # 1.2 识别 ABC 定义：class X(ABC) 或 class X(metaclass=ABCMeta)
        for abc_match in re.finditer(
            r'^class\s+(\w+)\s*\((?:.*?\bABC\b.*?|.*?metaclass\s*=\s*(?:abc\.)?ABCMeta.*?)\)',
            content_no_comments,
            re.MULTILINE
        ):
            abc_classes[abc_match.group(1)] = rel

        # 1.3 识别子类：用括号深度匹配处理类型标注里的嵌套括号，
        #     如 class Foo(Generic[Dict[str, int]])。
        #     在副本上剥离 # 注释，避免注释里的文本被当成类声明。
        #     启发式：只有前导空白的 # 才当作注释起始。
        content_cleaned = '\n'.join(
            (ln[:ln.find(' #')] if ln.find(' #') != -1 and not ln.strip().startswith('#') else
             ('' if ln.strip().startswith('#') else ln))
            for ln in content.split('\n')
        )
        for class_start in re.finditer(r'class\s+(\w+)\s*\(', content_cleaned):
            class_name = class_start.group(1)
            paren_pos = class_start.end() - 1  # 左括号位置
            close_pos = _find_matching_paren(content_cleaned, paren_pos)
            if close_pos == -1:
                continue
            parents_raw = content_cleaned[class_start.end():close_pos]
            parents = []
            for p in _split_comma_aware(parents_raw):
                p = p.strip()
                if not p:
                    continue
                # 剥离行内注释（如 `BaseClass  # 说明` -> `BaseClass`）
                comment_idx = p.find('#')
                if comment_idx != -1:
                    p = p[:comment_idx].strip()
                if p:
                    parents.append(p)
            for parent in parents:
                if parent != class_name:  # 跳过自引用
                    # 去掉泛型类型实参（如 Generic[T] -> Generic）
                    parent_clean = re.sub(r'\[.*\]', '', parent).strip()
                    simple_parent = parent_clean.split('.')[-1]
                    abc_subclasses[simple_parent].add(rel)

    # 2. 子类不超过一个时判为坏味道
    for abc_name, file_path in abc_classes.items():
        subs = abc_subclasses.get(abc_name, set())
        if len(subs) <= 1:
            results.append({
                "type": "python_single_impl_abc",
                "severity": "warning",
                "abc": file_path,
                "subclasses": sorted(subs),
                "message": f"ABC '{abc_name}' in {file_path} has only {len(subs)} concrete subclass(es). Consider using a plain class unless multiple implementations are needed."
            })

    return results


def _find_matching_paren(line: str, start: int) -> int:
    """返回 `start` 处左括号 ' 所匹配的右括号 ')' 下标，找不到时返回 -1。

    对字符串字面量敏感：会跳过引号内的字符，因此默认值里的括号
    （如 x="default(val)"）不会导致提前返回。

    Args:
        line: 待扫描的文本，可以是多行拼接后的签名。
        start: 左括号 '(' 的下标。

    Returns:
        匹配的右括号下标；没有匹配时返回 -1。
    """
    depth = 0
    idx = start
    while idx < len(line):
        ch = line[idx]
        # 1. 跳过字符串字面量
        if ch in ("'", '"'):
            # Triple quote?
            if idx + 2 < len(line) and line[idx:idx+3] in ('"""', "'''"):
                quote = line[idx:idx+3]
                idx += 3
                while idx + 2 < len(line) and line[idx:idx+3] != quote:
                    idx += 1
                idx += 3
                continue
            else:
                # 单字符引号：跳到配对的结束引号，反斜杠转义要一并跳过
                quote = ch
                idx += 1
                while idx < len(line):
                    if line[idx] == '\\' and idx + 1 < len(line):
                        idx += 2  # 跳过转义字符，具体是什么不重要
                    elif line[idx] == quote:
                        break
                    else:
                        idx += 1
                idx += 1
                continue
        # 2. 字符串之外按括号深度配对
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return idx
        idx += 1
    return -1


def find_python_pass_through(root: Path, file_list: list[Path] | None = None) -> list[dict]:
    """查找只做一次委托、没有自身逻辑的 Python 函数/方法。

    Args:
        root: 项目根目录，用于生成相对路径。
        file_list: 已选定的 Python 文件；为 None 时自行扫描 root。

    Returns:
        python_pass_through 类型的问题列表。
    """
    results = []
    for f in (file_list if file_list is not None else _rglob_filtered(root, "*.py")):
        try:
            content = f.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue

        rel = str(f.relative_to(root))
        lines = content.split('\n')

        # 1. 定位候选函数：def name(args): 后紧跟一行 return other.method(args)
        for i, line in enumerate(lines):
            # 1.1 用括号深度匹配处理默认值里的嵌套调用
            m = re.search(r'^\s*(?:async\s+)?def\s+(\w+)\s*(?:\[[^\]]*\])?\s*\(', line)
            if not m:
                continue
            # 1.2 找出形参列表的右括号：签名跨行时就逐行累加直到找到 ')'。
            paren_start = m.end() - 1  # 左括号位置
            close_idx = _find_matching_paren(line, paren_start)
            sig_end_i = i  # 签名闭合所在的物理行下标
            if close_idx == -1:
                # 1.2.1 跨行签名：逐行累加直到出现闭合的右括号
                sig_lines = [line]
                for k in range(i + 1, len(lines)):
                    # 拼接前先剥离 # 注释，避免注释里的 ')'（如 `x: int  # 默认(val)`）
                    # 让 _find_matching_paren 提前返回。
                    # 启发式：只有前导空白的 # 才当作注释起始。
                    ln = lines[k]
                    comment_pos = ln.find(' #')
                    if comment_pos != -1:
                        ln = ln[:comment_pos]
                    sig_lines.append(ln)
                    combined = '\n'.join(sig_lines)
                    close_idx = _find_matching_paren(combined, paren_start)
                    if close_idx != -1:
                        sig_end_i = k
                        break
                if close_idx == -1:
                    continue  # 签名残缺，跳过
                sig = '\n'.join(sig_lines)
            else:
                sig = line
            # 2. 校验右括号之后只剩返回类型标注和冒号
            rest = sig[close_idx+1:].strip()
            if rest and not rest.startswith(':') and not rest.startswith('->'):
                # rest 非空且既不是 ':' 也不是 '->' 收尾，签名残缺
                continue
            func_name = m.group(1)
            def_indent = len(line) - len(line.lstrip())
            # 3. 闭合括号与冒号同行时先检查单行函数体
            # def foo(x): <body> 或 def foo(x) -> T: <body>
            after_colon = ""
            if rest.startswith(':'):
                after_colon = rest[1:].strip()
            elif rest.startswith('->'):
                m_rtype = re.match(r'->\s*(.+):\s*(.*)', rest)
                if m_rtype:
                    after_colon = m_rtype.group(2).strip()
            if after_colon:
                # 剥离行内注释，使 `return bar.baz()  # 说明` 能被识别为代码
                comment_idx = after_colon.find('#')
                if comment_idx != -1:
                    maybe_code = after_colon[:comment_idx].strip()
                else:
                    maybe_code = after_colon
                if maybe_code:
                    if re.match(r'^return\s+(?:await\s+)?\w+(?:\.\w+)+\(', maybe_code):
                        results.append({
                            "type": "python_pass_through",
                            "severity": "info",
                            "file": rel,
                            "method": func_name,
                            "body": maybe_code,
                            "message": f"Function '{func_name}' in {rel} is a one-line pass-through. Consider inlining at the call site."
                        })
                    continue  # 单行函数，方法体已检查完
                # after_colon 全是注释，继续往下收集方法体
            # 4. 逐行收集方法体直到 dedent；跟踪三引号状态，避免多行字符串里
            #    未缩进的 """ 被误判成 dedent。
            #    必须跟踪是哪一种引号开启的区域：正文里含 ''' 的 """ docstring
            #    不能被内嵌的单引号变体提前闭合，反之亦然。
            body_lines = []
            triple_type = None  # None | '"""' | "'''"
            j = sig_end_i + 1
            while j < len(lines):
                line_j = lines[j]
                stripped_j = line_j.strip()
                if stripped_j == '':
                    j += 1
                    continue  # 跳过函数体内的空行
                # 精确统计三引号边界（不把连续 4 个以上的引号算进去）
                dq_count = len(re.findall(r'(?<!")"""(?!")', stripped_j))
                sq_count = len(re.findall(r"(?<!')'''(?!')", stripped_j))
                if triple_type is None:
                    # 4.1 在三引号字符串之外：任意一种标记出现奇数次即开启对应区域
                    if dq_count % 2 == 1:
                        triple_type = '"""'
                        j += 1
                        continue
                    if sq_count % 2 == 1:
                        triple_type = "'''"
                        j += 1
                        continue
                    # 4.2 单行三引号字符串（偶数次：开闭标记在同一行，如 """docstring."""），
                    #     跳过它以免 docstring 混进 body_lines，
                    #     把本可识别的单语句转发方法变成漏报。
                    if stripped_j.startswith(('"""', "'''", 'r"""', "r'''", 'f"""', "f'''", 'b"""', "b'''", 'u"""', "u'''", 'rb"""', "rb'''")):
                        j += 1
                        continue
                else:
                    # 4.3 在三引号字符串之内：只有同类引号才能闭合它，
                    #     另一种只是正文内容
                    if triple_type == '"""':
                        if dq_count % 2 == 1:
                            triple_type = None
                    else:  # triple_type == "'''"
                        if sq_count % 2 == 1:
                            triple_type = None
                    j += 1
                    continue
                current_indent = len(line_j) - len(line_j.lstrip())
                if current_indent <= def_indent and stripped_j:
                    break  # 已 dedent，后面是顶层或同级的语句
                if stripped_j.startswith('@') and current_indent <= def_indent:
                    break  # 同级方法上的装饰器，不属于当前嵌套作用域
                body_lines.append(line_j.strip())
                j += 1
            # 5. 过滤注释和空行；先剥行内注释，
            #    使 `return foo.bar()  # 委托` 能被识别为代码
            stripped_body = []
            for l in body_lines:
                if not l:
                    continue
                comment_pos = l.find(' #')
                if comment_pos != -1:
                    l = l[:comment_pos].strip()
                if l and not l.startswith('#'):
                    stripped_body.append(l)
            code_lines = stripped_body
            # 6. 方法体只剩一条 return 委托语句时判为转发包装
            if len(code_lines) == 1 and re.match(r'^return\s+(?:await\s+)?\w+(?:\.\w+)+\(', code_lines[0]):
                results.append({
                    "type": "python_pass_through",
                    "severity": "info",
                    "file": rel,
                    "method": func_name,
                    "body": code_lines[0],
                    "message": f"Function '{func_name}' in {rel} is a one-line pass-through. Consider inlining at the call site."
                })

    return results


# ---------------------------------------------------------------------------
# 报告输出
# ---------------------------------------------------------------------------

def report_text(smells: list[dict], unreadable: list[dict] | None = None) -> str:
    """生成按严重程度分组的可读报告。

    Args:
        smells: 检查器发现的问题。

    Returns:
        用于终端输出的报告。
    """
    lines: list[str] = []

    # 1. 无法解码的文件排在最前：它们根本没被检查，不是"没有问题"。
    if unreadable:
        lines.append(f"Could not read {len(unreadable)} file(s); they were NOT checked:\n")
        for item in unreadable:
            lines.append(f"  [UNREADABLE] {item['file']}: {item['reason']}")
        lines.append("")

    # 2. 再按严重程度报告坏味道，使阻断级别的发现优先可见。
    if smells:
        lines.append(f"Found {len(smells)} potential abstraction smell(s):\n")
        by_severity = defaultdict(list)
        for s in smells:
            by_severity[s["severity"]].append(s)
        # 保持各组内部顺序，方便人工对照同一次扫描结果。
        for severity in ("warning", "info"):
            items = by_severity.get(severity, [])
            if items:
                lines.append(f"  [{severity.upper()}]")
                for item in items:
                    lines.append(f"    - {item['message']}")
    elif not unreadable:
        lines.append("No abstraction smells found. Code looks direct and readable.")
    return "\n".join(lines) + "\n"


def report_json(smells: list[dict], unreadable: list[dict] | None = None) -> str:
    """生成包含问题列表与数量的 JSON。

    ``count`` 仍然只表示坏味道的数量；无法解码的文件单独放在
    ``unreadable`` 里，因为它们不是坏味道，而是检查本身没能完成。

    Args:
        smells: 检查器发现的问题。
        unreadable: 因不是 UTF-8 而无法检查的源文件。

    Returns:
        JSON 字符串。
    """
    return json.dumps({
        "smells": smells,
        "count": len(smells),
        "unreadable": unreadable or [],
    }, indent=2)


def find_unreadable(files: list[Path], root: Path) -> list[dict]:
    """找出无法按 UTF-8 解码的源文件。

    规范要求源文件一律使用 UTF-8。静默跳过会让调用方以为这个文件检查过了，
    而它其实从未进入分析 —— 与 check_comments.py 的 read-error 保持一致，
    这里同样把它当作一次失败的检查而不是"没有问题"。

    Args:
        files: 待检查的源文件列表。
        root: 计算相对路径用的根目录。

    Returns:
        每项含 ``file`` 与 ``reason``；全部可解码时返回空列表。
    """
    out: list[dict] = []
    for f in files:
        try:
            f.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            out.append({
                "file": f.relative_to(root).as_posix(),
                "reason": f"not UTF-8 ({exc.reason} at byte {exc.start}); re-save it as UTF-8",
            })
        except OSError as exc:
            out.append({
                "file": f.relative_to(root).as_posix(),
                "reason": f"cannot read ({exc.strerror or exc})",
            })
    return out


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def _related(smell: dict, selected: set[str]) -> bool:
    """按涉及文件限制报告，分析阶段仍保留完整上下文。"""
    paths = [smell.get(key) for key in ("file", "interface", "abc")]
    for key in ("files", "implementations", "subclasses"):
        paths.extend(smell.get(key, []))
    return any(Path(p).as_posix() in selected for p in paths if p)


def _scan(root: Path, args, selected: set[str] | None) -> tuple[list[dict], list[dict]]:
    """读取选定语言的完整上下文后限制报告范围。

    Returns:
        ``(坏味道, 无法解码的文件)``。后者单独返回是因为"没检查"和
        "检查后没发现问题"对调用方是完全不同的两件事。
    """
    # 1. 跨文件关系必须读取全部实现，避免将未修改的实现误判为不存在。
    java = _rglob_filtered(root, "*.java") if args.lang != "python" else []
    python = _rglob_filtered(root, "*.py") if args.lang != "java" else []
    language_files = {p.relative_to(root).as_posix() for p in java + python}
    unreadable = find_unreadable(java + python, root)
    smells = [s for s in find_suspect_packages(root, args.min_package_files)
              if _related(s, language_files)]
    smells.extend(find_deep_inheritance(root, args.max_depth, java, python))
    if java:
        smells.extend(find_single_impl_interfaces(root, java))
        smells.extend(find_pass_through_methods(root, java))
    if python:
        smells.extend(find_python_abc_smell(root, python))
        smells.extend(find_python_pass_through(root, python))
    # 2. 报告仅涉及本次选择的文件，保留完整分析产生的跨文件关系。
    #    unreadable 必须一起收窄：仓库里任何一个历史 GBK 文件都不该阻断
    #    与它无关的提交，否则这个检查在存量代码库上直接不可用。
    if selected is None:
        return smells, unreadable
    scope = {s.replace("\\", "/") for s in selected}
    return ([s for s in smells if _related(s, selected)],
            [u for u in unreadable if u["file"] in scope])


def _git(root: Path, *args: str) -> bytes:
    """以参数列表调用 Git，保留 NUL 分隔路径和源文件字节。"""
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def _snapshot_index(root: Path, destination: Path) -> set[str]:
    """复制 Git index 中的源文件，返回已暂存的变更路径。"""
    # 1. 使用 NUL 分隔处理中文、空格和换行路径，不读取工作区源文件。
    changed = _git(root, "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR")
    selected = {p.decode("utf-8") for p in changed.split(b"\0") if p}
    entries = _git(root, "ls-files", "--stage", "-z")
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        mode, oid, stage = metadata.split()
        relative = Path(raw_path.decode("utf-8"))
        if relative.suffix not in (".java", ".py"):
            continue
        if stage != b"0":
            raise ValueError(f"暂存区存在未解决冲突：{relative}")
        if mode not in (b"100644", b"100755"):
            continue
        # 2. 快照只写入临时目录中的普通源文件，拒绝逃逸路径和链接。
        target = (destination / relative).resolve()
        if not target.is_relative_to(destination.resolve()):
            raise ValueError(f"无效的 Git 路径：{relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_git(root, "cat-file", "blob", oid.decode("ascii")))
    return selected


def main():
    """解析检查范围并输出结果，仅在达到显式阈值时阻断。"""
    # 1. 区分报告范围与分析上下文，默认只报告而不阻止提交。
    parser = argparse.ArgumentParser(description="Check for abstraction smells")
    parser.add_argument("root", type=Path, help="Project root directory")
    parser.add_argument("--lang", choices=("java", "python", "auto"), default="auto")
    parser.add_argument("--max-depth", type=int, default=2,
                        help="Inheritance edge count at which to report (default: 2)")
    parser.add_argument("--min-package-files", type=int, default=2)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on", choices=("none", "warning", "info"), default="none")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--files", nargs="?", const="-", default=None,
                       help="Newline-separated relative paths; omit value to read stdin")
    scope.add_argument("--staged", action="store_true", help="Analyze Git index contents")
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        parser.error(f"Not a directory: {root}")
    if args.max_depth < 1 or args.min_package_files < 0:
        parser.error("Depth must be positive and package size must be non-negative")

    # 2. 暂存模式建立完整源文件快照，普通模式读取当前工作区。
    if args.staged:
        root = Path(_git(root, "rev-parse", "--show-toplevel").decode("utf-8").strip())
        with tempfile.TemporaryDirectory(prefix="readability-index-") as temp:
            snapshot = Path(temp)
            selected = _snapshot_index(root, snapshot)
            smells, unreadable = _scan(snapshot, args, selected)
    else:
        selected = None
        if args.files is not None:
            raw = sys.stdin.read() if args.files == "-" else args.files
            selected = set()
            for line in raw.splitlines():
                if not line:
                    continue
                candidate = (root / line).resolve()
                if not candidate.is_relative_to(root) or not candidate.is_file():
                    parser.error(f"Invalid source path: {line}")
                selected.add(candidate.relative_to(root).as_posix())
        smells, unreadable = _scan(root, args, selected)

    # 3. 输出与退出策略分开，info 不会触发 warning 级阻断。
    print(report_json(smells, unreadable) if args.json else report_text(smells, unreadable))
    blocked = args.fail_on != "none" and any(
        args.fail_on == "info" or s["severity"] == "warning" for s in smells)
    # 无法解码的文件一律失败：它们根本没被检查，不能算"没有问题"。
    # 与 check_comments.py 的 read-error 保持同一口径。
    sys.exit(2 if unreadable else (1 if blocked else 0))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: abstraction smell checker failed: {e}", file=sys.stderr)
        sys.exit(2)
