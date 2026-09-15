const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const { spawnSync } = require('node:child_process');

const root = path.resolve(__dirname, '..');
const checker = path.join(root, 'skills/readability-first-coding/scripts/check-abstraction-smell.py');
const python = process.env.READABILITY_PYTHON || 'python';

function workspace(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'readability-test-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  return dir;
}

function write(dir, name, content) {
  const file = path.join(dir, name);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content);
}

function git(dir, ...args) {
  const result = spawnSync('git', ['-C', dir, ...args], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
}

function scan(dir, ...args) {
  const result = spawnSync(python, ['-X', 'utf8', checker, dir, '--json', ...args], { encoding: 'utf8' });
  assert.notEqual(result.status, null, result.error?.message);
  return { ...result, report: result.stdout ? JSON.parse(result.stdout) : null };
}

test('info 默认放行，warning 阈值不阻断 info', t => {
  const dir = workspace(t);
  write(dir, 'wrapper.py', 'def run():\n    return service.run()\n');
  for (const args of [[], ['--fail-on', 'warning']]) {
    const result = scan(dir, ...args);
    assert.equal(result.status, 0, result.stderr);
    assert.ok(result.report.smells.some(s => s.severity === 'info'));
  }
  assert.equal(scan(dir, '--fail-on', 'info').status, 1);
});

test('warning 仅在显式阈值下阻断', t => {
  const dir = workspace(t);
  write(dir, 'contract.py', 'from abc import ABC\nclass Contract(ABC):\n    pass\n');
  assert.equal(scan(dir).status, 0);
  assert.equal(scan(dir, '--fail-on', 'warning').status, 1);
});

test('暂存版本保留问题，即使工作区已经修改为无问题代码', t => {
  const dir = workspace(t);
  git(dir, 'init', '-q');
  write(dir, '中文 路径.py', 'def run():\n    return service.run()\n');
  git(dir, 'add', '.');
  write(dir, '中文 路径.py', 'value = 1\n');
  const result = scan(dir, '--staged', '--fail-on', 'info');
  assert.equal(result.status, 1, result.stderr);
  assert.ok(result.report.smells.some(s => s.file === '中文 路径.py'));
  assert.equal(scan(dir, '--fail-on', 'info').status, 0);
});

test('暂存内容干净时忽略工作区新增 smell', t => {
  const dir = workspace(t);
  git(dir, 'init', '-q');
  write(dir, 'clean.py', 'value = 1\n');
  git(dir, 'add', '.');
  write(dir, 'clean.py', 'def run():\n    return service.run()\n');
  assert.equal(scan(dir, '--staged', '--fail-on', 'info').status, 0);
});

test('报告过滤不丢失未选择的实现，也不报告无关小包', t => {
  const dir = workspace(t);
  write(dir, 'Port.java', 'public interface Port {}\n');
  write(dir, 'One.java', 'public class One implements Port {}\n');
  write(dir, 'Two.java', 'public class Two implements Port {}\n');
  write(dir, 'common/old.py', 'value = 1\n');
  const result = scan(dir, '--files', 'Port.java', '--fail-on', 'info');
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.report.count, 0);
});

