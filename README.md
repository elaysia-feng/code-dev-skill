# readability-first-coding

A project-aware coding skill for **Java/Spring**, **Java microservices**, **Python/FastAPI**, and **LangGraph** application code.

The goal is not "never abstract". The rule is:

> Prefer the simplest structure that fits the real project, and require a concrete reason before adding indirection.

Existing project conventions take precedence over greenfield defaults.

## Install

```bash
npm install readability-first-coding
```

Project-local Claude Code skill:

```bash
npx readability-first-install
```

Installs to:

```text
<project>/.claude/skills/readability-first-coding/
```

Global installation:

```bash
npx readability-first-install --global
```

Installs to:

```text
~/.claude/skills/readability-first-coding/
```

The installer also creates the shorter `/readability-first` command alias under `.claude/commands/`.

Claude Code can invoke the skill directly as:

```text
/readability-first-coding
```

or through the compatibility alias:

```text
/readability-first
```

## Update

```bash
npx readability-first-check
npx readability-first-check --json
npx readability-first-install --check
npx readability-first-install --update
npx readability-first-install -U
```

Exit codes:

| Code | Meaning |
|---|---|
| 0 | Up to date |
| 1 | Update available |
| 2 | Network/tooling error |
| 3 | Package not installed locally |

## What the skill optimizes for

```text
Existing project consistency
> Easy to understand
> Directness
> Easy to modify
> Fewer unnecessary dependencies
> Less duplication
> Reusability
> Architectural elegance
```

The skill does **not** blindly reject interfaces, repositories, shared modules, enums, factories, or thin boundaries. It rejects them when they add indirection without owning meaningful behavior.

Concrete reasons for abstraction include:

- an existing project convention
- multiple real implementations
- a stable shared invariant/technical concern
- a framework/integration boundary
- an explicit user request

## Java defaults

For a new/simple Spring package with one implementation, a concrete service is enough:

```java
@Service
public class OrderService {
    public void cancelOrder(Long orderId) {
        // business logic
    }
}
```

If the surrounding project consistently uses `Service` + `ServiceImpl` for services, the skill follows that convention instead of fighting it.

Domain enums are valid when they model real states:

```java
public enum OrderStatus {
    PENDING,
    PAID,
    CANCELLED
}
```

The thing to avoid is a generic global `CommonConstants`/`CommonEnums` dumping ground.

## Python / FastAPI defaults

Recommended package shape for a non-trivial application:

```text
src/
└── app/
    ├── __init__.py
    ├── main.py
    ├── api/
    ├── core/
    ├── graphs/
    ├── schemas/
    ├── services/
    └── models/
```

Directories are optional; create only what the application actually needs.

Do not add `utils/`, `common/`, `repositories/`, or other generic layers just because a template has them. If the existing project already uses one, preserve it consistently.

## LangGraph structure

Small graph:

```text
graphs/
└── research_assistant.py
```

Keep state, a few small nodes, routing, and composition together when that is easiest to read.

Complex graph:

```text
graphs/
└── research_assistant/
    ├── __init__.py
    ├── graph.py
    ├── state.py
    ├── nodes/
    │   ├── __init__.py
    │   ├── plan.py
    │   ├── retrieve.py
    │   ├── grade_documents.py
    │   └── generate_answer.py
    ├── tools.py
    └── prompts.py              # optional
```

Rules:

- one meaningful node per file when a graph becomes complex
- graph-specific state/nodes/tools stay with that graph
- shared `core/langgraph/` code exists only when multiple graphs genuinely reuse it
- `__init__.py` stays empty or contains lightweight exports only
- do not compile graphs, connect databases, load large models, or perform network calls from `__init__.py`

## Skill structure

```text
code-dev-skill/
├── README.md
├── package.json
├── bin/
│   ├── install.js
│   └── check-update.js
├── commands/
│   └── readability-first.md
└── skills/
    └── readability-first-coding/
        ├── SKILL.md
        ├── assets/
        │   └── ide-settings.json
        ├── evals/
        │   ├── evals.json
        │   └── trigger-evals.json
        ├── references/
        │   ├── examples.md
        │   ├── java-guidelines.md
        │   ├── microservice-guidelines.md
        │   ├── project-structure.md
        │   └── python-guidelines.md
        └── scripts/
            ├── check-abstraction-smell.py
            └── pre-commit-check.sh
```

### `SKILL.md`

Small source-of-truth entry point: priorities, abstraction gate, workflow, and reference routing.

### `references/`

Detailed rules loaded only when relevant:

| File | Purpose |
|---|---|
| `java-guidelines.md` | Java/Spring conventions |
| `python-guidelines.md` | FastAPI + LangGraph conventions |
| `microservice-guidelines.md` | Cross-service boundaries and shared-code rules |
| `project-structure.md` | Directory/package layouts |
| `examples.md` | Representative good/bad shapes |

### `evals/`

Behavior/activation regression cases for checking that the skill remains useful after edits.

### `scripts/`

Best-effort static checks for abstraction smells. Findings are review prompts, not architectural truth.

## Smell checker

```bash
python3 skills/readability-first-coding/scripts/check-abstraction-smell.py . --lang java
python3 skills/readability-first-coding/scripts/check-abstraction-smell.py . --lang python
python3 skills/readability-first-coding/scripts/check-abstraction-smell.py . --lang auto
```

The checker is intentionally heuristic. Existing project conventions and explicitly requested abstractions can legitimately produce warnings.

## License

MIT © elaysia-feng
