---
name: code-dev
description: >-
  Development standard for Java/Spring, Python/FastAPI/LangGraph,
  TypeScript/JavaScript/Node.js, C++ and C#/.NET projects, covering framework-native
  environment configuration, prevention of hardcoded configuration and business magic
  values, language-specific structure, Simplified Chinese comments and TS publishing.
  For implementation, review and refactoring.
license: MIT
---

# Code Dev

**This standard is mandatory, not a list of suggestions.** It applies to every personal project, and the bar is never lowered to match the existing code style.

## Priority

1. Correctness.
2. **Company standards**: if the target project has a company-standards skill installed or a project-level conventions file, that takes precedence and this standard falls back to being a reference.
3. Explicit user requirements — they define the scope of the task, but do not exempt you from the mandatory rules below.
4. The mandatory rules of this standard.
5. The simplest, clearest implementation.

Item 2 is the **only** source of exemption. "The existing code is written this way" is not a reason in itself.

## Mandatory rules

These must be enforced for implementation, review and refactoring:

- **Project structure must follow [`references/project-structure.md`](references/project-structure.md)**, and must not be compromised to match the project's current state. When the structure does not comply, change the structure.
- **Java business components must always be `interface + impl/`**; a single implementation is not a reason to skip the interface.
- **Comments must always be in Simplified Chinese**; projects that use English comments must be rewritten the same way. Multi-stage methods must mark their steps with hierarchical numbering such as `1.` and `1.1`.
- **Source files must always be UTF-8**, with or without a BOM. Neither checker can analyse a file it cannot decode, so a non-UTF-8 source file is reported and rejected rather than quietly passed over.
- **配置必须外置并区分开发、测试、生产环境**：公共默认值与环境差异分开，遵循项目框架原生配置机制。TS/Python 可使用 `.env` 系列，Spring Boot 使用 YAML 与 profiles，ASP.NET Core 使用 `appsettings` 系列，C++ 按项目采用 JSON、TOML、INI 等。必须接入并验证实际加载机制，详见 [`references/configuration-guidelines.md`](references/configuration-guidelines.md)。
- **禁止配置硬编码和业务魔法值**：环境相关值、可调参数和敏感信息必须外置；固定业务状态及有明确业务含义的重复值使用领域所属的具名常量或枚举。把可变配置搬进常量类仍属于硬编码，但不要求提取每个数字和字符串。
- **Java 合理使用注解**：框架提供且适用于当前职责的声明式能力时，应使用注解并确认生效；普通 Java 项目不为此强行引入框架，也不要求所有逻辑都通过注解实现。具体边界见 [`references/java-guidelines.md`](references/java-guidelines.md#注解使用)。
- **In Java and TypeScript/JavaScript, every `if`, `else if` and `else` branch body must be enclosed in braces `{}`**, even when it contains only one statement. This applies whether the statement is on the same line or the next line, including guard clauses and early `return`, `throw`, `break` or `continue`. Unbraced branch bodies are mandatory violations in implementation, review and refactoring; Python retains its native indentation-based syntax. See the examples in [`references/java-guidelines.md`](references/java-guidelines.md#conditional-branch-braces).
- **Do not add** shared methods, base classes, shared modules or extra layers merely to reduce the number of duplicated lines.
- Extract a structure only when one of the following holds: the user explicitly asked for it, a stable shared rule exists, there is a clear extension point, or there is a framework boundary. The project's pre-existing architecture does not qualify.
- Read the relevant modules, call relationships and existing patterns before you start — reading them is for judging the blast radius, not for carrying on with the existing style.
- When the user explicitly requests a refactor or an extraction, complete it within their scope: do not refuse it and do not widen it. If that request conflicts with this standard, state the conflict first and then carry it out; never violate this standard silently.
- When the user only asks for a review, report the problems only and do not change code automatically.

A directory marked `optional` is **prohibited unless the application actually needs it** — the marker is a restriction, not an optional style. Create it when the need is real; skip it otherwise, never because a template happened to include it.

## Java business interfaces

Java components that carry business behaviour follow the interface-first convention in [`references/java-guidelines.md`](references/java-guidelines.md): first determine whether a dedicated `*.biz` module exists, then place the interface and its implementation according to the corresponding project shape. Definition types such as DTOs, entities, enums, exceptions and configuration do not gain an interface as a result.

A single-implementation interface must not be skipped just because "there is only one implementation"; a thin implementation is a legitimate boundary whenever it carries transactions, security, concurrency, resource management or a public contract.

## Load on demand

**Which section to load is decided by the task, but what you read is as mandatory as this file.** The reference documents carry no advisory weighting; read only what the current task calls for:

| Scenario | Reference document |
|---|---|
| 新增或修改配置、环境切换、配置默认值，或检查硬编码 | [`references/configuration-guidelines.md`](references/configuration-guidelines.md)；Java 同时读取 Java guidelines |
| Java/Spring backend | [`references/java-guidelines.md`](references/java-guidelines.md) |
| Java microservice boundaries | [`references/microservice-guidelines.md`](references/microservice-guidelines.md) and the Java guidelines |
| Python, FastAPI or LangGraph | [`references/python-guidelines.md`](references/python-guidelines.md) |
| C++ 实现、审查或重构 | [`references/cpp-guidelines.md`](references/cpp-guidelines.md) |
| C#/.NET 实现、审查或重构 | [`references/csharp-guidelines.md`](references/csharp-guidelines.md) |
| A new project, or adjusting directories/modules | [`references/project-structure.md`](references/project-structure.md) |
| Adding or changing Java, Python, TypeScript/JavaScript, C++ or C# comments | [`references/code-comment-guidelines.md`](references/code-comment-guidelines.md)；注释语法采用对应语言形式 |
| Deciding what a specific comment should actually say | [`references/code-comment-examples.md`](references/code-comment-examples.md) |
| Creating or maintaining a TypeScript npm package, its export entry point or its publish contents | [`references/typescript-package-guidelines.md`](references/typescript-package-guidelines.md) |
| Extracting a boundary, or when the organisation is unclear | Read only the relevant examples in [`references/examples.md`](references/examples.md) |
| Applying editor settings that stop tooling from rewriting the code this standard produces (auto-organize imports, cleanup-on-save, auto-refactoring) | [`assets/ide-settings.json`](assets/ide-settings.json) |

## Checks

Because the standard is mandatory, both commands below are used with blocking semantics. Checker output is only a lead and cannot replace human judgement.

语言专属规则只适用于对应语言：Java 的业务接口、`impl/` 和注解要求不套用到其他语言；Python 保留缩进语法。C++、C# 的结构和检查分别按对应参考文档执行。

When reviewing abstractions:

该检查器仅用于其支持的 Java/Python 代码；TS/JS、C++、C# 按规范人工审查，不得将未扫描语言报告为检查通过。

```sh
python <skill-dir>/scripts/check-abstraction-smell.py <project-root> --lang auto --fail-on warning
```

Java business components are automatically exempt from the single-implementation interface warning thanks to the `impl/` convention.

After changing Java/Python files:

```sh
python <skill-dir>/scripts/check_comments.py <changed-files>
python <skill-dir>/scripts/check_comments.py --staged   # 检查 Git 暂存区内容
```

Use `--staged` when the working tree and the index differ — it reads what would actually be committed, not what happens to be on disk.

Exit codes: `0` means no ERROR (a WARNING may still be present); `1` means an ERROR exists; `2` means no checkable file was matched (**which does not mean there is no problem**). This checker does not cover TypeScript, and every WARNING requires human judgement.

`check-abstraction-smell.py` exits `0` below the threshold, `1` when `--fail-on` is reached, and `2` when a source file cannot be decoded.

Optional git hook: merge `scripts/pre-commit-check.sh` into the existing hook, do not overwrite it. It runs **both** checkers over the staged Java/Python files — previously it ran only the abstraction checker, so comment rules had no coverage at the commit gate. Smell findings are advisory unless `READABILITY_FAIL_ON=warning` is set, but two things always block because they mean the check did not finish: a source file that is not UTF-8, and any `check_comments.py` ERROR (syntax error, unreadable file, or a TODO without an owner).

Before finishing, confirm that the requirements have been delivered, that the mandatory rules have been checked one by one, and state what has not yet been verified.

配置、硬编码和 Java 注解规则需要人工检查，现有检查器不覆盖这些要求。涉及配置变更时，还必须验证开发、测试、生产的环境选择、配置覆盖、缺失必填项的报错，以及生产环境不会回退到开发配置；不得使用真实生产凭据或连接真实生产服务来验证。
