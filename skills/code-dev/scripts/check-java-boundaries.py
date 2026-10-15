#!/usr/bin/env python3
"""检查 Java/Spring 边界及源码乱码；WARNING 是需核对的线索，不是运行验证。"""

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import subprocess
import tempfile

from check_comments import SKIP_DIRS, _split_java_views


SUFFIXES = {".java", ".py", ".ts", ".tsx", ".js", ".jsx", ".cs", ".cpp", ".c",
            ".h", ".hpp", ".sql", ".yml", ".yaml", ".xml", ".json", ".properties"}
METHOD = re.compile(
    r"(?m)^[ \t]*(?:(?:public|protected|private|static|final|synchronized|default)\s+)*"
    r"[\w.$<>?,\[\]]+\s+(?P<name>\w+)\s*\([^;{}()]*\)\s*(?:throws\s+[\w.,\s]+)?\{")
FIELD = re.compile(
    r"\b(?:private|protected|public)\s+(?:(?:static|final|volatile)\s+)*"
    r"(?P<type>[\w.$<>?,\[\]]+)\s+(?P<name>\w+)\s*=\s*[^;]+;")
TUNABLE = re.compile(r"timeout|backoff|retries|retry|concurrency|batch.?size|batch.?limit|"
                     r"scan.?limit|candidate.?limit|threshold|interval|page.?size|max.?redirect|"
                     r"(?:base|api|service|endpoint).?url|endpoint|storage.?root|file.?path|"
                     r"password|secret|api.?key", re.I)


@dataclass
class Finding:
    """保存定位、严重程度与不含配置值的诊断。

    Attributes:
        file: 相对扫描根目录的路径。
        line: 从 1 开始的行号。
        severity: ERROR 或 WARNING。
        code: 稳定诊断标识，供自动门禁分类。
        message: 不包含配置值或源代码片段的说明。
    """

    file: str
    line: int
    severity: str
    code: str
    message: str


@dataclass
class JavaSource:
    """保存原文与等长去噪视图，字符串和注释不参与调用识别。

    Attributes:
        path: 相对扫描根目录的路径。
        raw: 以统一换行读取的原文，仅用于定位绑定声明和字面量。
        code: 保留位置、去掉注释和字符串内容的代码视图。
    """

    path: str
    raw: str
    code: str


def matching_brace(code, opening):
    """返回已去噪代码中匹配的右花括号位置。

    Args:
        code: 已去掉字符串和注释的代码。
        opening: 左花括号的字符偏移。

    Returns:
        右花括号偏移；没有闭合时返回代码长度，后续仍需编译验证。
    """
    depth = 0
    for index in range(opening, len(code)):
        depth += (code[index] == "{") - (code[index] == "}")
        if depth == 0:
            return index
    return len(code)


def methods(source):
    """收集具备方法体的方法和紧邻注解，不解析继承及重载类型。

    Args:
        source: 原文与去噪视图必须保持相同字符位置的源码。

    Returns:
        包含名称、声明偏移、方法体及注解视图的候选方法列表。
    """
    result = []
    for match in METHOD.finditer(source.code):
        opening = match.end() - 1
        previous = max(source.code.rfind(";", 0, match.start()),
                       source.code.rfind("}", 0, match.start()),
                       source.code.rfind("{", 0, match.start())) + 1
        result.append({"name": match["name"], "start": match.start(),
                       "body": source.code[opening + 1:matching_brace(source.code, opening)],
                       "annotations": source.code[previous:match.start()],
                       "raw_annotations": source.raw[previous:match.start()]})
    return result


def yaml_keys(raw):
    """提取常规缩进 YAML 的有值叶子键；不把它当作完整 YAML 加载器。

    Args:
        raw: application YAML 的原始文本，允许多个文档段落。

    Returns:
        各段落有值叶子键的并集，不代表任何 profile 已实际加载。
    """
    stack = []
    keys = set()
    for line in raw.splitlines():
        # 1. 每个环境段落重新确定层级，避免继承上一段的键路径。
        if line.strip() == "---":
            stack = []
        match = re.match(r"^( *)([\w-]+):(?:\s+(.*))?$", line)
        if not match:
            continue
        # 2. 用缩进还原当前叶子键，仅记录显式有值的配置。
        indent, name, value = len(match[1]), match[2], match[3]
        while stack and stack[-1][0] >= indent:
            stack.pop()
        key = ".".join([item[1] for item in stack] + [name])
        if value and not value.startswith("#"):
            keys.add(key)
        else:
            stack.append((indent, name))
    return keys


