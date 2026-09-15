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
  const allowed = new Set(['--global', '-g', '--check', '--update', '-U', '--target-dir', '--json']);
  for (const arg of args) {
    if (arg.startsWith('-') && !allowed.has(arg)) throw new Error('Unknown option: ' + arg);
  }
  const direct = args.indexOf('--target-dir');
  const global = args.includes('--global') || args.includes('-g');
  const paths = args.filter(arg => !arg.startsWith('-'));
  if (paths.length > 1 || (global && paths.length)) throw new Error('Choose one install destination');
  if (direct >= 0) {
    if (!args[direct + 1] || args[direct + 1].startsWith('-')) {
      throw new Error('--target-dir requires a directory');
    }
    return path.resolve(args[direct + 1]);
  }
  if (global) return path.join(os.homedir(), '.claude', 'skills', SKILL_NAME);
  return path.join(path.resolve(paths[0] || process.cwd()), '.claude', 'skills', SKILL_NAME);
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
  const target = resolveTarget();
  // 在独立前缀安装新包，避免改动调用者的 package.json 或复用旧 npx 缓存。
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'readability-update-'));
  try {
    execSync('npm install readability-first-coding@latest --ignore-scripts --no-audit --no-fund --package-lock=false', {
      cwd: temp,
      timeout: 60000,
      stdio: 'inherit',
    });
    const freshRoot = path.join(temp, 'node_modules', SKILL_NAME);
    const freshSkill = path.join(freshRoot, 'skills', SKILL_NAME);
    const freshPackage = JSON.parse(fs.readFileSync(path.join(freshRoot, 'package.json'), 'utf8'));
    if (freshPackage.name !== SKILL_NAME || !freshPackage.version || !fs.existsSync(path.join(freshSkill, 'SKILL.md'))) {
      throw new Error('Updated package is incomplete');
    }
    copyDir(freshSkill, target);
    copyCommand(target, path.join(freshRoot, 'commands', COMMAND_NAME + '.md'));
    if (!fs.readFileSync(path.join(target, 'SKILL.md')).equals(fs.readFileSync(path.join(freshSkill, 'SKILL.md')))) {
      throw new Error('Installed skill verification failed');
    }
    console.log('Installed v' + freshPackage.version + ' to: ' + target);
  } finally {
    // temp 由本进程创建，清理范围不依赖用户输入。
    fs.rmSync(temp, { recursive: true, force: true });
  }
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
function copyCommand(target, source = commandSrc) {
  if (!fs.existsSync(source)) return;

  const globalTarget = path.join(os.homedir(), '.claude', 'skills', SKILL_NAME);
  if (target === globalTarget) {
    const cmdDest = path.join(os.homedir(), '.claude', 'commands', `${COMMAND_NAME}.md`);
    fs.mkdirSync(path.dirname(cmdDest), { recursive: true });
    fs.copyFileSync(source, cmdDest);
    console.log(`Installed slash command: /${COMMAND_NAME} -> ${cmdDest}`);
  } else {
    console.log(`Hint: to enable /${COMMAND_NAME} in a project, copy ${commandSrc} to <project>/.claude/commands/`);
  }
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
  copyCommand(target);

  console.log(`Installed to: ${target}`);
  console.log('');
  console.log('Claude Code can discover the skill from .claude/skills/.');
  console.log(`Direct command: /${SKILL_NAME}`);
  console.log(`Alias command:  /${COMMAND_NAME}`);
  console.log('');
  console.log('Optional checks:');
  console.log('  Optional hook: merge scripts/pre-commit-check.sh into your existing hook; do not overwrite it.');
  console.log(`  Run smell checker:        python3 ${target}/scripts/check-abstraction-smell.py . --lang auto`);
}

try { main(); } catch (error) {
  console.error('ERROR: ' + error.message);
  process.exitCode = 2;
}
