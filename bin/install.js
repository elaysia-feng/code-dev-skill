#!/usr/bin/env node

/**
 * Install the readability-first-coding skill into a project or user config.
 *
 * Usage:
 *   readability-first-install                    # install to current project
 *   readability-first-install --global           # install to user's global skills
 *   readability-first-install /path/to/project   # install to specific project
 *   readability-first-install --check            # check for updates (no install)
 *   readability-first-install --update           # pull latest and reinstall
 *   readability-first-install -U                 # shorthand for --update
 *
 * Default behaviour:
 *   - If a target path is given, install there.
 *   - If --global is used, install to ~/.claude/skills/.
 *   - Otherwise, install to ./.omc/skills/ (project-local).
 */

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { execSync } = require('node:child_process');

const SKILL_NAME = 'readability-first-coding';
const COMMAND_NAME = 'readability-first';

// Resolve the skill source directory (bundled inside the npm package).
const skillSrc = path.join(__dirname, '..', 'skills', SKILL_NAME);
const commandSrc = path.join(__dirname, '..', 'commands', `${COMMAND_NAME}.md`);

function resolveTarget() {
  const args = process.argv.slice(2);

  if (args.includes('--global') || args.includes('-g')) {
    return path.join(os.homedir(), '.claude', 'skills', SKILL_NAME);
  }

  // Skip all flags when looking for an explicit path
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

function compareVersions(a, b) {
  const pa = a.split('.').map(Number);
  const pb = b.split('.').map(Number);
  const len = Math.max(pa.length, pb.length);
  for (let i = 0; i < len; i++) {
    const av = pa[i] || 0;
    const bv = pb[i] || 0;
    if (av !== bv) return av - bv;
  }
  return 0;
}

function getLocalVersion() {
  const pkgPath = path.join(__dirname, '..', 'package.json');
  if (fs.existsSync(pkgPath)) {
    return JSON.parse(fs.readFileSync(pkgPath, 'utf8')).version;
  }
  return null;
}

function getRemoteVersion() {
  try {
    const out = execSync(`npm view ${SKILL_NAME} version`, {
      encoding: 'utf8',
      timeout: 15000,
      stdio: ['pipe', 'pipe', 'pipe'],
    }).trim();
    if (out) return out;
  } catch {
    // not on npm registry — fall through
  }

  // Fallback: git tags
  try {
    const repoUrl = 'https://github.com/elaysia-feng/code-dev-skill.git';
    const out = execSync(`git ls-remote --tags --refs ${repoUrl}`, {
      encoding: 'utf8',
      timeout: 15000,
      stdio: ['pipe', 'pipe', 'pipe'],
    }).trim();
    if (out) {
      const tags = out.split('\n').map(line => {
        const match = line.match(/refs\/tags\/v?(\d+\.\d+\.\d+)$/);
        return match ? match[1] : null;
      }).filter(Boolean);
      if (tags.length) {
        tags.sort(compareVersions);
        return tags[tags.length - 1];
      }
    }
  } catch {
    // git not available
  }

  return null;
}

function doCheck() {
  const local = getLocalVersion();
  const remote = getRemoteVersion();

  if (!remote) {
    console.error('ERROR: Could not fetch remote version. Check your network connection.');
    process.exit(2);
  }

  if (!local) {
    console.log(`Package "${SKILL_NAME}" is not installed locally.`);
    console.log(`Latest version: ${remote}`);
    console.log(`\nInstall with: npm install ${SKILL_NAME}`);
    process.exit(1);
  }

  const cmp = compareVersions(local, remote);
  if (cmp >= 0) {
    console.log(`You are up to date! (v${local})`);
  } else {
    console.log(`Update available: v${local} → v${remote}`);
    console.log(`\nRun: npx readability-first-install --update`);
  }
  process.exit(cmp >= 0 ? 0 : 1);
}

function doUpdate() {
  const local = getLocalVersion();
  console.log(`Current version: ${local || 'unknown'}`);
  console.log(`Pulling latest from npm...`);

  try {
    execSync(`npm install ${SKILL_NAME}@latest`, {
      encoding: 'utf8',
      timeout: 60000,
      stdio: 'inherit',
    });
  } catch {
    console.error('ERROR: Failed to update package. Try manually: npm install readability-first-coding@latest');
    process.exit(2);
  }

  if (!fs.existsSync(skillSrc)) {
    console.error(`ERROR: skill source not found at: ${skillSrc} after update.`);
    console.error('The npm package may be corrupted. Try: npm install readability-first-coding@latest');
    process.exit(2);
  }

  const newVersion = getLocalVersion();
  console.log(`\nUpdated: v${local || '?'} → v${newVersion || '?'}`);
  console.log('Reinstalling skill files...');

  // Re-run install to copy updated files
  const target = resolveTarget();
  copyDir(skillSrc, target);
  copyCommand(target);
  console.log(`Installed to: ${target}`);
  console.log('\nDone!');
}

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (entry.isDirectory() && (entry.name === '__pycache__' || entry.name === '.omc')) {
      continue; // skip Python bytecode cache and OMC runtime state
    }

    if (entry.isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

// Copy the /<COMMAND_NAME> slash command so users can trigger the skill from the REPL.
// Global installs go to ~/.claude/commands/; project installs only get a hint.
function copyCommand(target) {
  if (!fs.existsSync(commandSrc)) return;

  const globalTarget = path.join(os.homedir(), '.claude', 'skills', SKILL_NAME);
  if (target === globalTarget) {
    const cmdDest = path.join(os.homedir(), '.claude', 'commands', `${COMMAND_NAME}.md`);
    fs.mkdirSync(path.dirname(cmdDest), { recursive: true });
    fs.copyFileSync(commandSrc, cmdDest);
    console.log(`Installed slash command: /${COMMAND_NAME} -> ${cmdDest}`);
  } else {
    console.log(`Hint: to enable /${COMMAND_NAME} in a project, copy ${commandSrc} to <project>/.claude/commands/`);
  }
}

function main() {
  const args = process.argv.slice(2);

  // Handle --check flag
  if (args.includes('--check')) {
    doCheck();
    return;
  }

  // Handle --update / -U flag
  if (args.includes('--update') || args.includes('-U')) {
    doUpdate();
    return;
  }

  // Default: install
  if (!fs.existsSync(skillSrc)) {
    console.error(`ERROR: skill source not found at: ${skillSrc}`);
    console.error('This script must be run from the readability-first-coding npm package.');
    process.exit(1);
  }

  const target = resolveTarget();
  console.log(`Installing "${SKILL_NAME}"...`);

  copyDir(skillSrc, target);
  copyCommand(target);

  console.log(`Installed to: ${target}`);
  console.log('');
  console.log('The skill will be active for Claude Code in this project.');
  console.log('');
  console.log('Manual steps (optional):');
  console.log(`  Install pre-commit hook:  cp ${target}/scripts/pre-commit-check.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit`);
  console.log(`  Run smell checker:        python3 ${target}/scripts/check-abstraction-smell.py . --lang auto`);
}

main();
