---
name: readability-first-coding
description: >-
  Use this skill when implementing, modifying, reviewing, or refactoring Java or Python backend code.
  Prioritize readable and direct code, avoid unsolicited abstractions, and preserve duplicated business
  logic unless the user explicitly requests extraction or reuse.
triggers:
  - 可读性优先
  - 易读懂优先
  - 不要抽取
  - 不要抽象
  - 不要DRY
  - 不要公共模块
  - 保持重复
  - readability first
  - 写代码
  - 实现功能
  - 不要过度设计
  - 代码规范
  - 实现接口
  - 重构
  - review代码
  - 修改service
  - 写controller
  - 写service
  - 抽取公共
  - common模块
  - 公共模块
argument-hint: "[optional: Java | Python | Java microservices]"
allowed-tools: Read,Write,Edit,Glob,Grep
license: MIT
---

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
- Do not create `common`, `util`, `utils`, `shared`, `core`, `framework`, or `base` modules on your own (unless the user explicitly requests extraction — see "When Extraction IS Requested" below).
- Do not modify unrelated code.

# The Abstraction Gate

Before extracting any code, ask internally:

> **Did the user explicitly request this abstraction?**

If the answer is **No** → do not extract. No matter how many times the code repeats.

# Language-Specific Rules

| Language / Context | Reference File |
|---|---|
| Java backend | `references/java-guidelines.md` |
| Python backend | `references/python-guidelines.md` |
| Java microservices | `references/microservice-guidelines.md` |
| Directory layout | `references/project-structure.md` |
| Good/Bad examples | `references/examples.md` |

Load the relevant reference when starting work in that language or context.

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
10. Confirm the final code is easy to read top-to-bottom.

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

# Scripts

| Script | Purpose |
|---|---|
| `scripts/check-abstraction-smell.py` | Scan project for over-abstraction smells (single-impl interfaces, suspect packages, pass-through methods, deep inheritance, single-impl ABCs, Python pass-throughs) |
| `scripts/pre-commit-check.sh` | Git pre-commit hook that runs the smell checker against staged Java/Python files |

Run before committing:

```bash
python3 .omc/skills/readability-first-coding/scripts/check-abstraction-smell.py . --lang java
python3 .omc/skills/readability-first-coding/scripts/check-abstraction-smell.py . --lang python
python3 .omc/skills/readability-first-coding/scripts/check-abstraction-smell.py . --lang java --json  # machine-readable
```

If `python3` is not available, `python` (without the 3) usually works as well.

Install as git hook:

```bash
cp .omc/skills/readability-first-coding/scripts/pre-commit-check.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

# Assets

| Asset | Purpose |
|---|---|
| `assets/ide-settings.json` | IDE settings template that disables auto-refactoring features (organize imports, auto-cleanup) |

# Final Checks

Before completing any task:

- [ ] Did I create a shared method just to reduce duplication? → If yes, inline it back.
- [ ] Did I create a `common`, `util`, `utils`, `shared`, `core`, `framework`, or `base` module the user did not ask for? → If yes, delete it.
- [ ] Did I add unnecessary parent classes or interfaces? → If yes, delete them.
- [ ] Does understanding simple logic require jumping across multiple files? → If yes, inline.
- [ ] Did I modify unrelated code? → If yes, revert.
- [ ] Did I use a more complex approach than the task requires? → If yes, simplify.
- [ ] Can the code be read top-to-bottom? → If not, rewrite.

**If an abstraction reduces readability, delete the abstraction and restore direct code.**

# Core Rule (Repeated)

> **Unless the user explicitly requests it, never extract shared methods, utility classes, parent classes, or shared modules — no matter how many times the code repeats.**
>
> **Easy to understand > Directness > Easy to modify > Less duplication > Reusability > Abstraction > Architectural beauty.**
