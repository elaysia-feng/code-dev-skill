---
name: readability-first-coding
description: >-
  Use this skill when implementing, modifying, reviewing, or refactoring Java or Python backend code.
  Prioritize readable and direct code, avoid unsolicited abstractions, and preserve duplicated business
  logic unless the user explicitly requests extraction or reuse.
model: sonnet
triggers:
  - 可读性优先
  - 易读懂优先
  - 不要抽取
  - 不要抽象
  - 不要DRY
  - 不要公共模块
  - 保持重复
  - readability first
  - 不要过度设计  # activates the same readability-first workflow: prevents over-engineering and unsolicited abstractions
  - 抽取公共
  - common模块
  - 公共模块
argument-hint: "[project language or context, e.g. Java, Python (FastAPI + LangGraph), or Java microservices]"
allowed-tools: Read,Write,Edit,Glob,Grep,Bash,Task,Agent,LSP
license: MIT
---

> **Warning:** `Task` and `Agent` are listed in `allowed-tools` for orchestration purposes, but sub-agents spawned via these tools may not automatically inherit this skill's readability-first constraints. Ensure sub-agents are explicitly instructed to follow the same rules.

# Core Principle

Readable code is the highest priority. Easy to understand beats everything.

Correctness is always mandatory and never compromised — readability never justifies bugs.

For style/structure decisions (given correctness):

```
Easy to understand
> Directness
> Easy to modify
> Less duplication
> Reusability
> Abstraction
> Architectural beauty
```

# Default Behavior

- Implement only what the user requested.
- Keep business logic close to where it is used.
- Allow duplicated code by default.
- Do not extract repeated logic unless explicitly asked.
- Do not create `common`, `util`, `utils`, `shared`, `framework`, `helpers`, `extensions`, `support`, `infrastructure`, or `base` modules on your own (unless the user explicitly requests extraction — see "When Extraction IS Requested" below). `core/` is acceptable **only** in FastAPI + LangGraph projects where it holds infrastructure files (`config.py`, `llm.py`, `middleware.py`, `langgraph/`); do not use it as a general-purpose dumping ground.
- Do not modify unrelated code.

# The Abstraction Gate

Before extracting any code, ask internally:

> **Did the user explicitly request this abstraction?**

If the answer is **No** → do not extract. No matter how many times the code repeats.

> **Note:** The Gate prevents unsolicited abstractions. If the user explicitly requests extraction, proceed with the extraction — the Gate does not block it.

# Language-Specific Rules & References

| Language / Context | Reference File |
|---|---|
| Java backend | `references/java-guidelines.md` |
| Python backend (FastAPI + LangGraph) | `references/python-guidelines.md` |
| Java microservices | `references/microservice-guidelines.md` |
| Directory layout | `references/project-structure.md` |
| Good/Bad examples | `references/examples.md` |

When starting work in a supported language, use Read to load the corresponding reference file before implementing code — this ensures the language-specific guidelines are in context.

# Agent Workflow

When receiving a development task:

