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

1. Explicit user requirements and authorized task scope.
2. Correctness and preservation of agreed contracts.
3. **Company standards**: if the target project has a company-standards skill installed or a project-level conventions file, that takes precedence and this standard falls back to being a reference.
4. The mandatory rules of this standard.
5. The simplest, clearest implementation.

Explicit user requirements override this skill. Existing style alone does not justify a violation; apply corrections within the authorized scope rather than turning a local task into a repository-wide migration.

## Mandatory rules

These must be enforced for implementation, review and refactoring:

- **Project structure must follow [`references/project-structure.md`](references/project-structure.md)** for the relevant language and application type. Correct affected structure within the task scope; report unrelated structural debt instead of migrating it automatically.
- **Java business components must always be `interface + impl/`**; a single implementation is not a reason to skip the interface.
- **Comments must always be in Simplified Chinese**; projects that use English comments must be rewritten the same way. Multi-stage methods must mark their steps with hierarchical numbering such as `1.` and `1.1`.
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
| TypeScript/JavaScript application or Node.js implementation | [`references/typescript-guidelines.md`](references/typescript-guidelines.md) |
| C++ implementation, review or refactoring | [`references/cpp-guidelines.md`](references/cpp-guidelines.md) |
| C#/.NET implementation, review or refactoring | [`references/csharp-guidelines.md`](references/csharp-guidelines.md) |
| Creating or moving files, determining type/module ownership, or adjusting project structure | [`references/project-structure.md`](references/project-structure.md) |
| Creating or modifying SQL initialization scripts, migrations or table definitions | [`references/sql-guidelines.md`](references/sql-guidelines.md) |
| Adding or changing Java, Python, TypeScript/JavaScript, C++ or C# comments | [`references/code-comment-guidelines.md`](references/code-comment-guidelines.md); use the language's own comment syntax |
| Deciding what a specific comment should actually say | [`references/code-comment-examples.md`](references/code-comment-examples.md) |
| Creating or maintaining a TypeScript npm package, its export entry point or its publish contents | [`references/typescript-package-guidelines.md`](references/typescript-package-guidelines.md) |
| Extracting a boundary, or when the organisation is unclear | Read only the relevant examples in [`references/examples.md`](references/examples.md) |
| Applying editor settings that stop tooling from rewriting the code this standard produces (auto-organize imports, cleanup-on-save, auto-refactoring) | [`assets/ide-settings.json`](assets/ide-settings.json) |

## Checks

Because the standard is mandatory, both commands below are used with blocking semantics. Checker output is only a lead and cannot replace human judgement.

Language-specific rules apply only to their language: Java business interfaces, `impl/` and annotations do not apply to other languages; Python retains indentation-based syntax. Follow the respective references for C++ and C# structure and checks.

When reviewing abstractions:

This checker supports Java/Python only. Review TS/JS, C++ and C# manually against the standards; do not report unscanned languages as having passed.

```sh
python <skill-dir>/scripts/check-abstraction-smell.py <project-root> --lang auto --fail-on warning
```

Java business components are automatically exempt from the single-implementation interface warning thanks to the `impl/` convention.

After changing Java/Python files:

```sh
python <skill-dir>/scripts/check_comments.py <changed-files>
python <skill-dir>/scripts/check_comments.py --staged   # Check Git staged contents
```

Use `--staged` when the working tree and the index differ — it reads what would actually be committed, not what happens to be on disk.

Exit codes: `0` means no ERROR (a WARNING may still be present); `1` means an ERROR exists; `2` means no checkable file was matched (**which does not mean there is no problem**). This checker does not cover TypeScript, and every WARNING requires human judgement.

`check-abstraction-smell.py` exits `0` below the threshold, `1` when `--fail-on` is reached, and `2` when a source file cannot be decoded.

Optional git hook: merge `scripts/pre-commit-check.sh` into the existing hook, do not overwrite it. It runs **both** checkers over the staged Java/Python files — previously it ran only the abstraction checker, so comment rules had no coverage at the commit gate. Smell findings are advisory unless `READABILITY_FAIL_ON=warning` is set, but two things always block because they mean the check did not finish: a source file that is not UTF-8, and any `check_comments.py` ERROR (syntax error, unreadable file, or a TODO without an owner).

Before finishing, confirm that the requirements have been delivered, that the mandatory rules have been checked one by one, and state what has not yet been verified.

Configuration, hardcoding and Java annotation rules require manual review; existing checkers do not cover them. For configuration changes, also verify development/test/production selection, overrides, missing required values and prevention of production fallback to development configuration. Use no real production credentials or connections during validation.