def analyze(sources, config_keys):
    """生成事务、默认值、硬编码与集成装配线索，不输出秘密值。

    Args:
        sources: 同一扫描范围内的生产及测试源码；测试不算生产消费者。
        config_keys: 配置文件声明的叶子键，用于识别第二套 Java 默认值。

    Returns:
        需要人工确认或提供豁免依据的 WARNING 列表。
    """
    findings = []

    def report(source, offset, code, message):
        findings.append(Finding(source.path, source.code.count("\n", 0, offset) + 1,
                                "WARNING", code, message))

    # 1. 先按每个顶层源码文件检查局部调用及配置声明。
    for source in sources:
        if "/test/" in "/" + source.path or "/tests/" in "/" + source.path:
            continue
        entries = methods(source)
        targets = {entry["name"] for entry in entries
                   if re.search(r"@(?:[\w.]+\.)?Transactional\b", entry["annotations"])}
        for caller in entries:
            caller_transaction = re.search(r"@(?:[\w.]+\.)?Transactional\b", caller["annotations"])
            for target in targets:
                call = re.search(r"(?<![\w$.])(?:this\s*\.\s*)?" + re.escape(target) + r"\s*\(", caller["body"])
                reference = re.search(r"\bthis\s*::\s*" + re.escape(target) + r"\b", caller["body"])
                target_annotations = next(entry["annotations"] for entry in entries if entry["name"] == target)
                independent_boundary = re.search(r"REQUIRES_NEW|NESTED|NOT_SUPPORTED|NEVER", target_annotations)
                if (call or reference) and (not caller_transaction or independent_boundary):
                    report(source, caller["start"], "transaction-self-invocation",
                           f"`{caller['name']}` 在同类内调用事务方法 `{target}`；目标注解不会经过代理，核对调用链及事务边界")

        binding = re.search(r"@(?:[\w.]+\.)?ConfigurationProperties\s*\(", source.code)
        annotation_raw = source.raw[binding.start():source.code.find(")", binding.end()) + 1] if binding else ""
        prefix = re.search(r'(?:prefix\s*=\s*|value\s*=\s*|\(\s*)"([\w.-]+)"', annotation_raw)
        is_config = bool(prefix)
        for field in FIELD.finditer(source.code):
            name = field["name"]
            raw_field = source.raw[field.start():field.end()]
            if is_config:
                kebab = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", name).lower()
                key = prefix[1] + "." + kebab
                if key in config_keys:
                    report(source, field.start(), "duplicate-config-default",
                           f"`{key}` 同时在配置文件和 Java 字段初始化中设置；应由配置文件统一维护默认值")
            elif TUNABLE.search(name) and not re.search(r"(?:STATUS|COLUMN|FLAG|PREFIX|VERSION)", name):
                initializer = raw_field.split("=", 1)[1].rstrip("; ")
                if re.search(r'\d|"[^"\n]+"', initializer) and not re.search(r"\b\w*(?:properties|config)\s*\.", initializer, re.I):
                    report(source, field.start(), "hardcoded-tunable",
                           f"字段 `{name}` 疑似可调运行参数，检查是否应进入统一配置；协议常量需给出豁免依据")

        # 字面量先通过去噪视图定位注解，再读取原文；不搜索注释里的示例。
        for annotation in re.finditer(r"@(?:[\w.]+\.)?Value\s*\(", source.code):
            raw_annotation = source.raw[annotation.start():source.raw.find(")", annotation.end()) + 1]
            if re.search(r"\$\{[^}]+:", raw_annotation):
                report(source, annotation.start(), "annotation-config-default",
                       "@Value 内包含第二套配置默认值，应移入框架配置文件")
        for call in re.finditer(r"\b(?:uri|baseUrl|create|getConnection)\s*\(\s*", source.code):
            # 去噪视图中的字面量为空格，原文位置保留；仅识别明确的地址字面量。
            raw_tail = source.raw[source.code.rfind("(", call.start(), call.end()) + 1:]
            if re.match(r'\s*"(?:https?://|jdbc:)', raw_tail):
                report(source, call.start(), "hardcoded-endpoint",
                       "客户端调用直接使用地址字面量，应从统一配置读取；诊断不输出地址或凭证")
        if not is_config:
            for call in re.finditer(r"\b(?:Duration\s*\.\s*of\w+|Thread\s*\.\s*sleep)\s*\(\s*\d", source.code):
                if any(field.start() <= call.start() < field.end() and TUNABLE.search(field["name"])
                       for field in FIELD.finditer(source.code)):
                    continue
                report(source, call.start(), "hardcoded-runtime-duration",
                       "业务代码直接使用固定时长，核对是否为需外置的超时、退避或频率")
        for annotation in re.finditer(r"@(?:[\w.]+\.)?(?:Scheduled|Retryable)\s*\([^)]*\b(?:fixedDelay|fixedRate|initialDelay|maxAttempts|delay|multiplier)\s*=\s*\d", source.code):
            report(source, annotation.start(), "hardcoded-runtime-annotation",
                   "调度或重试注解包含可调数字参数，应使用统一配置绑定")

    # 2. 按实际类型引用检查集成契约是否接入生产调用路径。
    for source in sources:
        if "/integration/" not in "/" + source.path or "/test/" in "/" + source.path:
            continue
        interface = re.search(r"\binterface\s+(\w+)\b", source.code)
        if interface is None:
            continue
        name = interface[1]
        provider = source.path.split("/integration/", 1)[1].split("/", 1)[0]
        implementation = any(re.search(r"\bimplements\s+[^{};]*\b" + re.escape(name) + r"\b", other.code)
                             for other in sources if "/test/" not in "/" + other.path)
        consumers = []
        for other in sources:
            if other.path == source.path or "/test/" in "/" + other.path or "/tests/" in "/" + other.path:
                continue
            # import、implements 和 Javadoc 不构成使用；字段、参数和显式装配才计入。
            code = re.sub(r"(?m)^\s*import\s+[^;]+;", "", other.code)
            code = re.sub(r"\bimplements\s+[^{};]+", "", code)
            if re.search(r"\b" + re.escape(name) + r"\b", code):
                consumers.append(other)
        if implementation and not consumers:
            report(source, interface.start(), "integration-not-wired",
                   f"集成接口 `{name}` 有实现但未发现生产类型使用；核对注入、Bean 装配或反射注册，测试引用不算业务接入")
            for other in sources:
                if re.search(r"\.service\." + re.escape(provider) + r"\b", other.code) and re.search(r"\b(?:WebClient|HttpClient|RestClient|RestTemplate)\b", other.code):
                    report(other, 0, "integration-bypass",
                           f"同领域已有 `{name}`，业务层却直接使用 HTTP 客户端且接口未接入，核对重复协议实现")
    return findings