1. Read existing code structure first.
2. Implement within the existing structure.
3. Prefer completing work in the current file or module.
4. Even if you see duplicated code, do not extract it.
5. Do not modify unrelated code.
6. Do not introduce new architectural layers.
7. Do not create new shared modules.
8. Do not propose complex alternatives unless the task genuinely demands them.
9. Only analyze shared logic when the user explicitly requests refactoring.
10. Confirm the final code is easy to read top-to-bottom (see [Final Checks](#final-checks)).

**Existing project conventions:** If the project already consistently uses interface+impl, abstract base classes, or other abstraction patterns, follow that convention — do not break consistency. Readability-first principles take precedence for new code and new modules, and in areas where the existing convention is inconsistent or absent.

# Code Writing Rules

- Method names directly express their purpose.
- Variable names are clear and complete.
- Business flow reads top-to-bottom.
- Avoid deep nesting.
- Avoid meaningless wrappers.
- Avoid requiring cross-file jumps to understand simple logic.
- Avoid complex syntax just to save a few lines.
- Avoid overusing inheritance, generics, reflection, or design patterns.
- Critical business decisions are written inline.
- A single file should tell the main story on its own.

Prefer direct code:

```java
OrderEntity order = orderMapper.selectById(orderId);
if (order == null) {
    throw new OrderNotFoundException(orderId);
}
if (!order.getStatus().equals("PENDING")) {
    throw new IllegalStateException("Only pending orders can be cancelled");
}
order.setStatus("CANCELLED");
orderMapper.updateById(order);
```

Do NOT default to layered call chains:

```java
orderValidator.validateCancelable(order);
orderStateMachine.fire(order, OrderEvent.CANCEL);
orderDomainService.cancel(order);
orderRepository.save(order);
```

# When Extraction IS Requested

These rules apply only when the user explicitly asks to extract shared code:

| Shared Content | Location |
|---|---|
| Shared DTOs, exceptions, enums, response wrappers | `common/` |
| Stateless utilities (DateUtil, StringUtil, JsonUtil) | `util/` |
| Explicitly requested base classes | `base/` |

Only extract what the user specified. Do not "also add" extra framework classes.

> **Microservice exception:** In microservice projects, shared code lives in `base-service/` instead of `common/` — see [microservice-guidelines.md](references/microservice-guidelines.md).

# Scripts

| Script | Purpose |
|---|---|
| `scripts/check-abstraction-smell.py` | Scan project for over-abstraction smells. **Best-effort only:** uses regex-based parsing and may miss edge cases (multiline generics, annotations spanning lines, complex nested structures). **Designed for new/greenfield projects.** On legacy projects with existing abstractions, expect high noise — use `--json` output and filter results to files touched in the current change. |
| `scripts/pre-commit-check.sh` | Git pre-commit hook that runs the smell checker against staged Java/Python files. On legacy projects, consider skipping the hook or filtering its output to changed lines only. |

**Smells detected per language:**

| Smell | Java | Python |
|---|---|---|
| Single-implementation interfaces/ABCs | ✅ | ✅ |
| Empty or single-class common/util packages | ✅ | ✅ |
| Deep inheritance chains (depth > 2) | ✅ | ✅ |
| Pass-through wrapper methods | ✅ | ✅ |
| Python pass-through functions | — | ✅ |

Run before committing:

```bash
python3 skills/readability-first-coding/scripts/check-abstraction-smell.py . --lang java
python3 skills/readability-first-coding/scripts/check-abstraction-smell.py . --lang python
python3 skills/readability-first-coding/scripts/check-abstraction-smell.py . --lang auto   # auto-detect language
python3 skills/readability-first-coding/scripts/check-abstraction-smell.py . --lang java --json  # machine-readable
```

If `python3` is not available, `python` (without the 3) usually works as well.

Install as git hook:

```bash
cp skills/readability-first-coding/scripts/pre-commit-check.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

# Assets

| Asset | Purpose |
|---|---|
| `assets/ide-settings.json` | IDE settings template that disables auto-refactoring features (organize imports, auto-cleanup) |

# Final Checks

Before completing any task:

- [ ] Did I create a shared method just to reduce duplication? → If yes, inline it back. **(Test code exempt if 3+ test methods use it — shared fixtures, base test classes, and test helpers are acceptable.)**
- [ ] Did I create a `common`, `util`, `utils`, `shared`, `framework`, `helpers`, `extensions`, `support`, `infrastructure`, or `base` module the user did not ask for? → If yes, delete it. (Example: creating `common/` to hold a helper used by two files — inline it instead.) (`core/` is allowed only as FastAPI+LangGraph infrastructure — not as a generic extraction target.)
- [ ] Did I add unnecessary parent classes or interfaces? → If yes, delete them. **(Test code exempt — base test classes are acceptable.)**
- [ ] Does understanding simple logic require jumping across multiple files? → If yes, inline.
- [ ] Did I modify unrelated code? → If yes, revert.
- [ ] Did I use a more complex approach than the task requires? → If yes, simplify.
- [ ] Can the main business flow be read top-to-bottom? → If not, rewrite.

**If an abstraction reduces readability, delete the abstraction and restore direct code.**

# Test Code

Test code follows the same readability-first principles but with a lower bar for extraction. Within the Core Principle hierarchy, **readability still takes precedence over boilerplate reduction** — "reduce boilerplate" is not a priority; it is merely a side benefit of acceptable test abstractions:

- Shared fixtures, base test classes, and test helpers are acceptable when they reduce boilerplate without obscuring the test's intent.
- A reader should still understand what a test does by reading the test method alone — avoid deep inheritance chains in test classes.
- `setUp()` / `@BeforeEach` is fine for common arrangement; keep it limited to what every test in the class genuinely needs.
- If a shared test utility makes individual tests harder to follow, inline it.

# Skill Deactivation

Deactivate this skill when:

- The user explicitly asks to refactor for reuse or DRY extraction.
- The project has already committed to a layered/abstraction-heavy architecture and the task is within that existing pattern.
- The user explicitly requests a different coding style or priority.
