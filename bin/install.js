#!/usr/bin/env node

/**
 * Install the readability-first-coding skill into a Claude Code project or user config.
 *
 * Usage:
 *   readability-first-install                    # project -> ./.claude/skills/
 *   readability-first-install --global           # user -> ~/.claude/skills/
 *   readability-first-install /path/to/project   # project -> <path>/.claude/skills/
 *   readability-first-install --check
 *   readability-first-install --update
 *   readability-first-install -U
 */

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { execSync } = require('node:child_process');

const SKILL_NAME = 'readability-first-coding';
const COMMAND_NAME = 'readability-first';

const skillSrc = path.join(__dirname, '..', 'skills', SKILL_NAME);
const commandSrc = path.join(__dirname, '..', 'commands', `${COMMAND_NAME}.md`);

function resolveTarget() {
  const args = process.argv.slice(2);

  if (args.includes('--global') || args.includes('-g')) {
    return path.join(os.homedir(), '.claude', 'skills', SKILL_NAME);
  }

  const explicitProjectPath = args.find(arg => !arg.startsWith('-'));
  if (explicitProjectPath) {
    const projectRoot = path.resolve(explicitProjectPath);
    return path.join(projectRoot, '.claude', 'skills', SKILL_NAME);
  }

  return path.join(process.cwd(), '.claude', 'skills', SKILL_NAME);
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
  if (!fs.existsSync(pkgPath)) return null;
  return JSON.parse(fs.readFileSync(pkgPath, 'utf8')).version;
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
    // Fall back to git tags.
  }

  try {
    const repoUrl = 'https://github.com/elaysia-feng/code-dev-skill.git';
    const out = execSync(`git ls-remote --tags --refs ${repoUrl}`, {
      encoding: 'utf8',
      timeout: 15000,
      stdio: ['pipe', 'pipe', 'pipe'],
    }).trim();

    if (out) {
      const tags = out
        .split('\n')
        .map(line => {
          const match = line.match(/refs\/tags\/v?(\d+\.\d+\.\d+)$/);
          return match ? match[1] : null;
        })
        .filter(Boolean);

      if (tags.length) {
        tags.sort(compareVersions);
        return tags[tags.length - 1];
      }
    }
  } catch {
    // git may be unavailable.
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
    process.exit(3);
  }

  const cmp = compareVersions(local, remote);
  if (cmp >= 0) {
    console.log(`You are up to date! (v${local})`);
    process.exit(0);
  }

  console.log(`Update available: v${local} -> v${remote}`);
  console.log(`\nRun: npx readability-first-install --update`);
  process.exit(1);
}

function doUpdate() {
  const local = getLocalVersion();
  console.log(`Current version: ${local || 'unknown'}`);
  console.log('Pulling latest from npm...');

  try {
    execSync(`npm install ${SKILL_NAME}@latest`, {
      encoding: 'utf8',
      timeout: 60000,
      stdio: 'inherit',
    });
  } catch {
    console.error('ERROR: Failed to update package. Try: npm install readability-first-coding@latest');
    process.exit(2);
  }

  if (!fs.existsSync(skillSrc)) {
    console.error(`ERROR: skill source not found at: ${skillSrc} after update.`);
    process.exit(2);
  }

  const newVersion = getLocalVersion();
  console.log(`\nUpdated: v${local || '?'} -> v${newVersion || '?'}`);

  const target = resolveTarget();
  copyDir(skillSrc, target);
  copyCommandAlias(target);
  console.log(`Installed to: ${target}`);
  console.log('\nDone!');
}

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });

  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (entry.isDirectory() && entry.name === '__pycache__') {
      continue;
    }

    if (entry.isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

function getClaudeRootFromSkillTarget(target) {
  const skillsDir = path.dirname(target);
  if (path.basename(skillsDir) !== 'skills') return null;

  const claudeDir = path.dirname(skillsDir);
  if (path.basename(claudeDir) !== '.claude') return null;

  return claudeDir;
}

// The skill itself is directly invocable as /readability-first-coding.
// Keep /readability-first as a shorter compatibility alias.
function copyCommandAlias(target) {
  if (!fs.existsSync(commandSrc)) return;

  const claudeRoot = getClaudeRootFromSkillTarget(target);
  if (!claudeRoot) return;

  const commandDest = path.join(claudeRoot, 'commands', `${COMMAND_NAME}.md`);
  fs.mkdirSync(path.dirname(commandDest), { recursive: true });
  fs.copyFileSync(commandSrc, commandDest);
  console.log(`Installed alias: /${COMMAND_NAME} -> ${commandDest}`);
}

function main() {
  const args = process.argv.slice(2);

  if (args.includes('--check')) {
    doCheck();
    return;
  }

  if (args.includes('--update') || args.includes('-U')) {
    doUpdate();
    return;
  }

  if (!fs.existsSync(skillSrc)) {
    console.error(`ERROR: skill source not found at: ${skillSrc}`);
    console.error('This command must be run from the readability-first-coding npm package.');
    process.exit(1);
  }

  const target = resolveTarget();
  console.log(`Installing "${SKILL_NAME}"...`);

  copyDir(skillSrc, target);
  copyCommandAlias(target);

  console.log(`Installed to: ${target}`);
  console.log('');
  console.log('Claude Code can discover the skill from .claude/skills/.');
  console.log(`Direct command: /${SKILL_NAME}`);
  console.log(`Alias command:  /${COMMAND_NAME}`);
  console.log('');
  console.log('Optional checks:');
  console.log(`  python3 ${target}/scripts/check-abstraction-smell.py . --lang auto`);
}

main();
