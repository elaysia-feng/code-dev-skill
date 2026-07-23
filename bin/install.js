#!/usr/bin/env node

/**
 * Install the readability-first-coding skill into a project or user config.
 *
 * Usage:
 *   readability-first-install                    # install to current project
 *   readability-first-install --global           # install to user's global skills
 *   readability-first-install /path/to/project   # install to specific project
 *
 * Default behaviour:
 *   - If a target path is given, install there.
 *   - If --global is used, install to ~/.claude/skills/.
 *   - Otherwise, install to ./.omc/skills/ (project-local).
 */

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');

const SKILL_NAME = 'readability-first-coding';

// Resolve the skill source directory (bundled inside the npm package).
const skillSrc = path.join(__dirname, '..', 'skills', SKILL_NAME);

function resolveTarget() {
  const args = process.argv.slice(2);

  if (args.includes('--global') || args.includes('-g')) {
    return path.join(os.homedir(), '.claude', 'skills', SKILL_NAME);
  }

  const explicitPath = args.find(a => !a.startsWith('-'));
  if (explicitPath) {
    const resolved = path.resolve(explicitPath);
    // If the path looks like a project root, install under .omc/skills/.
    if (fs.existsSync(path.join(resolved, '.git')) || fs.existsSync(path.join(resolved, '.omc'))) {
      return path.join(resolved, '.omc', 'skills', SKILL_NAME);
    }
    return resolved;
  }

  // Default: install to current project under .omc/skills/.
  return path.join(process.cwd(), '.omc', 'skills', SKILL_NAME);
}

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (entry.isDirectory() && entry.name === '__pycache__') {
      continue; // skip Python bytecode cache
    }

    if (entry.isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

function main() {
  if (!fs.existsSync(skillSrc)) {
    console.error(`ERROR: skill source not found at: ${skillSrc}`);
    console.error('This script must be run from the readability-first-coding npm package.');
    process.exit(1);
  }

  const target = resolveTarget();
  console.log(`Installing "${SKILL_NAME}"...`);

  copyDir(skillSrc, target);

  console.log(`Installed to: ${target}`);
  console.log('');
  console.log('The skill will be active for Claude Code in this project.');
  console.log('');
  console.log('Manual steps (optional):');
  console.log(`  Install pre-commit hook:  cp ${target}/scripts/pre-commit-check.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit`);
  console.log(`  Run smell checker:        python3 ${target}/scripts/check-abstraction-smell.py . --lang auto`);
}

main();
