# Changelog

All notable changes to this skill are recorded here. The version is kept in
sync between `package.json` and `plugin.json`; a release is incomplete unless
both are bumped.

## 1.3.3

Fixes three defects introduced by 1.3.1 and 1.3.2, all found by an independent
verification pass against the published package.

### Fixed

- **The commit gate could be bypassed.** `pre-commit-check.sh` passed the
  *working-tree* path to `check_comments.py`, so staging a violation and then
  cleaning up the working tree let it through (`EXIT=0`), and a clean commit was
  blocked when the working tree still held uncommitted edits. `check_comments.py`
  now has a `--staged` mode that reads the Git index, and the hook uses it. Both
  directions are covered by regression tests.
- **One legacy non-UTF-8 file blocked every commit.** The abstraction checker
  made undecodable files fatal, but computed `unreadable` over the whole
  repository instead of the selected scope — so a single GBK file anywhere made
  the gate unusable on exactly the legacy codebases this standard targets. The
  scope is now narrowed the same way the report is, keeping "selected but
  unreadable is fatal".
- **`--update` could delete the only copy of the installation.** It removed the
  target before renaming the staged copy into place; a failure between the two
  (process killed, antivirus holding a handle, power loss) left nothing. The old
  install is now moved aside as `.previous` and only deleted once the swap
  succeeds, with rollback on failure.
- A plain install (no `--update`) merged instead of replacing, so re-running it
  left files that upstream had deleted in place. Both paths now replace.
- `check_comments.py --staged` no longer claims "no checkable files" when it did
  check files and simply found nothing.

## 1.3.2

### Fixed

- `pre-commit-check.sh` ran only `check-abstraction-smell.py`. Comment rules —
  the bulk of what this skill actually specifies — had **no coverage at the commit
  gate at all**, while `check_comments.py` is the checker that carries ERROR
  semantics. It now runs both, over the staged Java/Python files only.
- The hook's documented contract was inaccurate once 1.3.1 made undecodable files
  fatal: it said "advisory by default", but a non-UTF-8 source file blocks even
  with `READABILITY_FAIL_ON=none`. The wording in the hook header, `SKILL.md`,
  `README.md` and the installer's output now states exactly what always blocks.

## 1.3.1

Source encoding is now an explicit part of the standard rather than an
unenforced side effect of the checkers.

### Changed

- **Source files must be UTF-8**, with or without a BOM. The standard required
  this in practice but never said so, which left the checkers enforcing a rule
  nobody had been told about.
- Both checkers now treat a file they cannot decode as a failed check rather than
  a clean one. `check-abstraction-smell.py` previously skipped such files
  silently, so an agent could report "no problems" about a file it had never
  read. It now lists them under `UNREADABLE` / `unreadable` and exits `2`.
  `count` still means "number of smells", so existing consumers of the JSON are
  unaffected.
- The unreadable message says what to do (`re-save it as UTF-8`) instead of
  reporting an opaque codec error.

## 1.3.0

The standard became **mandatory** rather than advisory, and the documentation
was translated to English. Code comments in this repository stay in Simplified
Chinese, because that is what the standard mandates for user projects.

### Breaking

- **The standard is now mandatory.** It applies to every personal project and is
  not lowered to match existing code style. The only exemption is a
  company-standards skill or project-level conventions file in the target
  project; that takes precedence and this standard falls back to being a
  reference.
- **Project structure is mandatory, not illustrative.** A project whose layout
  differs gets migrated, not exempted. `service/` is the only accepted package
  name (a project using `services/` must migrate), and the shared module is
  named `common-api/`.
- **Comments must be in Simplified Chinese**, including projects that currently
  use English comments. Rewriting is scoped to files the change touches — never
  a repository-wide sweep.
- `docstring` style is fixed to Google style, and an override that matches the
  interface behaviour must use `@inheritDoc`.

### Fixed

- `install.js --check` crashed on every invocation: it called `compareVersions`,
  which was only defined in `check-update.js`. Version comparison now lives in
  a shared `bin/version.js`.
- Pre-release versions compared incorrectly — `1.2.0-beta.1` was treated as equal
  to `1.2.0`. Comparison now follows semver precedence.
- `install.js --json` was accepted but silently ignored. It is now rejected; use
  `readability-first-check --json`, which is implemented.
- `--update` merged into the target directory, so files deleted upstream lingered
  forever in every user's installation. It now replaces the directory wholesale.
- `--update` could delete a directory belonging to a *different* skill. It now
  reads the target's `SKILL.md` `name:` and refuses unless it is `code-dev`;
  `--force` overrides deliberately.
- `--update` deleted the old installation before copying, so a failure mid-copy
  left a half-written directory. The new version is staged and swapped in only
  after a verified copy.
- `check_comments.py` reported a valid UTF-8 BOM Python file as `parse-error`
  while Python itself ran it fine. It now reads with `utf-8-sig`; the same fix
  was applied to all six read sites in `check-abstraction-smell.py`.
- The comment checker flagged comments that merely *mention* `TODO` mid-sentence,
  and missed `FIXME` / `XXX` entirely. Markers are now anchored to the start of
  a comment and all three are covered.
- The Chinese-comment rule flagged tool directives and boilerplate
  (`#!/usr/bin/env`, `# type: ignore`, generator headers, licence headers,
  `@author`, bare URLs) that cannot be translated without breaking something.
  Exemptions are anchored to line start, so English prose that happens to
  contain `copyright` or `generated by` is still caught.

### Changed

- Documentation translated to English; code examples keep their Simplified
  Chinese comments, since those demonstrate what compliant comments look like.
- `review-complexity` was removed. It fired on every method past a length
  threshold regardless of comment quality, so it could never be satisfied.
- `check_comments.py` gained a `non-chinese-comment` rule and exit-code
  documentation.
- The comment checker is now covered by the regression suite; the suite grew
  from 11 to 22 cases and covers installer safety, semver ordering and the
  checker's own rules.

### Removed

- `references/fastapi-langgraph.md` — zero inbound links, so it could never be
  loaded. Its content is covered by `python-guidelines.md`.
- The `review-complexity` rule (see above).

### Added

- `LICENSE` — MIT. It was declared in three places but no licence file existed.
- `bin/version.js` — shared semver comparison.
- Regression coverage for `--check`, semver precedence, stale-file cleanup,
  BOM handling, boilerplate exemptions and TODO anchoring.

## 1.2.0

Adopted the Agent Plugins 1.0.0 package format; added `plugin.json` as the
plugin manifest and moved the skill under `skills/code-dev/`.