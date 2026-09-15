#!/usr/bin/env python3
"""
Check a Java/Python codebase for abstraction smells that violate
the readability-first-coding skill.

Smells detected:
  - Single-implementation interfaces (XxxService -> XxxServiceImpl)
    - Exempted when the implementation lives in an `impl/` subfolder (project
      convention — see references/java-guidelines.md)
  - Empty or single-class common/util/shared/base packages
  - Unnecessary inheritance chains (depth > 2)
  - Pass-through wrapper methods

Usage:
  python check-abstraction-smell.py <project-root> [--lang java|python] [--json]

Exit codes:
  0 - 未达到阻断阈值（默认只报告）
  1 - 达到 --fail-on 指定的阻断阈值
  2 - Error running the check
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
    """Remove generic type parameters including nested angle brackets.

    Handles cases like: class Foo<T extends Comparable<T>> extends Bar
    by iteratively stripping innermost <...> pairs until none remain.
    Also handles bounded generics: T extends Foo & Bar.
    """
    while True:
        # Require at least one word character between < >, and reject content
        # containing logical operators (&&, ||) which indicates a comparison
        # expression rather than a generic type parameter.
        cleaned = re.sub(r'<(?=[^\s>]*\w)(?![^<>]*(?:&&|\|\|))[^<>]*>', '', text)
        if cleaned == text:
            break
        text = cleaned
    return text


def _split_comma_aware(text: str) -> list[str]:
    """Split text by commas, respecting bracket nesting (angle, square, round).

    Handles cases like: Generic[T, U], Dict[str, int], List[Tuple[int, str]]
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
    """Recursively glob for files matching *pattern*, skipping well-known
    dependency / cache directories to avoid false positives and wasted work."""
    return [
        f for f in root.rglob(pattern)
        if not any(part in _DEPENDENCY_DIRS for part in f.relative_to(root).parts)
    ]


# ---------------------------------------------------------------------------
# Smell detectors
# ---------------------------------------------------------------------------