test('暂存扫描不报告已提交且未修改的小包', t => {
  const dir = workspace(t);
  git(dir, 'init', '-q');
  write(dir, 'common/old.py', 'value = 1\n');
  git(dir, 'add', '.');
  git(dir, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture');
  write(dir, 'new.py', 'value = 2\n');
  git(dir, 'add', '.');
  assert.equal(scan(dir, '--staged', '--fail-on', 'info').status, 0);
});

test('语言过滤与无效文件路径', t => {
  const dir = workspace(t);
  write(dir, 'wrapper.py', 'def run():\n    return service.run()\n');
  assert.equal(scan(dir, '--lang', 'java', '--fail-on', 'info').report.count, 0);
  assert.equal(scan(dir, '--files', '../missing.py').status, 2);
  assert.equal(scan(dir, '--staged', '--files', 'wrapper.py').status, 2);
});

function installer(dir, args, download) {
  const logs = [];
  const fakeProcess = { argv: ['node', 'install.js', ...args], cwd: () => dir, exitCode: 0 };
  const context = {
    __dirname: path.join(root, 'bin'), process: fakeProcess,
    console: { log: s => logs.push(s), error: s => logs.push(s) },
    require: name => {
      if (name === 'node:os') return { ...os, homedir: () => path.join(dir, 'home') };
      if (name === 'node:child_process') return { execSync: download };
      return require(name);
    },
  };
  vm.runInNewContext(fs.readFileSync(path.join(root, 'bin/install.js'), 'utf8'), context);
  return { status: fakeProcess.exitCode, logs };
}

test('目录参数始终表示项目根目录，直接目录选项独立', t => {
  const dir = workspace(t);
  assert.equal(installer(dir, []).status, 0);
  assert.ok(fs.existsSync(path.join(dir, '.claude/skills/readability-first-coding/SKILL.md')));
  const project = path.join(dir, 'new-project');
  assert.equal(installer(dir, [project]).status, 0);
  assert.ok(fs.existsSync(path.join(project, '.claude/skills/readability-first-coding/SKILL.md')));
  const direct = path.join(dir, 'direct');
  assert.equal(installer(dir, ['--target-dir', direct]).status, 0);
  assert.ok(fs.existsSync(path.join(direct, 'SKILL.md')));
  assert.equal(installer(dir, ['--target-dir']).status, 2);
  assert.equal(installer(dir, ['--global', direct]).status, 2);
});

test('更新从新包复制技能及全局命令，调用者依赖文件保持原样', t => {
  const dir = workspace(t);
  write(dir, 'package.json', '{"private":true}');
  let temporary;
  const result = installer(dir, ['--update', '--global'], (command, options) => {
    temporary = options.cwd;
    assert.notEqual(temporary, dir);
    assert.match(command, /--ignore-scripts/);
    const fresh = path.join(temporary, 'node_modules/readability-first-coding');
    write(fresh, 'package.json', '{"name":"readability-first-coding","version":"9.0.0"}');
    write(fresh, 'skills/readability-first-coding/SKILL.md', 'new skill');
    write(fresh, 'commands/readability-first.md', 'new command');
  });
  assert.equal(result.status, 0, result.logs.join('\n'));
  assert.equal(fs.readFileSync(path.join(dir, 'home/.claude/skills/readability-first-coding/SKILL.md'), 'utf8'), 'new skill');
  assert.equal(fs.readFileSync(path.join(dir, 'home/.claude/commands/readability-first.md'), 'utf8'), 'new command');
  assert.equal(fs.readFileSync(path.join(dir, 'package.json'), 'utf8'), '{"private":true}');
  assert.ok(result.logs.some(s => s.includes('9.0.0')));
  assert.equal(fs.existsSync(temporary), false);
});

test('下载失败保留原技能并返回错误', t => {
  const dir = workspace(t);
  write(dir, '.claude/skills/readability-first-coding/SKILL.md', 'existing');
  const result = installer(dir, ['--update'], () => { throw new Error('offline'); });
  assert.equal(result.status, 2);
  assert.equal(fs.readFileSync(path.join(dir, '.claude/skills/readability-first-coding/SKILL.md'), 'utf8'), 'existing');
});

test('Git Bash hook 实际调用检查器并传递严重程度阈值', t => {
  const dir = workspace(t);
  git(dir, 'init', '-q');
  write(dir, '中文 wrapper.py', 'def run():\n    return service.run()\n');
  git(dir, 'add', '.');
  const bash = process.env.READABILITY_BASH || (process.platform === 'win32'
    ? 'C:/Program Files/Git/bin/bash.exe' : 'bash');
  const hook = path.join(root, 'skills/readability-first-coding/scripts/pre-commit-check.sh');
  for (const [threshold, expected] of [['none', 0], ['warning', 0], ['info', 1]]) {
    const result = spawnSync(bash, [hook], {
      cwd: dir, encoding: 'utf8',
      env: { ...process.env, READABILITY_PYTHON: python, READABILITY_FAIL_ON: threshold },
    });
    assert.equal(result.status, expected, result.stderr || result.error?.message);
    assert.match(result.stdout, /python_pass_through|pass-through/i);
  }
});
