---
name: code-dev
description: >-
  用于 Java/Spring、Python/FastAPI/LangGraph 和 TypeScript 前端/Node.js 项目的实现、审查与重构。
  规范项目结构、Java 业务接口、简体中文注释和流程编号，并按需核对 TypeScript npm 包发布。
license: MIT
---

# Code Dev

**This standard is mandatory, not a list of suggestions.** It applies to every personal project, and the bar is never lowered to match the existing code style.

## Priority

1. Correctness.
2. **Company standards**: if the target project has a company-standards skill installed or a project-level conventions file, that takes precedence and this standard falls back to being a reference.
3. Explicit user requirements — they define the scope of the task, including the migration choice below; this skill never authorizes changes beyond that scope.
4. The mandatory rules of this standard.
5. The simplest, clearest implementation.

Company standards take precedence; preservation of existing structure follows the migration choice below. "The existing code is written this way" does not exempt new code from this standard.

## 既有项目迁移

发现既有项目结构不符合本规范时，先说明拟迁移的范围，再询问用户是否全量迁移。用户同意后直接完成全量迁移，并验证相关导入、构建和运行行为；用户不同意时，仅新增代码、目录和模块遵循本规范，保留既有结构，不顺带搬移、重命名或重构既有代码。新增代码与既有结构衔接时复用已有业务与数据访问边界，不复制一套实现。用户尚未答复时，不开始既有结构迁移；当前会话已明确同意或拒绝的，不重复询问。以下所有既有结构迁移条款均受此规则约束。

## Mandatory rules

These must be enforced for implementation, review and refactoring:

- **Project structure must follow [`references/project-structure.md`](references/project-structure.md)**; existing structures are migrated only within the user's migration choice above.
- **Java business components must always be `interface + impl/`**; a single implementation is not a reason to skip the interface.
- 新增和修改的说明性注释使用简体中文；不顺带翻译未修改的历史注释。多阶段方法按真实流程使用 `1.`、`1.1` 等编号，私有方法和短方法也按业务阶段判断，不能仅因行数少而省略。
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
| TypeScript 前端应用（React/Vue/Next.js 等） | [`references/frontend-guidelines.md`](references/frontend-guidelines.md) 与结构规范中的前端章节 |
| A new project, or adjusting directories/modules | [`references/project-structure.md`](references/project-structure.md) |
| 新增、修改或审查 Java/Python/TypeScript 代码（即使用户没提注释） | 必须加载 [`references/code-comment-guidelines.md`](references/code-comment-guidelines.md) |
| Deciding what a specific comment should actually say | [`references/code-comment-examples.md`](references/code-comment-examples.md) |
| Creating or maintaining a TypeScript npm package, its export entry point or its publish contents | [`references/typescript-package-guidelines.md`](references/typescript-package-guidelines.md) |
| Extracting a boundary, or when the organisation is unclear | Read only the relevant examples in [`references/examples.md`](references/examples.md) |
| Applying editor settings that stop tooling from rewriting the code this standard produces (auto-organize imports, cleanup-on-save, auto-refactoring) | [`assets/ide-settings.json`](assets/ide-settings.json) |

## Checks

检查器只提供启发式线索，不能替代人工判断。WARNING 必须逐条修正，或说明符合哪项豁免及其源码依据；退出码为 0 不代表注释规范已通过。审查任务只报告，不自动修正。

When reviewing abstractions:

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