def find_single_impl_interfaces(root: Path, file_list: list[Path] | None = None) -> list[dict]:
    """Find interfaces that have exactly one implementation class."""
    results = []
    java_files = file_list if file_list is not None else _rglob_filtered(root, "*.java")
    interfaces = {}
    implementations = defaultdict(set)  # use set to deduplicate

    for f in java_files:
        try:
            content = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        # Detect interface and implementation declarations (line-by-line with
        # multi-line peek-ahead for 'class\n    implements' patterns; avoids
        # re.DOTALL false matches and comment/string false positives)
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # Strip inline block comments BEFORE skip checks so that
            # '/* comment */ class Foo ...' is not missed.
            line = re.sub(r'/\*.*?\*/', '', line).strip()
            # Skip comment-only and annotation-only lines
            if line.startswith('//') or line.startswith('/*') or line.startswith('*'):
                i += 1; continue
            # Skip annotation-only lines (no class/interface keyword on same line)
            if line.startswith('@') and not re.search(r'\b(class|interface)\b', line):
                i += 1; continue
            # Strip remaining single-line comments (// ...)
            line = re.sub(r'//.*$', '', line)

            # Detect interface declarations (exclude @interface annotation types;
            # the negative-lookbehind alone misses `public @interface Foo` because the
            # char before `interface` in that string is a space, not `@`.)
            if '@interface' not in line:
                iface_match = re.search(r'(?<!\w)interface\s+(\w+)', line)
                if iface_match:
                    interfaces[iface_match.group(1)] = str(f.relative_to(root))

            # Detect class/record/enum declarations that implement interfaces
            m = re.search(r'\b(?:class|record|enum)\s+(\w+)(?:(?!\b(?:class|record|enum|interface)\b).)*\bimplements\s+(.+)', line)
            if not m:
                # Peek ahead ≤2 lines for multi-line declarations
                class_decl = re.search(r'\b(?:class|record|enum)\s+(\w+)', line)
                if class_decl:
                    j = i + 1
                    combined = line
                    while j < len(lines) and j < i + 5:   # increased from 3 to 5 for multi-annotation classes
                        nl = lines[j].strip()
                        # Strip block comments first so '/* ... */ code' is not skipped
                        nl_nc = re.sub(r'/\*.*?\*/', '', nl).strip()
                        nl_nc = re.sub(r'//.*$', '', nl_nc).strip()
                        if nl_nc.startswith('/*') or nl_nc.startswith('*'):
                            j += 1; continue
                        if nl_nc.startswith('@'):
                            j += 1; continue
                        if nl_nc == '':
                            j += 1; continue   # skip blank lines instead of breaking
                        combined += ' ' + nl_nc
                        if 'implements' in nl_nc:
                            m = re.search(
                                r'\b(?:class|record|enum)\s+(\w+)(?:(?!\b(?:class|record|enum|interface)\b).)*\bimplements\s+(.+)',
                                combined
                            )
                            break
                        j += 1
                    # Skip past lines already consumed by the peek-ahead
                    if m:
                        i = j
            if m:
                iface_list_raw = re.split(r'\s*[{;]', m.group(2))[0]
                # Strip generics BEFORE splitting on commas so that commas
                # inside generic type parameters (e.g. Bar<Map<String, Object>>)
                # are not treated as interface-list separators.
                iface_list_raw = _strip_generics(iface_list_raw)
                for raw_name in iface_list_raw.split(','):
                    iface_name = raw_name.strip().split('.')[-1]  # simple name only
                    iface_name = iface_name.rstrip('>')  # strip residual '>'
                    if iface_name:
                        rel_path = str(f.relative_to(root))
                        implementations[iface_name].add(rel_path)
            i += 1

    for iface_name, impl_set in implementations.items():
        impl_count = len(impl_set)
        if impl_count == 1 and iface_name in interfaces:
            impl_paths = sorted(impl_set)
            # Exempt the interface + impl/ folder convention: when the project
            # adopts this layout (interface in parent package, implementation in
            # an `impl/` subfolder), the single implementation is project-mandated
            # convention, not unsolicited abstraction. See references/java-guidelines.md.
            if any("impl" in Path(p).parts for p in impl_paths):
                continue
            results.append({
                "type": "single_impl_interface",
                "severity": "warning",
                "interface": interfaces[iface_name],
                "implementations": impl_paths,
                "message": f"Interface '{iface_name}' has only 1 implementation. Consider using a concrete class unless multiple implementations are needed."
            })

    # Interfaces declared in the project but never implemented
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
    """Find common/util/shared/base packages that are nearly empty or contain only pass-through code.

    A package with <= min_files source files is considered suspect because
    such small packages often exist without explicit user request and may
    represent unnecessary abstraction.
    """
    results = []
    # `core` is intentionally excluded: FastAPI + LangGraph projects use `core/`
    # as the standard location for infrastructure (config, llm, middleware, langgraph/).
    suspect_names = {"common", "util", "utils", "shared", "framework", "base"}
    # Exclusions matched against full path components (exact match)
    exclude_dirs = {"node_modules", ".git", "__pycache__", "venv", ".venv",
                    "target", "build", "dist", ".mvn", ".gradle", "egg-info"}

    for pkg_dir in root.rglob("*"):
        if not pkg_dir.is_dir():
            continue
        if pkg_dir.name not in suspect_names:
            continue
        # Check each path component against exclude list (exact match, not substring)
        if any(part in exclude_dirs for part in pkg_dir.relative_to(root).parts):
            continue

        files = [f for f in pkg_dir.rglob("*") if f.is_file() and f.suffix in (".java", ".py") and not any(p in exclude_dirs for p in f.relative_to(pkg_dir).parts)]
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
    """Find class inheritance chains deeper than max_depth levels (Java + Python)."""
    results = []
    extends_graph = {}       # class_name -> parent_name
    class_files = {}         # class_name -> file path

    # --- Java pass ---
    for f in (file_list_java if file_list_java is not None else _rglob_filtered(root, "*.java")):
        try:
            content = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        lines_j = content.split('\n')
        i = 0
        while i < len(lines_j):
            stripped = lines_j[i].strip()
            # Strip inline block comments BEFORE skip checks so that
            # '/* comment */ class Foo extends Bar' is not missed.
            stripped_nc = re.sub(r'/\*.*?\*/', '', stripped).strip()
            if stripped_nc == '' or stripped_nc.startswith('//') or stripped_nc.startswith('/*') or stripped_nc.startswith('*'):
                i += 1; continue
            # Skip annotation-only lines (no class keyword on same line)
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
                # Multi-line: 'class Name' here, 'extends Parent' on a subsequent line
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
                            # extends keyword found but parent name may be on next line; keep scanning
                        # Stop if we see opening brace, another type decl, or implements
                        if re.search(r'\{|\b(?:class|interface|enum|record)\b|\bimplements\b', nl_nc):
                            break
                        j += 1
            i += 1

    # --- Python pass ---
    for f in (file_list_py if file_list_py is not None else _rglob_filtered(root, "*.py")):
        try:
            content = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        # Strip #-style comments to avoid false matches inside comments/docstrings.
        # Best-effort: does not handle # inside multi-line strings perfectly.
        # Heuristic: only treat '#' as a comment start when preceded by whitespace
        # or at line start, to reduce false positives with string literals like x="#foo".
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
            paren_pos = class_start.end() - 1  # position of '('
            close_pos = _find_matching_paren(content, paren_pos)
            if close_pos == -1:
                continue
            parents_raw = content[class_start.end():close_pos]
            parents = [p.strip() for p in _split_comma_aware(parents_raw) if p.strip()]
            if parents:
                first_parent = re.sub(r'\[.*\]', '', parents[0]).strip()  # primary base, strip generics
                class_files[class_name] = str(f.relative_to(root))
                extends_graph[class_name] = first_parent.split(".")[-1]

    # Helper: calculate inheritance depth.  Returns -1 for cyclic chains
    # so they are never flagged as "deep inheritance".
    def calc_depth(cls_name: str, visiting: set = None) -> int:
        if visiting is None:
            visiting = set()
        if cls_name in visiting:
            return -1  # cycle detected — do not report
        visiting.add(cls_name)
        parent = extends_graph.get(cls_name)
        if parent is None:
            return 0
        child_depth = calc_depth(parent, visiting)
        if child_depth == -1:
            return -1  # propagate cycle marker
        return 1 + child_depth

    # Second pass: report classes with depth >= max_depth (skip cycles)
    for class_name, file_path in class_files.items():
        depth = calc_depth(class_name)
        if depth >= max_depth and depth != -1:
            # Build the chain for reporting
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
    """Find methods that only delegate to another method with minimal logic (pass-through wrappers)."""
    results = []
    for f in (file_list if file_list is not None else _rglob_filtered(root, "*.java")):
        try:
            content = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        # Match a Java method, skipping optional annotations above it.
        # Approach: scan line-by-line; when we see a method signature, check its body.
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # Strip inline block comments first so '/* ... */ code' is not skipped
            line = re.sub(r'/\*.*?\*/', '', line).strip()
            # Skip comment-only and annotation-only lines
            if line.startswith('//') or line.startswith('/*') or line.startswith('*'):
                i += 1
                continue
            # Skip annotation-only lines (no method-like keyword on same line).
            # After making the modifier optional below, we must also let through
            # lines that start with a return-type + method-name without a modifier.
            if line.startswith('@') and not re.search(r'\b(public|private|protected|default|static|void|int|boolean|long|double|float|byte|short|char|String)\b', line):
                i += 1
                continue
            m = re.search(
                r'(?:(?:public|private|protected|default)\s+)?'  # access modifier or interface default (optional — package-private methods have none)
                r'(?:static\s+)?'
                r'(?:<[^<>]*>\s+)?'            # optional generic type param (simplified; nested generics unsupported)
                r'(.+)'                     # return type (greedily match incl. generics with spaces)
                r'\s+(\w+)\s*'               # method name
                r'\(([^)]*)\)',               # parameter list
                line
            )
            if not m:
                i += 1
                continue
            method_name = m.group(2)
            # Collect the method body (naive brace counting)
            brace_count = 0
            open_pos = None
            # Heuristic: only treat '//' as comment start when preceded by space
            # to reduce false positives with URLs inside strings.
            comment_pos = line.find(' //')
            clean = line[:comment_pos] if comment_pos != -1 else line
            if '{' in clean:
                brace_count = clean.count('{') - clean.count('}')
                open_pos = clean.index('{')
            else:
                # Look ahead for Allman-style opening brace on next line(s)
                j = i + 1
                while j < len(lines):
                    ahead = lines[j].strip()
                    # Strip inline block comments first
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
                        break  # non-empty, non-comment line without '{' — not parseable
                if open_pos is None:
                    i += 1
                    continue
            if '}' in clean[open_pos:]:
                # Inline single-line body: "public void foo() { return bar.baz(); }"
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
# Python-specific detectors
# ---------------------------------------------------------------------------