def scan(root):
    """扫描源码与配置；读取失败和原文替换字符始终作为 ERROR。

    Args:
        root: 扫描目录或单个文件；单文件扫描不能证明跨文件装配情况。

    Returns:
        诊断列表及实际读取或尝试读取的受支持文件数量。
    """
    findings, sources, config_keys = [], [], set()
    files = [root] if root.is_file() else sorted(root.rglob("*"))
    count = 0
    # 1. 对受支持文件检查编码，并收集跨文件分析上下文。
    for path in files:
        if not path.is_file() or path.suffix not in SUFFIXES:
            continue
        relative = path.name if root.is_file() else path.relative_to(root).as_posix()
        if any(part in SKIP_DIRS for part in Path(relative).parts):
            continue
        count += 1
        try:
            raw = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            findings.append(Finding(relative, 1, "ERROR", "read-error", "无法按 UTF-8 读取文件，检查未完成"))
            continue
        for index, line in enumerate(raw.splitlines(), 1):
            if "\ufffd" in line:
                findings.append(Finding(relative, index, "ERROR", "replacement-character",
                                        "发现 U+FFFD 替换字符；恢复原文，故意使用该字符时写 Unicode 转义"))
        if path.suffix == ".java":
            code = "\n".join(_split_java_views(raw.splitlines())[0])
            sources.append(JavaSource(relative, raw, code))
        if path.suffix in (".yml", ".yaml") and path.name.startswith("application"):
            config_keys.update(yaml_keys(raw))
        if path.suffix == ".properties" and path.name.startswith("application"):
            config_keys.update(match[1] for match in re.finditer(r"(?m)^\s*([\w.-]+)\s*[=:]", raw))
    # 2. 用完整生产引用和配置键检查运行边界。
    findings.extend(analyze(sources, config_keys))
    return findings, count


