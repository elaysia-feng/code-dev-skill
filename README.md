# readability-first-coding

Claude Code skill — prioritize readable, direct code over unsolicited abstractions for Java & Python backends.

## Install

```bash
npm install readability-first-coding
npx readability-first-install             # project-local → ./.omc/skills/
npx readability-first-install --global    # global → ~/.claude/skills/
```

Claude Code auto-discovers skills under `.claude/skills/`. No marketplace required.

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

## What It Does

- Implements only what you asked for — no extra abstraction layers
- Keeps duplicated business logic duplicated unless you explicitly request extraction
- Never creates `common`, `util`, `utils`, `shared`, `core`, `framework`, or `base` modules on its own
- Writes code that reads top-to-bottom, with business logic inline

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/check-abstraction-smell.py` | Scan for over-abstraction: single-impl interfaces, pass-through methods, deep inheritance, single-impl ABCs |
| `scripts/pre-commit-check.sh` | Git pre-commit hook wrapping the smell checker |

```bash
python3 skills/readability-first-coding/scripts/check-abstraction-smell.py . --lang java
python3 skills/readability-first-coding/scripts/check-abstraction-smell.py . --lang python
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

MIT