def find_python_abc_smell(root: Path, file_list: list[Path] | None = None) -> list[dict]:
    """Find ABCs with at most one concrete subclass in the project.

    An ABC with a single implementation is the Python equivalent of a
    single-implementation Java interface — the abstraction may be unnecessary.
    """
    results = []
    abc_classes = {}          # abc_name -> file_path
    abc_subclasses = defaultdict(set)  # abc_name -> set of subclass file paths

    for f in (file_list if file_list is not None else _rglob_filtered(root, "*.py")):
        try:
            content = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        rel = str(f.relative_to(root))

        # Strip comment-only lines so that '# class Foo(ABC):' is not matched
        # as a real class definition.
        content_no_comments = '\n'.join(
            '' if ln.strip().startswith('#') else ln
            for ln in content.split('\n')
        )

        # Detect ABC definitions: class X(ABC) or class X(metaclass=ABCMeta)
        for abc_match in re.finditer(
            r'^class\s+(\w+)\s*\((?:.*?\bABC\b.*?|.*?metaclass\s*=\s*(?:abc\.)?ABCMeta.*?)\)',
            content_no_comments,
            re.MULTILINE
        ):
            abc_classes[abc_match.group(1)] = rel

        # Detect subclasses: use paren-depth matching to handle nested parens in
        # type-hint arguments like class Foo(Generic[Dict[str, int]]).
        # Strip #-comments from a copy to avoid false class matches in comments.
        # Heuristic: only treat '#' as comment start when preceded by whitespace.
        content_cleaned = '\n'.join(
            (ln[:ln.find(' #')] if ln.find(' #') != -1 and not ln.strip().startswith('#') else
             ('' if ln.strip().startswith('#') else ln))
            for ln in content.split('\n')
        )
        for class_start in re.finditer(r'class\s+(\w+)\s*\(', content_cleaned):
            class_name = class_start.group(1)
            paren_pos = class_start.end() - 1  # position of '('
            close_pos = _find_matching_paren(content_cleaned, paren_pos)
            if close_pos == -1:
                continue
            parents_raw = content_cleaned[class_start.end():close_pos]
            parents = []
            for p in _split_comma_aware(parents_raw):
                p = p.strip()
                if not p:
                    continue
                # Strip inline comment (e.g. 'BaseClass  # explanation' -> 'BaseClass')
                comment_idx = p.find('#')
                if comment_idx != -1:
                    p = p[:comment_idx].strip()
                if p:
                    parents.append(p)
            for parent in parents:
                if parent != class_name:  # skip self-referential
                    # Strip generic type parameters (e.g., Generic[T] -> Generic)
                    parent_clean = re.sub(r'\[.*\]', '', parent).strip()
                    simple_parent = parent_clean.split('.')[-1]
                    abc_subclasses[simple_parent].add(rel)

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
    """Return index of matching ')' for '(' at `start`, or -1 if not found.

    String-literal aware: skips over characters inside single/double/triple-quoted
    strings so that parentheses inside default values like x="default(val)" do not
    cause premature return.
    """
    depth = 0
    idx = start
    while idx < len(line):
        ch = line[idx]
        # --- string-literal skipping ---
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
                # Single-char quote: skip to matching close, respecting backslash escapes
                quote = ch
                idx += 1
                while idx < len(line):
                    if line[idx] == '\\' and idx + 1 < len(line):
                        idx += 2  # skip escaped character, whatever it is
                    elif line[idx] == quote:
                        break
                    else:
                        idx += 1
                idx += 1
                continue
        # --- end string-literal skipping ---
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return idx
        idx += 1
    return -1