def git(root, *args):
    """仅用于读取索引快照，不修改仓库。

    Args:
        root: Git 仓库内路径。
        args: 作为独立参数传入的只读 Git 子命令。

    Returns:
        未经编码转换的 Git 输出，保留索引原文。

    Raises:
        subprocess.CalledProcessError: Git 读取失败，交由入口返回检查失败状态。
    """
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True).stdout


def staged_scan(root):
    """分析完整索引作上下文，只报告已暂存变更涉及的文件。

    Args:
        root: Git 仓库内路径，不要求调用方当前位于仓库根目录。

    Returns:
        暂存变更文件的诊断和受支持文件数量，工作区修复不影响索引诊断。

    Raises:
        ValueError: 存在冲突阶段或快照路径逃逸，拒绝给出通过结论。
    """
    # 1. 确定索引中的变更范围，不读取工作区代替索引。
    root = Path(git(root, "rev-parse", "--show-toplevel").decode("utf-8").strip())
    changed = {name.decode("utf-8") for name in git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").split(b"\0") if name}
    # 2. 在隔离目录重建索引上下文，退出时由临时目录管理器回收。
    with tempfile.TemporaryDirectory(prefix="java-boundaries-") as directory:
        snapshot = Path(directory)
        for entry in git(root, "ls-files", "--stage", "-z").split(b"\0"):
            if not entry:
                continue
            metadata, raw_name = entry.split(b"\t", 1)
            mode, oid, stage = metadata.split()
            name = Path(raw_name.decode("utf-8"))
            if stage != b"0":
                raise ValueError("索引存在未解决冲突")
            if mode not in (b"100644", b"100755") or name.suffix not in SUFFIXES:
                continue
            target = (snapshot / name).resolve()
            if not target.is_relative_to(snapshot.resolve()):
                raise ValueError("索引路径超出快照范围")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(git(root, "cat-file", "blob", oid.decode("ascii")))
        # 3. 保留跨文件分析能力，只把本次暂存文件的发现交给门禁。
        findings, _ = scan(snapshot)
        selected = [finding for finding in findings if finding.file in changed]
        count = sum(Path(name).suffix in SUFFIXES for name in changed)
        return selected, count


def main():
    """输出人工核对线索并按严重程度设置退出码。

    Returns:
        0 表示未达阈值，1 表示被诊断阻断，2 表示检查失败或未匹配文件。
    """
    # 1. 默认阻断 WARNING，提交钩子可显式选择仅阻断 ERROR。
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on", choices=("error", "warning"), default="warning")
    args = parser.parse_args()
    # 2. 读取工作区或索引；读取失败不输出可能含秘密值的异常正文。
    try:
        findings, count = staged_scan(Path(args.root)) if args.staged else scan(Path(args.root))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"检查失败：{type(error).__name__}")
        return 2
    # 3. 输出结构化或文本诊断，再按实际覆盖数量和阈值返回状态。
    if args.json:
        print(json.dumps({"checked": count, "findings": [asdict(item) for item in findings]}, ensure_ascii=False))
    else:
        for item in findings:
            print(f"{item.file}:{item.line}: {item.severity} [{item.code}] {item.message}")
        print(f"检查 {count} 个文件，ERROR={sum(item.severity == 'ERROR' for item in findings)}，WARNING={sum(item.severity == 'WARNING' for item in findings)}")
    if not count:
        return 0 if args.staged else 2
    return int(any(item.severity == "ERROR" or args.fail_on == "warning" for item in findings))


if __name__ == "__main__":
    raise SystemExit(main())
