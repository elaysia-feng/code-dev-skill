# readability-first-coding

Claude Code skill — prioritize readable, direct code over unsolicited abstractions for **Java**, **Python (FastAPI + LangGraph)**, and **Java microservice** backends.

## Install

```bash
npm install readability-first-coding
npx readability-first-install             # project-local → ./.omc/skills/
npx readability-first-install --global    # global → ~/.claude/skills/
```

Claude Code auto-discovers skills under `.claude/skills/`. No marketplace required.

### Slash command (Claude Code)

`--global` also installs a `/readability-first` custom command to `~/.claude/commands/`, so you can force the skill on directly from the REPL:

```bash
/readability-first 给这个 Java 服务加一个订单取消接口
/readability-first Python (FastAPI + LangGraph) 实现一个查询接口
```

For a project-scoped command (non-global install), copy it manually:

```bash
cp commands/readability-first.md .claude/commands/
```

> **Note:** Skills normally auto-trigger on the keywords below; the slash command just forces the mode on explicitly. Codex CLI has no custom slash commands — use the keyword triggers there.

## Update

```bash
# Check for updates
npx readability-first-check
npx readability-first-check --json        # machine-readable output
npx readability-first-install --check     # same, via install script

# Pull latest and reinstall skill files
npx readability-first-install --update
npx readability-first-install -U          # shorthand
```

`--check` compares your local version against the latest on npm/git and prints whether an update is available. `--update` runs `npm install readability-first-coding@latest`, then copies the new skill files over the existing ones.

### Check exit codes

| Code | Meaning |
|------|---------|
| 0 | Up to date |
| 1 | Update available |
| 2 | Error (network, missing tooling) |
| 3 | Package not installed locally |

## Philosophy

```
Easy to understand
> Directness
> Easy to modify
> Less duplication
> Reusability
> Abstraction
> Architectural beauty
```

Readable code that tells its story top-to-bottom in a single file beats clever abstractions spread across five files. Correctness is mandatory and never compromised — readability never justifies bugs.

## The Core Rule

> **Unless the user explicitly requests it, never extract shared methods, utility classes, parent classes, or shared modules — no matter how many times the code repeats.**

If the user didn't ask for an abstraction, don't create one. Duplicated business logic is allowed. Keep code close to where it's used.

## What It Does

- Implements only what you asked for — no extra abstraction layers
- Keeps duplicated business logic duplicated unless you explicitly request extraction
- Forbids unsolicited `common`, `util`, `utils`, `shared`, `framework`, `helpers`, `extensions`, `support`, `infrastructure`, `base` modules. `core/` is allowed **only** as FastAPI + LangGraph infrastructure (`config.py`, `llm.py`, `middleware.py`, `langgraph/`)
- Forbids `BaseGraph` / `BaseState` / `BaseAgent` for LangGraph
- Writes code that reads top-to-bottom, with business logic inline

## Language-Specific Rules

| Stack | Reference |
|---|---|
| Java backend | `references/java-guidelines.md` |
| Python backend (FastAPI + LangGraph) | `references/python-guidelines.md` |
| Java microservices | `references/microservice-guidelines.md` |
| Directory layout | `references/project-structure.md` |
| Good/Bad examples | `references/examples.md` |

### Python (FastAPI + LangGraph) Layout

```
src/
├── main.py                # FastAPI entry
├── api/v1/                # APIRoute handlers
├── core/
│   ├── config.py          # pydantic-settings
│   ├── llm.py             # LLM clients
│   ├── middleware.py
│   └── langgraph/         # state.py, nodes.py, tools.py, graph.py
├── graphs/                # one compiled StateGraph per file
├── schemas/               # Pydantic request/response
├── services/              # business logic (talks to models/ directly)
├── models/                # SQLModel / SQLAlchemy ORM
└── memory/                # mem0 / pgvector (optional)
```

Naming follows LangGraph official terms — `graphs/` aligns with the `graphs` key in `langgraph.json`.

## Triggers

The skill activates when your prompt contains keywords like:

| Trigger | Meaning |
|---|---|
| `/readability-first` | Force-activate via Claude Code slash command |
| `可读性优先` / `readability first` | Activate readability-first mode |
| `易读懂优先` | Prioritize easy-to-read code |
| `不要抽取` / `不要抽象` / `不要DRY` | Don't extract or abstract |
| `不要公共模块` / `不要过度设计` | Don't create shared modules |
| `保持重复` | Keep duplication |
| `抽取公共` / `common模块` / `公共模块` | User explicitly wants extraction |

## Scripts

| Script | Purpose |
|---|---|
| `scripts/check-abstraction-smell.py` | Scan for over-abstraction: single-impl interfaces, pass-through methods, deep inheritance, single-impl ABCs |
| `scripts/pre-commit-check.sh` | Git pre-commit hook wrapping the smell checker |

```bash
python3 skills/readability-first-coding/scripts/check-abstraction-smell.py . --lang java
python3 skills/readability-first-coding/scripts/check-abstraction-smell.py . --lang python
python3 skills/readability-first-coding/scripts/check-abstraction-smell.py . --lang java --json
```

Install as git hook:

```bash
cp skills/readability-first-coding/scripts/pre-commit-check.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## Structure

```
skills/readability-first-coding/
├── SKILL.md
├── assets/ide-settings.json
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

## License

MIT © [elaysia-feng](https://github.com/elaysia-feng)

## Links

- [GitHub Repository](https://github.com/elaysia-feng/code-dev-skill)
- [npm Package](https://www.npmjs.com/package/readability-first-coding)