def find_python_pass_through(root: Path, file_list: list[Path] | None = None) -> list[dict]:
    """Find Python functions/methods that only delegate to another callable."""
    results = []
    for f in (file_list if file_list is not None else _rglob_filtered(root, "*.py")):
        try:
            content = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        rel = str(f.relative_to(root))
        lines = content.split('\n')

        # Detect: def name(args):\n    return other.method(args)
        for i, line in enumerate(lines):
            # Use paren-depth matching to handle nested calls in default values
            m = re.search(r'^\s*(?:async\s+)?def\s+(\w+)\s*(?:\[[^\]]*\])?\s*\(', line)
            if not m:
                continue
            # Find matching closing paren for the parameter list.
            # Start on the current line; if the signature spans multiple lines,
            # accumulate lines until the closing ')' is found.
            paren_start = m.end() - 1  # position of '('
            close_idx = _find_matching_paren(line, paren_start)
            sig_end_i = i  # physical line index where signature closes
            if close_idx == -1:
                # Multi-line signature: accumulate lines until closing paren
                sig_lines = [line]
                for k in range(i + 1, len(lines)):
                    # Strip #-comments before appending so that ')' inside
                    # comments (e.g. 'x: int  # default(val)') does not
                    # cause _find_matching_paren to return prematurely.
                    # Heuristic: only treat '#' as comment start when preceded by whitespace.
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
                    continue  # malformed — skip
                sig = '\n'.join(sig_lines)
            else:
                sig = line
            # Check for return type annotation and colon after the closing paren
            rest = sig[close_idx+1:].strip()
            if rest and not rest.startswith(':') and not rest.startswith('->'):
                # rest is non-empty and not a ':' or '->' suffix — malformed signature
                continue
            func_name = m.group(1)
            def_indent = len(line) - len(line.lstrip())
            # Check for single-line body on same line as closing paren:
            # def foo(x): <body>  or  def foo(x) -> T: <body>
            after_colon = ""
            if rest.startswith(':'):
                after_colon = rest[1:].strip()
            elif rest.startswith('->'):
                m_rtype = re.match(r'->\s*(.+):\s*(.*)', rest)
                if m_rtype:
                    after_colon = m_rtype.group(2).strip()
            if after_colon:
                # Strip inline comment so 'return bar.baz()  # explain' is recognised
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
                    continue  # single-line function, body already checked
                # after_colon was purely a comment — fall through to body collection
            # Collect the body until dedent (track triple-quote state to avoid
            # false dedent on unindented """ inside a multi-line string).
            # Track WHICH quote type opened the region — a """ docstring that
            # contains ''' in its body text must not be closed by the embedded
            # single-quote variant, and vice versa.
            body_lines = []
            triple_type = None  # None | '"""' | "'''"
            j = sig_end_i + 1
            while j < len(lines):
                line_j = lines[j]
                stripped_j = line_j.strip()
                if stripped_j == '':
                    j += 1
                    continue  # skip blank lines within function body
                # Count exact triple-quote boundaries (not part of 4+ consecutive quotes)
                dq_count = len(re.findall(r'(?<!")"""(?!")', stripped_j))
                sq_count = len(re.findall(r"(?<!')'''(?!')", stripped_j))
                if triple_type is None:
                    # Outside a triple-quoted string — an odd count of either
                    # marker opens a region of that type.
                    if dq_count % 2 == 1:
                        triple_type = '"""'
                        j += 1
                        continue
                    if sq_count % 2 == 1:
                        triple_type = "'''"
                        j += 1
                        continue
                    # Single-line triple-quoted string (even count — both open
                    # and close markers on the same line, e.g. """docstring.""").
                    # Skip it so docstrings don't pollute body_lines and cause
                    # false negatives for otherwise single-statement pass-throughs.
                    if stripped_j.startswith(('"""', "'''", 'r"""', "r'''", 'f"""', "f'''", 'b"""', "b'''", 'u"""', "u'''", 'rb"""', "rb'''")):
                        j += 1
                        continue
                else:
                    # Inside a triple-quoted string — only the matching quote
                    # type can close it; the other type is just body content.
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
                    break  # dedented — next top-level or peer statement
                if stripped_j.startswith('@') and current_indent <= def_indent:
                    break  # decorator on next peer method (not inside nested scope)
                body_lines.append(line_j.strip())
                j += 1
            # Filter out comments and blanks; strip inline comments first
            # so that 'return foo.bar()  # delegate' is recognised as code.
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
# Reporters
# ---------------------------------------------------------------------------

