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
const { compareVersions } = require(path.join(__dirname, 'version.js'));

const PACKAGE_NAME = 'readability-first-coding';
const SKILL_NAME = 'code-dev';
const GITHUB_PACKAGE_SPEC = 'github:elaysia-feng/code-dev-skill#main';

const skillSrc = path.join(__dirname, '..', 'skills', SKILL_NAME);

function resolveTarget() {
  const args = process.argv.slice(2);
  const allowed = new Set(['--global', '-g', '--check', '--update', '-U', '--target-dir', '--force']);
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
    replaceSkillDir(freshSkill, target, process.argv.slice(2).includes('--force'));
    if (!fs.readFileSync(path.join(target, 'SKILL.md')).equals(fs.readFileSync(path.join(freshSkill, 'SKILL.md')))) {
      throw new Error('Installed skill verification failed');
    }
    console.log('Installed v' + freshPackage.version + ' to: ' + target);
  } finally {
    // temp 由本进程创建，清理范围不依赖用户输入。
    fs.rmSync(temp, { recursive: true, force: true });
  }
}

/**
 * List every file under dir as a posix relative path, skipping symlinks.
 * Used only to report what an update is about to remove.
 */
function listFiles(dir, prefix = '') {
  let out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const rel = prefix ? prefix + '/' + entry.name : entry.name;
    if (entry.isSymbolicLink()) continue;
    if (entry.isDirectory()) {
      out = out.concat(listFiles(path.join(dir, entry.name), rel));
    } else if (entry.isFile()) {
      out.push(rel);
    }
  }
  return out;
}

/**
 * Report the skill name declared in a SKILL.md frontmatter block.
 * Returns null when the file is missing, unreadable or has no usable name.
 */
function readSkillName(dir) {
  try {
    const marker = path.join(dir, 'SKILL.md');
    if (!fs.existsSync(marker)) return null;
    const head = fs.readFileSync(marker, 'utf8').slice(0, 4096);
    const front = /^---\r?\n([\s\S]*?)\r?\n---/.exec(head);
    if (!front) return null;
    const name = /^name:\s*(.+?)\s*$/m.exec(front[1]);
    return name ? name[1].trim() : null;
  } catch {
    return null;
  }
}

/**
 * Replace the installed skill directory wholesale.
 *
 * Merging instead of replacing would leave files that upstream deleted still on
 * disk forever — a reference doc dropped in a later version would linger in every
 * user's installation.
 *
 * Two guards keep this from destroying the wrong directory:
 *  - The target must be an existing code-dev installation, identified by the
 *    `name:` in its own SKILL.md. "Some directory that happens to contain a
 *    SKILL.md" is not enough — --target-dir is a documented option and a typo
 *    can land on somebody else's skill. Set --force to override deliberately.
 *  - The new content is staged next to the target and only swapped in after a
 *    successful copy, so a failure mid-copy leaves the working installation
 *    untouched instead of a half-written directory.
 */
function replaceSkillDir(freshSkill, target, force) {
  assertNoSymbolicPath(target);
  const declared = readSkillName(target);

  if (declared === null) {
    // Not an installation at all: a fresh install must never delete anything.
    copyDir(freshSkill, target);
    return;
  }
  if (declared !== SKILL_NAME && !force) {
    throw new Error(
      'Refusing to replace ' + target + ': it holds a skill named "' + declared +
      '", not "' + SKILL_NAME + '". Point --target-dir at the code-dev ' +
      'installation, or pass --force if you really mean to overwrite it.');
  }

  const shipped = new Set(listFiles(freshSkill));
  const stale = listFiles(target).filter(rel => !shipped.has(rel));

  // 1. 先把新内容复制到同级暂存目录并校验，此时旧安装完全没被碰过
  const staging = target + '.incoming';
  const backup = target + '.previous';
  fs.rmSync(staging, { recursive: true, force: true });
  fs.rmSync(backup, { recursive: true, force: true });
  let movedAway = false;
  try {
    copyDir(freshSkill, staging);
    const stagedMarker = fs.readFileSync(path.join(staging, 'SKILL.md'));
    if (!stagedMarker.equals(fs.readFileSync(path.join(freshSkill, 'SKILL.md')))) {
      throw new Error('Staged skill verification failed before swap');
    }
    // 2. 把旧安装改名让位，而不是删除。Windows 上 rename 不能覆盖已存在的
    //    目录，所以"删了再 rename"在两者之间留了一个真实窗口：进程被杀、
    //    杀软占用、断电，都会让技能被完整删除且无从恢复。改名让位则把
    //    旧内容留到切换成功为止。
    if (fs.existsSync(target)) {
      fs.renameSync(target, backup);
      movedAway = true;
    }
    fs.renameSync(staging, target);
    if (movedAway) {
      fs.rmSync(backup, { recursive: true, force: true });
    }
  } catch (error) {
    fs.rmSync(staging, { recursive: true, force: true });
    // 切换失败就把旧安装放回去，不能让用户落到"完全没有技能"的状态
    if (movedAway && !fs.existsSync(target) && fs.existsSync(backup)) {
      try {
        fs.renameSync(backup, target);
      } catch (restoreError) {
        console.error('WARNING: could not restore the previous installation from ' +
          backup + ': ' + restoreError.message);
        throw error;
      }
    }
    throw error;
  }

  if (stale.length) {
    console.log('Removed entries that upstream no longer ships: ' + stale.join(', '));
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

  // 同样是整体替换：重装一次不应该把上游已经删掉的文件留在原地。
  // 首次安装（目标不存在或不是技能目录）时 replaceSkillDir 退化为普通复制。
  replaceSkillDir(skillSrc, target, args.includes('--force'));

  console.log(`Installed to: ${target}`);
  console.log('');
  console.log('Claude Code can discover the skill from .claude/skills/.');
  console.log(`Direct Claude Code trigger: /${SKILL_NAME}`);
  console.log('Codex trigger after installation to a Codex skill root: $code-dev');
  console.log('');
  console.log('Optional checks:');
  console.log('  Optional hook: merge scripts/pre-commit-check.sh into your existing hook;');
  console.log('    it checks staged files with both checkers; not overwriting your hook.');
  console.log(`  Run smell checker:        python3 ${target}/scripts/check-abstraction-smell.py . --lang auto`);
}

function reportError(error) {
  console.error('ERROR: ' + error.message);
  process.exitCode = 2;
}

try { main(); } catch (error) { reportError(error); }
