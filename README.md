# code-dev

A **mandatory development standard** for Java/Spring, Python/FastAPI/LangGraph and TypeScript/Node.js projects. It unifies project structure, the shape of Java business interfaces and Simplified Chinese code comments, and sets the entry point and packaging requirements for publishable TypeScript npm packages.

The standard is mandatory: it applies to every personal project, and the bar is never lowered to match the existing code style. The only source of exemption is company standards — if the target project has a company-standards skill installed or a project-level conventions file, that takes precedence and this standard falls back to being a reference.

The skill name, the directory name and the explicit trigger name are all `code-dev`: Codex uses `$code-dev`, Claude Code uses `/code-dev`. The package name in `package.json` is temporarily kept as `readability-first-coding` as a compatibility identifier; installation fetches from GitHub and does not depend on a same-named package in the npm registry.

## Agent Plugins standard format

The repository is organized according to the [Agent Plugins 1.0.0 specification](https://agent-plugins.org/specification); `plugin.json` in the root directory is the plugin manifest, declaring the plugin name `code-dev`, the standard version and the publishing metadata. The skill entry point follows the [Agent Skills specification](https://agentskills.io/specification).

The core directories of the plugin are listed below; `scripts/`, `references/`, `assets/` and `evals/` stay inside the skill directory:

```text
code-dev-skill/
├── plugin.json
├── skills/
│   └── code-dev/
│       ├── SKILL.md
│       ├── scripts/
│       ├── references/
│       ├── assets/
│       └── evals/
├── package.json
└── bin/
```

Clients that support Agent Plugins 1.0.0 can load the repository root, or the root extracted from the npm package, as the plugin directory and discover `code-dev` under `skills/`. This plugin ships only the skill and contains no MCP server, so `mcp.json` is not required; `bin/` is a standalone installer.

Standard plugin loading and the single-skill installation below are two separate entry points: when loading the plugin, use the root directory that contains `plugin.json`; when installing the single skill, use `skills/code-dev/`. Whether a client supports this standard must be determined from that client's own documentation. Keep the versions of `plugin.json` and `package.json` in sync at release time.

## Installation and invocation

To install the package from GitHub in the target project directory and run the installer:

```sh
npm install github:elaysia-feng/code-dev-skill
npx readability-first-install
```

By default it installs into the project's `.claude/skills/code-dev/`, and the skill can be invoked directly with `/code-dev`. For Codex's global skill directory, install `skills/code-dev/` into `.agents/skills/code-dev/`, then trigger it with `$code-dev`.

For a user-level installation, run:

```sh
npx readability-first-install --global
```

Use `--target-dir` for a custom installation directory; the path must point at the skill directory itself. See the [installer](bin/install.js) for how the arguments are handled.

## Scope of application

- Implementing and reviewing Java / Python backends and TypeScript/Node.js code.
- Choosing how to organize services, interfaces and the data access layer based on the existing project.
- Keeping responsibilities and dependencies under control in microservice, FastAPI and LangGraph projects.
- Maintaining the comments touched by a change while editing code; read the package standards on demand when creating or maintaining a TS npm package.
- Judging when to inline directly and when a reusable standalone component is required.

Company standards take precedence over this standard; aside from that, this is a mandatory standard rather than a list of suggestions. The skill does not replace compilation, tests or human review; its checkers only provide leads, and every WARNING requires human judgement.

## Checking for updates

Checking and updating are two independent operations:

```sh
npx readability-first-check
npx readability-first-install --update
```

The checker supports `--json`. Exit code `0` means it is already up to date, `1` means an update is available, `2` means a network or tool error, `3` means it is not installed locally.

`--update` replaces the installed skill directory wholesale, so files that upstream deleted are cleaned up rather than lingering forever. Two safety rules apply:

- it refuses to replace a directory whose `SKILL.md` declares a different skill name — point `--target-dir` at the code-dev installation, or pass `--force` to overwrite deliberately;
- the new version is staged next to the target and swapped in only after a verified copy, so a failure mid-update leaves the working installation intact.

## Repository structure and validation

| Path | Contents |
| --- | --- |
| [Plugin manifest](plugin.json) | Agent Plugins 1.0.0 metadata and standard identity |
| [Skill entry point](skills/code-dev/SKILL.md) | Priority order, mandatory rules, and the load-on-demand routing table |
| `skills/code-dev/references/` | Detailed rules for Java, Python, TypeScript packages and comments |
| `skills/code-dev/assets/ide-settings.json` | Editor settings that stop tooling from rewriting the code this standard produces |
| `skills/code-dev/scripts/check_comments.py` | Heuristic Java/Python comment checker |
| `skills/code-dev/scripts/check-abstraction-smell.py` | Abstraction smell checker (single-implementation interfaces, small dumping packages, deep inheritance, pass-through methods) |
| `skills/code-dev/scripts/pre-commit-check.sh` | Optional git hook; advisory by default |
| `skills/code-dev/evals/` | Behaviour regression cases — **kept in the repository, excluded from the npm package** |
| `bin/` | Installer, update checker, and shared semver comparison |
| `tests/` | Tests for the installer, semver comparison, and both checkers |
| [LICENSE](LICENSE) | MIT |

### Validation

```sh
npm test                                    # regression suite
npx skills-ref validate ./skills/code-dev   # Agent Skills format validation
npm pack --dry-run --ignore-scripts         # inspect the actual published contents
```

`npm test` needs a Python interpreter. On Windows, pass an absolute path if `python` is not on `PATH`:

```sh
READABILITY_PYTHON=$(py -3 -c "import sys; print(sys.executable)") npm test
```
