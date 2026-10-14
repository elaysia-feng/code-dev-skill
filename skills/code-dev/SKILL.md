---
name: code-dev
description: >-
  用于 Java/Spring、Python/FastAPI/LangGraph、TypeScript/JavaScript/Node.js、C++ 和 C#/.NET 项目的实现、审查与重构。
  规范项目结构、环境配置、业务常量、SQL 文档和简体中文注释，并按需核对 TypeScript npm 包发布。
license: MIT
---

# Code Dev

**This standard is mandatory, not a list of suggestions.** It applies to every personal project, and the bar is never lowered to match the existing code style.

## Priority

1. Explicit user requirements and authorized task scope.
2. Correctness and preservation of agreed contracts.
3. **Company standards**: if the target project has a company-standards skill installed or a project-level conventions file, that takes precedence and this standard falls back to being a reference.
4. The mandatory rules of this standard.
5. The simplest, clearest implementation.

Explicit user requirements override this skill. Existing style alone does not justify a violation; apply corrections within the authorized scope rather than turning a local task into a repository-wide migration.

## 既有项目迁移

发现既有结构不符合规范且迁移范围尚未确定时，先说明拟迁移的范围，再询问是否全量迁移。用户同意后在确认范围内完成迁移，验证导入、构建及相关运行行为；用户不同意时保留既有结构，仅新增部分遵循规范，复用已有边界，不另建重复实现。当前任务已明确要求结构迁移或当前会话已给出选择时，直接按授权范围执行，不重复询问；不顺带迁移无关代码。所有参考文档的结构调整均受此规则约束。

## Mandatory rules

These must be enforced for implementation, review and refactoring:

