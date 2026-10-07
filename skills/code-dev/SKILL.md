---
name: code-dev
description: >-
  Mandatory development standard for Java/Spring, Python/FastAPI/LangGraph and
  TypeScript/Node.js projects, covering project structure, the shape of Java business
  interfaces, Simplified Chinese code comments and TypeScript npm package publishing.
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
| Java/Spring backend | [`references/java-guidelines.md`](references/java-guidelines.md) |
| Java microservice boundaries | [`references/microservice-guidelines.md`](references/microservice-guidelines.md) and the Java guidelines |
| Python, FastAPI or LangGraph | [`references/python-guidelines.md`](references/python-guidelines.md) |
| A new project, or adjusting directories/modules | [`references/project-structure.md`](references/project-structure.md) |
| Adding or changing Java, Python or TypeScript comments | [`references/code-comment-guidelines.md`](references/code-comment-guidelines.md) |
| Deciding what a specific comment should actually say | [`references/code-comment-examples.md`](references/code-comment-examples.md) |
| Creating or maintaining a TypeScript npm package, its export entry point or its publish contents | [`references/typescript-package-guidelines.md`](references/typescript-package-guidelines.md) |
| Extracting a boundary, or when the organisation is unclear | Read only the relevant examples in [`references/examples.md`](references/examples.md) |
| Applying editor settings that stop tooling from rewriting the code this standard produces (auto-organize imports, cleanup-on-save, auto-refactoring) | [`assets/ide-settings.json`](assets/ide-settings.json) |

## Checks

Because the standard is mandatory, both commands below are used with blocking semantics. Checker output is only a lead and cannot replace human judgement.

When reviewing abstractions:

```sh
python <skill-dir>/scripts/check-abstraction-smell.py <project-root> --lang auto --fail-on warning
```

Java business components are automatically exempt from the single-implementation interface warning thanks to the `impl/` convention.

After changing Java/Python files:

```sh
python <skill-dir>/scripts/check_comments.py <changed-files>
```

Exit codes: `0` means no ERROR (a WARNING may still be present); `1` means an ERROR exists; `2` means no checkable file was matched (**which does not mean there is no problem**). This checker does not cover TypeScript, and every WARNING requires human judgement.

`check-abstraction-smell.py` exits `0` below the threshold, `1` when `--fail-on` is reached, and `2` when a source file cannot be decoded.

Optional git hook: merge `scripts/pre-commit-check.sh` into the existing hook, do not overwrite it. It does not block by default; it only blocks on WARNING-level issues when `READABILITY_FAIL_ON=warning` is set.

Before finishing, confirm that the requirements have been delivered, that the mandatory rules have been checked one by one, and state what has not yet been verified.