def report_text(smells: list[dict]) -> str:
    """生成按严重程度分组的可读报告。

    Args:
        smells: 检查器发现的问题。

    Returns:
        用于终端输出的报告。
    """
    if not smells:
        return "No abstraction smells found. Code looks direct and readable.\n"

    # 1. 先按严重程度归组，使阻断级别的发现优先可见。
    lines = [f"Found {len(smells)} potential abstraction smell(s):\n"]
    by_severity = defaultdict(list)
    for s in smells:
        by_severity[s["severity"]].append(s)

    # 2. 保持各组内部顺序，方便人工对照同一次扫描结果。
    for severity in ("warning", "info"):
        items = by_severity.get(severity, [])
        if items:
            lines.append(f"  [{severity.upper()}]")
            for item in items:
                lines.append(f"    - {item['message']}")
    return "\n".join(lines) + "\n"


def report_json(smells: list[dict]) -> str:
    """生成包含问题列表与数量的 JSON。

    Args:
        smells: 检查器发现的问题。

    Returns:
        JSON 字符串。
    """
    return json.dumps({"smells": smells, "count": len(smells)}, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _related(smell: dict, selected: set[str]) -> bool:
    """按涉及文件限制报告，分析阶段仍保留完整上下文。"""
    paths = [smell.get(key) for key in ("file", "interface", "abc")]
    for key in ("files", "implementations", "subclasses"):
        paths.extend(smell.get(key, []))
    return any(Path(p).as_posix() in selected for p in paths if p)


def _scan(root: Path, args, selected: set[str] | None) -> list[dict]:
    """读取选定语言的完整上下文后限制报告范围。"""
    # 1. 跨文件关系必须读取全部实现，避免将未修改的实现误判为不存在。
    java = _rglob_filtered(root, "*.java") if args.lang != "python" else []
    python = _rglob_filtered(root, "*.py") if args.lang != "java" else []
    language_files = {p.relative_to(root).as_posix() for p in java + python}
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
    return smells if selected is None else [s for s in smells if _related(s, selected)]


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
            smells = _scan(snapshot, args, selected)
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
        smells = _scan(root, args, selected)

    # 3. 输出与退出策略分开，info 不会触发 warning 级阻断。
    print(report_json(smells) if args.json else report_text(smells))
    blocked = args.fail_on != "none" and any(
        args.fail_on == "info" or s["severity"] == "warning" for s in smells)
    sys.exit(1 if blocked else 0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: abstraction smell checker failed: {e}", file=sys.stderr)
        sys.exit(2)