- **Project structure must follow [`references/project-structure.md`](references/project-structure.md)** for the relevant language and application type; existing structure changes follow the migration rule above.
- **Java business components must always be `interface + impl/`**; a single implementation is not a reason to skip the interface.
- 新增和修改的说明性注释使用简体中文；不顺带翻译未修改的历史注释。多阶段方法按真实流程使用 `1.`、`1.1` 等编号，私有方法和短方法也按业务阶段判断，不能仅因行数少而省略。
- **Source files must always be UTF-8**, with or without a BOM. Neither checker can analyse a file it cannot decode, so a non-UTF-8 source file is reported and rejected rather than quietly passed over.
- **SQL schema documentation is mandatory**: initialization and migration DDL must describe each table's purpose and each column's meaning using database metadata comments plus a trailing `-- ` explanation on every column definition. Use dialect-supported syntax; see [`references/sql-guidelines.md`](references/sql-guidelines.md). Descriptions are in Simplified Chinese, while skill instructions remain in English.
- **Externalize configuration and separate development, test and production environments**: keep shared defaults separate from environment differences and use the framework's native configuration mechanism. TS/Python may use `.env` files, Spring Boot uses YAML and profiles, ASP.NET Core uses `appsettings` files, and C++ uses the project's JSON, TOML, INI or equivalent format. Wire up and verify actual loading; see [`references/configuration-guidelines.md`](references/configuration-guidelines.md).
- **No hardcoded configuration or business magic values**: externalize environment values, tunable parameters and secrets. Represent fixed business states and repeated values with meaningful domain constants or enums. Moving configurable values into constants still counts as hardcoding; extracting every number or string is not required.
- **Use Java annotations appropriately**: use applicable declarative framework capabilities and verify they take effect. Do not introduce frameworks into plain Java merely for annotations or require all logic to use them. See [`references/java-guidelines.md`](references/java-guidelines.md#annotation-usage).
- **In Java and TypeScript/JavaScript, every `if`, `else if` and `else` branch body must be enclosed in braces `{}`**, even when it contains only one statement. This applies whether the statement is on the same line or the next line, including guard clauses and early `return`, `throw`, `break` or `continue`. Unbraced branch bodies are mandatory violations in implementation, review and refactoring; Python retains its native indentation-based syntax. See the examples in [`references/java-guidelines.md`](references/java-guidelines.md#conditional-branch-braces).
- **Do not add** shared methods, base classes, shared modules or extra layers merely to reduce the number of duplicated lines.
- Extract a structure only when one of the following holds: the user explicitly asked for it, a stable shared rule exists, there is a clear extension point, or there is a framework boundary. The project's pre-existing architecture does not qualify.
- Read the relevant modules, call relationships and existing patterns before you start — reading them is for judging the blast radius, not for carrying on with the existing style.
- **Determine file ownership before creating or moving files**: inspect the type's responsibility, framework markers, callers and project layout, then choose the layer defined by the relevant language reference. Names, proximity to a caller and "it runs" do not establish structural correctness. If the evidence leaves materially different valid placements, explain the ambiguity and ask before choosing.
- When the user explicitly requests a refactor or an extraction, complete it within their scope: do not refuse it and do not widen it. If that request conflicts with this standard, state the conflict first and then carry it out; never violate this standard silently.
- When the user only asks for a review, report the problems only and do not change code automatically.

A directory marked `optional` is **prohibited unless the application actually needs it** — the marker is a restriction, not an optional style. Create it when the need is real; skip it otherwise, never because a template happened to include it.

## Java business interfaces

Java components that carry business behaviour follow the interface-first convention in [`references/java-guidelines.md`](references/java-guidelines.md): first determine whether a dedicated `*.biz` module exists, then place the interface and its implementation according to the corresponding project shape. Definition types such as DTOs, entities, enums, exceptions and configuration do not gain an interface as a result.

A single-implementation interface must not be skipped just because "there is only one implementation"; a thin implementation is a legitimate boundary whenever it carries transactions, security, concurrency, resource management or a public contract.

## Load on demand

**Which section to load is decided by the task, but what you read is as mandatory as this file.** The reference documents carry no advisory weighting; read only what the current task calls for:

All reference rules, including package or module renaming, inherit the priority and scope limits above. They do not independently authorize broader migrations or external actions.

| Scenario | Reference document |
|---|---|
| Designing or changing API versions, contracts or migration paths | [`references/api-versioning-guidelines.md`](references/api-versioning-guidelines.md) |
| Changing persistence, external calls, retries, scheduled/background work or runtime error handling | [`references/runtime-boundaries.md`](references/runtime-boundaries.md) |
| Adding or changing configuration, environment selection, defaults, or reviewing hardcoding | [`references/configuration-guidelines.md`](references/configuration-guidelines.md); also read Java guidelines for Java |
| Java/Spring backend | [`references/java-guidelines.md`](references/java-guidelines.md) |
| Java microservice boundaries | [`references/microservice-guidelines.md`](references/microservice-guidelines.md) and the Java guidelines |
| Python, FastAPI or LangGraph | [`references/python-guidelines.md`](references/python-guidelines.md) |
| TypeScript 前端应用（React/Vue/Next.js 等） | [`references/frontend-guidelines.md`](references/frontend-guidelines.md) 与结构规范中的前端章节 |
| TypeScript/JavaScript application or Node.js implementation | [`references/typescript-guidelines.md`](references/typescript-guidelines.md) |
| C++ implementation, review or refactoring | [`references/cpp-guidelines.md`](references/cpp-guidelines.md) |
| C#/.NET implementation, review or refactoring | [`references/csharp-guidelines.md`](references/csharp-guidelines.md) |
| Creating or moving files, determining type/module ownership, or adjusting project structure | [`references/project-structure.md`](references/project-structure.md) |
| Creating or modifying SQL initialization scripts, migrations or table definitions | [`references/sql-guidelines.md`](references/sql-guidelines.md) |
| Implementing, changing or reviewing Java, Python, TypeScript/JavaScript, C++ or C# code, even when comments were not requested | [`references/code-comment-guidelines.md`](references/code-comment-guidelines.md); use the language's own comment syntax |
| Deciding what a specific comment should actually say | [`references/code-comment-examples.md`](references/code-comment-examples.md) |
| Creating or maintaining a TypeScript npm package, its export entry point or its publish contents | [`references/typescript-package-guidelines.md`](references/typescript-package-guidelines.md) |
| Extracting a boundary, or when the organisation is unclear | Read only the relevant examples in [`references/examples.md`](references/examples.md) |
| Applying editor settings that stop tooling from rewriting the code this standard produces (auto-organize imports, cleanup-on-save, auto-refactoring) | [`assets/ide-settings.json`](assets/ide-settings.json) |

## Checks

检查器只提供启发式线索，不能替代人工判断。WARNING 必须逐条修正，或说明符合哪项豁免及其源码依据；退出码为 0 不代表注释规范已通过。审查任务只报告，不自动修正。

Language-specific rules apply only to their language: Java business interfaces, `impl/` and annotations do not apply to other languages; Python retains indentation-based syntax. Follow the respective references for C++ and C# structure and checks.

When reviewing abstractions:

This checker supports Java/Python only. Review TS/JS, C++ and C# manually against the standards; do not report unscanned languages as having passed.

```sh
python <skill-dir>/scripts/check-abstraction-smell.py <project-root> --lang auto --fail-on warning
```

Java business components are automatically exempt from the single-implementation interface warning thanks to the `impl/` convention.

After changing Java/Python files:

```sh
python <skill-dir>/scripts/check_comments.py <changed-files> --fail-on warning
python <skill-dir>/scripts/check_comments.py --staged --fail-on warning
```

Use `--staged` when the working tree and the index differ — it reads what would actually be committed, not what happens to be on disk.

默认退出码 `0` 仅表示没有 ERROR；`--fail-on warning` 会同时阻断 WARNING；`1` 表示达到阻断阈值；`2` 表示路径未匹配可检查文件或检查无法完成。暂存区无 Java/Python 变更时返回 `0` 并说明未检查文件。TypeScript 必须人工核对，不能宣称该检查器已覆盖。

`check-abstraction-smell.py` exits `0` below the threshold, `1` when `--fail-on` is reached, and `2` when a source file cannot be decoded.

可选 Git hook：将 `scripts/pre-commit-check.sh` 合并到现有 hook，不覆盖。它检查暂存内容；设置 `READABILITY_FIRST_STRICT=1` 时两个检查器的 WARNING 都会阻断，也可单独设置 `COMMENT_FAIL_ON=warning`。默认只阻断注释 ERROR 和读取失败；不能把 hook 放行当成规范通过。

完成前逐个核对本次新增或修改的函数：公开契约是否需要文档、多阶段流程是否有编号、父子层级是否真实、关键边界/失败原因是否说明。覆盖短函数和私有函数；简单访问器、单步函数、纯转发可以豁免。说明 WARNING 的处理与未验证部分，不用无意义注释消除提示。

Before finishing, confirm that the requirements have been delivered, that the mandatory rules have been checked one by one, and state what has not yet been verified.

Configuration, hardcoding and Java annotation rules require manual review; existing checkers do not cover them. For configuration changes, also verify development/test/production selection, overrides, missing required values and prevention of production fallback to development configuration. Use no real production credentials or connections during validation.
