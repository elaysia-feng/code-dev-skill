#!/usr/bin/env node

/**
 * Install the code-dev skill into a Claude Code project or user config.
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
const getRemoteVersion = require(path.join(__dirname, 'remote-version.js'));

const PACKAGE_NAME = 'readability-first-coding';
const SKILL_NAME = 'code-dev';
const GITHUB_PACKAGE_SPEC = 'github:elaysia-feng/code-dev-skill#main';

const skillSrc = path.join(__dirname, '..', 'skills', SKILL_NAME);

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

function getLocalVersion() {
  const pkgPath = path.join(__dirname, '..', 'package.json');
  if (!fs.existsSync(pkgPath)) return null;
  return JSON.parse(fs.readFileSync(pkgPath, 'utf8')).version;
}

async function doCheck() {
  const local = getLocalVersion();
  const remote = await getRemoteVersion();

  if (!remote) {
    console.error('ERROR: Could not fetch remote version. Check your network connection.');
    process.exit(2);
  }

  if (!local) {
    console.log(`Package "${PACKAGE_NAME}" is not installed locally.`);
    console.log(`Latest version: ${remote}`);
    console.log('\nInstall with: npm install github:elaysia-feng/code-dev-skill');
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
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'code-dev-update-'));
  try {
    execSync('npm install ' + GITHUB_PACKAGE_SPEC + ' --ignore-scripts --no-audit --no-fund --package-lock=false', {
      cwd: temp,
      timeout: 60000,
      stdio: 'inherit',
    });
    const freshRoot = path.join(temp, 'node_modules', PACKAGE_NAME);
    const freshSkill = path.join(freshRoot, 'skills', SKILL_NAME);
    const freshPackage = JSON.parse(fs.readFileSync(path.join(freshRoot, 'package.json'), 'utf8'));
    if (freshPackage.name !== PACKAGE_NAME || !freshPackage.version || !fs.existsSync(path.join(freshSkill, 'SKILL.md'))) {
      throw new Error('Updated package is incomplete');
    }
    copyDir(freshSkill, target);
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
  assertNoSymbolicPath(src);
  assertNoSymbolicPath(dest);
  if (!fs.lstatSync(src).isDirectory()) {
    throw new Error('Skill source is not a directory: ' + src);
  }
  fs.mkdirSync(dest, { recursive: true });
  assertNoSymbolicPath(dest);

  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (entry.isSymbolicLink()) {
      throw new Error('Refusing symbolic link in skill source: ' + srcPath);
    }

    if (entry.isDirectory() && (entry.name === '__pycache__' || entry.name === '.omc')) {
      continue; // skip Python bytecode cache and OMC runtime state
    }

    if (entry.isDirectory()) {
      copyDir(srcPath, destPath);
    } else if (entry.isFile()) {
      assertNoSymbolicPath(destPath);
      assertRegularUnlinkedFile(srcPath, 'skill source');
      assertRegularUnlinkedFileIfPresent(destPath, 'install target');
      fs.copyFileSync(srcPath, destPath);
    } else {
      throw new Error('Refusing unsupported file type in skill source: ' + srcPath);
    }
  }
}

function assertNoSymbolicPath(targetPath) {
  const absolute = path.resolve(targetPath);
  const root = path.parse(absolute).root;
  let current = root;

  for (const part of absolute.slice(root.length).split(path.sep).filter(Boolean)) {
    current = path.join(current, part);
    try {
      if (fs.lstatSync(current).isSymbolicLink()) {
        throw new Error('Refusing symbolic link in install path: ' + current);
      }
    } catch (error) {
      if (error.code === 'ENOENT') return;
      throw error;
    }
  }
}

function assertRegularUnlinkedFile(targetPath, description) {
  const stat = fs.lstatSync(targetPath);
  if (!stat.isFile() || stat.nlink > 1) {
    throw new Error('Refusing linked or non-regular ' + description + ': ' + targetPath);
  }
}

function assertRegularUnlinkedFileIfPresent(targetPath, description) {
  try {
    assertRegularUnlinkedFile(targetPath, description);
  } catch (error) {
    if (error.code === 'ENOENT') return;
    throw error;
  }
}

function main() {
  const args = process.argv.slice(2);

  if (args.includes('--check')) {
    doCheck().catch(reportError);
    return;
  }

  if (args.includes('--update') || args.includes('-U')) {
    doUpdate();
    return;
  }

  if (!fs.existsSync(skillSrc)) {
    console.error(`ERROR: skill source not found at: ${skillSrc}`);
    console.error('This command must be run from the readability-first-coding npm distribution package.');
    process.exit(1);
  }

  const target = resolveTarget();
  console.log(`Installing "${SKILL_NAME}"...`);

  copyDir(skillSrc, target);

  console.log(`Installed to: ${target}`);
  console.log('');
  console.log('Claude Code can discover the skill from .claude/skills/.');
  console.log(`Direct Claude Code trigger: /${SKILL_NAME}`);
  console.log('Codex trigger after installation to a Codex skill root: $code-dev');
  console.log('');
  console.log('Optional checks:');
  console.log('  Optional hook: merge scripts/pre-commit-check.sh into your existing hook; do not overwrite it.');
  console.log(`  Run smell checker:        python3 ${target}/scripts/check-abstraction-smell.py . --lang auto`);
}

function reportError(error) {
  console.error('ERROR: ' + error.message);
  process.exitCode = 2;
}

try { main(); } catch (error) { reportError(error); }
