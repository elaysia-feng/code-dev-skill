const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const { spawnSync } = require('node:child_process');

const root = path.resolve(__dirname, '..');
const checker = path.join(root, 'skills/code-dev/scripts/check-abstraction-smell.py');
const commentChecker = path.join(root, 'skills/code-dev/scripts/check_comments.py');
const python = process.env.READABILITY_PYTHON || 'python';

function scanComments(dir) {
  const result = spawnSync(python, ['-X', 'utf8', commentChecker, dir], { encoding: 'utf8' });
  const output = (result.stdout || '') + (result.stderr || '');
  return {
    status: result.status,
    lines: output.split(/\r?\n/).filter(Boolean),
    codes: [...output.matchAll(/\[([a-z][\w-]*)\]/g)].map(m => m[1]),
    output,
  };
}

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

const EXIT_SIGNAL = Symbol('process.exit');

function installer(dir, args, download) {
  const logs = [];
  const fakeProcess = {
    argv: ['node', 'install.js', ...args], cwd: () => dir, exitCode: 0,
    // 真实 process.exit() 会终止执行；测试桩用异常模拟，
    // 否则 install.js 里所有 process.exit(...) 分支在测试中永远不可达。
    exit(code) { this.exitCode = code; throw { [EXIT_SIGNAL]: true }; },
  };
  const context = {
    __dirname: path.join(root, 'bin'), process: fakeProcess,
    console: { log: s => logs.push(s), error: s => logs.push(s) },
    require: name => {
      if (name === 'node:os') return { ...os, homedir: () => path.join(dir, 'home') };
      if (name === 'node:child_process') return { execSync: download };
      return require(name);
    },
  };
  try {
    vm.runInNewContext(fs.readFileSync(path.join(root, 'bin/install.js'), 'utf8'), context);
  } catch (error) {
    if (!error || !error[EXIT_SIGNAL]) throw error;
  }
  return { status: fakeProcess.exitCode, logs };
}

test('目录参数始终表示项目根目录，直接目录选项独立', t => {
  const dir = workspace(t);
  assert.equal(installer(dir, []).status, 0);
  assert.ok(fs.existsSync(path.join(dir, '.claude/skills/code-dev/SKILL.md')));
  const project = path.join(dir, 'new-project');
  assert.equal(installer(dir, [project]).status, 0);
  assert.ok(fs.existsSync(path.join(project, '.claude/skills/code-dev/SKILL.md')));
  const direct = path.join(dir, 'direct');
  assert.equal(installer(dir, ['--target-dir', direct]).status, 0);
  assert.ok(fs.existsSync(path.join(direct, 'SKILL.md')));
  assert.equal(installer(dir, ['--target-dir']).status, 2);
  assert.equal(installer(dir, ['--global', direct]).status, 2);
});

test('更新从新包复制 code-dev 技能，调用者依赖文件保持原样', t => {
  const dir = workspace(t);
  write(dir, 'package.json', '{"private":true}');
  let temporary;
  const result = installer(dir, ['--update', '--global'], (command, options) => {
    temporary = options.cwd;
    assert.notEqual(temporary, dir);
    assert.match(command, /--ignore-scripts/);
    const fresh = path.join(temporary, 'node_modules/readability-first-coding');
    write(fresh, 'package.json', '{"name":"readability-first-coding","version":"9.0.0"}');
    write(fresh, 'skills/code-dev/SKILL.md', 'new skill');
  });
  assert.equal(result.status, 0, result.logs.join('\n'));
  assert.equal(fs.readFileSync(path.join(dir, 'home/.claude/skills/code-dev/SKILL.md'), 'utf8'), 'new skill');
  assert.equal(fs.readFileSync(path.join(dir, 'package.json'), 'utf8'), '{"private":true}');
  assert.ok(result.logs.some(s => s.includes('9.0.0')));
  assert.equal(fs.existsSync(temporary), false);
});

test('下载失败保留原技能并返回错误', t => {
  const dir = workspace(t);
  write(dir, '.claude/skills/code-dev/SKILL.md', 'existing');
  const result = installer(dir, ['--update'], () => { throw new Error('offline'); });
  assert.equal(result.status, 2);
  assert.equal(fs.readFileSync(path.join(dir, '.claude/skills/code-dev/SKILL.md'), 'utf8'), 'existing');
});

test('版本比较遵循 semver 优先级，预发布版低于正式版', () => {
  const { compareVersions } = require(path.join(root, 'bin/version.js'));
  const cases = [
    ['1.2.0-beta.1', '1.2.0', -1],
    ['1.2.0', '1.2.0', 0],
    ['1.2.0', '1.2.1', -1],
    ['1.2.0-beta.2', '1.2.0-beta.10', -1],
    ['1.2.0-rc.1', '1.2.0-beta.1', 1],
    ['2.0.0', '1.9.9', 1],
    ['1.2.0+build', '1.2.0', 0],
  ];
  for (const [a, b, want] of cases) {
    assert.equal(Math.sign(compareVersions(a, b)), want, `${a} vs ${b}`);
  }
});

test('install.js --check 不再因缺少 compareVersions 崩溃', () => {
  const result = spawnSync(process.execPath, [path.join(root, 'bin/install.js'), '--check'],
    { encoding: 'utf8' });
  const output = (result.stdout || '') + (result.stderr || '');
  assert.doesNotMatch(output, /is not defined/, output);
  // 无论网络是否可用，都不应是"函数未定义"这种崩溃
  assert.ok(result.status === 0 || result.status === 2, `unexpected ${result.status}: ${output}`);
});

test('安装器拒绝静默失效的选项', t => {
  const dir = workspace(t);
  assert.equal(installer(dir, ['--json']).status, 2);
});

test('注释检查器接受 UTF-8 BOM 与样板注释，只标记真正的英文散文', t => {
  const dir = workspace(t);
  const doc = '"""中文说明。"""\n';
  const body = '\nX = 1\n';
  write(dir, 'bom.py', '﻿' + doc + body);
  write(dir, 'generated.py', doc + '# Code generated by OpenAPI Generator. DO NOT EDIT.' + body);
  write(dir, 'license.py', doc + '# Copyright 2024 Example Inc. Licensed under the Apache License.' + body);
  write(dir, 'url.py', doc + '# https://example.com/docs/order' + body);
  write(dir, 'numbered.py', doc + '# XXX-1: 临时方案' + body);
  write(dir, 'english.py', doc + '# This comment is plain English prose and must be flagged.' + body);

  const result = scanComments(dir);
  assert.equal(result.status, 0, result.output);
  assert.ok(!result.codes.includes('parse-error'),
    `BOM 不应被判为语法错误:\n${result.output}`);
  // 样板注释、许可证、纯 URL、编号 XXX 都不该被标记
  for (const file of ['generated.py', 'license.py', 'url.py', 'numbered.py']) {
    assert.ok(!result.lines.some(l => l.includes(file) && l.includes('non-chinese-comment')),
      `${file} 不应被判为非中文注释:\n${result.output}`);
  }
  // 真正的英文散文必须仍然被抓到，否则这条规则形同虚设
  assert.ok(result.lines.some(l => l.includes('english.py') && l.includes('non-chinese-comment')),
    `英文散文应被标记:\n${result.output}`);
});

test('样板豁免按行首锚定：句中出现样板词仍要报，工具指令无冒号也要豁免', t => {
  const dir = workspace(t);
  const doc = '"""中文。"""\n\n';
  const body = '\nX = 1\n';
  const write_ = (name, comment) => write(dir, name, doc + '# ' + comment + body);

  // 这些是真正的英文散文，只是句中出现了样板关键词 —— 必须被报出来
  const mustCatch = [
    'copyright-in-sentence.py', 'This helper returns the copyright owner name.',
    'generated-by-in-sentence.py', 'The payload was generated by an upstream service.',
    'auto-generated-in-sentence.py', 'This code was auto-generated and never reviewed.',
    'type-as-word.py', 'Type of the value determines which branch we take.',
    'format-as-word.py', 'Format the value before writing it into the cache.',
  ];
  for (let i = 0; i < mustCatch.length; i += 2) write_(mustCatch[i], mustCatch[i + 1]);

  // 这些是工具指令，作者唯一"修法"就是删指令或加抑制注释 —— 必须豁免
  const mustSkip = [
    'shellcheck.py', 'shellcheck disable=SC2086 unused here',
    'rubocop.py', 'rubocop:disable Metrics/AbcSize',
    'istanbul.py', 'istanbul ignore next',
    'checkstyle-word.py', 'checkstyle suppression comment for this line',
    'prettier-hyphen.py', 'prettier-ignore start',
    'type-colon.py', 'type: ignore[assignment]',
  ];
  for (let i = 0; i < mustSkip.length; i += 2) write_(mustSkip[i], mustSkip[i + 1]);

  const result = scanComments(dir);
  const flagged = f => result.lines.some(l => l.includes(f) && l.includes('non-chinese-comment'));
  for (let i = 0; i < mustCatch.length; i += 2) {
    assert.ok(flagged(mustCatch[i]), `${mustCatch[i]} 含样板词但是散文，应被标记:\n${result.output}`);
  }
  for (let i = 0; i < mustSkip.length; i += 2) {
    assert.ok(!flagged(mustSkip[i]), `${mustSkip[i]} 是工具指令，不应被标记:\n${result.output}`);
  }
});

test('待办规则只在注释开头的标记上报，且覆盖 FIXME / XXX', t => {
  const dir = workspace(t);
  write(dir, 'A.java',
    'public class A {\n' +
    '    // TODO: 缺负责人\n' +
    '    // FIXME: 也缺\n' +
    '    // 1.1 这里讨论的是 TODO 标记的判定规则\n' +
    '    void f() { String s = "TODO: in string"; }\n' +
    '}\n');
  write(dir, 'B.java',
    'public class B {\n' +
    '    // TODO(alice): 有负责人和说明\n' +
    '    void g() {}\n' +
    '}\n');

  const result = scanComments(dir);
  const aTodo = result.lines.filter(l => l.includes('A.java') && l.includes('todo-no-owner'));
  assert.equal(aTodo.length, 2, `A.java 应报 2 条待办:\n${result.output}`);
  assert.ok(!result.lines.some(l => l.includes('B.java') && l.includes('todo-no-owner')),
    `格式完整的待办不应报错:\n${result.output}`);
  assert.equal(result.status, 1, '存在 ERROR 时退出码应为 1');
});

test('更新整体替换技能目录，清除上游已删除的文件', t => {
  const dir = workspace(t);
  const installed = path.join(dir, 'skill');
  // 模拟"上一版装过、这一版上游删掉了某个参考文档"的场景
  write(installed, 'SKILL.md', '---\nname: code-dev\ndescription: old\n---\n\n# Old\n');
  write(installed, 'references/removed-upstream.md', 'gone in new version');
  write(installed, 'references/kept.md', 'still shipped');

  const result = installer(dir, ['--update', '--target-dir', installed], (_command, options) => {
    const fresh = path.join(options.cwd, 'node_modules/readability-first-coding');
    write(fresh, 'package.json', '{"name":"readability-first-coding","version":"9.1.0"}');
    write(fresh, 'skills/code-dev/SKILL.md', '---\nname: code-dev\ndescription: new\n---\n\n# New\n');
    write(fresh, 'skills/code-dev/references/kept.md', 'still shipped');
  });

  assert.equal(result.status, 0, result.logs.join('\n'));
  assert.ok(fs.readFileSync(path.join(installed, 'SKILL.md'), 'utf8').includes('description: new'));
  assert.ok(fs.existsSync(path.join(installed, 'references/kept.md')));
  assert.equal(fs.existsSync(path.join(installed, 'references/removed-upstream.md')), false,
    '上游已删除的文件必须一并清除，否则会永久残留在用户机器上');
  assert.ok(result.logs.some(s => s.includes('removed-upstream.md')),
    result.logs.join('\n'));
});

test('更新不会误删一个不含 SKILL.md 的普通目录', t => {
  const dir = workspace(t);
  write(dir, 'precious/data.txt', 'user data');
  const result = installer(dir, ['--update', '--target-dir', path.join(dir, 'precious')],
    (_command, options) => {
      const fresh = path.join(options.cwd, 'node_modules/readability-first-coding');
      write(fresh, 'package.json', '{"name":"readability-first-coding","version":"9.1.0"}');
      write(fresh, 'skills/code-dev/SKILL.md', 'new skill');
    });
  assert.equal(result.status, 0, result.logs.join('\n'));
  assert.equal(fs.readFileSync(path.join(dir, 'precious/data.txt'), 'utf8'), 'user data');
});

const FRONTMATTER = name => `---\nname: ${name}\ndescription: fixture\n---\n\n# Fixture\n`;

test('更新拒绝覆盖指向别的技能的目录', t => {
  const dir = workspace(t);
  const target = path.join(dir, 'other-skill');
  write(target, 'SKILL.md', FRONTMATTER('some-other-skill'));
  write(target, 'my-notes.md', '用户自己的笔记');

  const result = installer(dir, ['--update', '--target-dir', target], (_c, options) => {
    const fresh = path.join(options.cwd, 'node_modules/readability-first-coding');
    write(fresh, 'package.json', '{"name":"readability-first-coding","version":"9.1.0"}');
    write(fresh, 'skills/code-dev/SKILL.md', FRONTMATTER('code-dev'));
  });

  assert.equal(result.status, 2, result.logs.join('\n'));
  assert.ok(result.logs.some(s => /Refusing to replace/.test(s)), result.logs.join('\n'));
  assert.equal(fs.readFileSync(path.join(target, 'my-notes.md'), 'utf8'), '用户自己的笔记');
  assert.equal(fs.readFileSync(path.join(target, 'SKILL.md'), 'utf8'), FRONTMATTER('some-other-skill'));
});

test('更新遇到非 code-dev 目录时 --force 可以显式覆盖', t => {
  const dir = workspace(t);
  const target = path.join(dir, 'other-skill');
  write(target, 'SKILL.md', FRONTMATTER('some-other-skill'));
  const result = installer(dir, ['--update', '--target-dir', target, '--force'], (_c, options) => {
    const fresh = path.join(options.cwd, 'node_modules/readability-first-coding');
    write(fresh, 'package.json', '{"name":"readability-first-coding","version":"9.1.0"}');
    write(fresh, 'skills/code-dev/SKILL.md', FRONTMATTER('code-dev'));
  });
  assert.equal(result.status, 0, result.logs.join('\n'));
  assert.ok(fs.readFileSync(path.join(target, 'SKILL.md'), 'utf8').includes('name: code-dev'));
});

test('更新中途失败时保留旧的完整安装', t => {
  const dir = workspace(t);
  const target = path.join(dir, 'skill');
  write(target, 'SKILL.md', FRONTMATTER('code-dev'));
  write(target, 'references/keep.md', 'old content');

  const result = installer(dir, ['--update', '--target-dir', target], (_c, options) => {
    const fresh = path.join(options.cwd, 'node_modules/readability-first-coding');
    write(fresh, 'package.json', '{"name":"readability-first-coding","version":"9.1.0"}');
    const good = path.join(fresh, 'skills/code-dev/SKILL.md');
    write(fresh, 'skills/code-dev/SKILL.md', FRONTMATTER('code-dev'));
    // 在暂存目录里放一个符号链接，让 copyDir 在切换前失败
    const link = path.join(fresh, 'skills/code-dev/broken-link');
    fs.symlinkSync(path.join(fresh, 'package.json'), link);
    assert.ok(fs.existsSync(good));
  });

  assert.equal(result.status, 2, result.logs.join('\n'));
  assert.ok(result.logs.some(s => /symbolic link/i.test(s)), result.logs.join('\n'));
  // 旧安装必须完好无损
  assert.ok(fs.existsSync(path.join(target, 'SKILL.md')), '失败后旧安装的 SKILL.md 仍在');
  assert.equal(fs.readFileSync(path.join(target, 'references/keep.md'), 'utf8'), 'old content');
  assert.equal(fs.existsSync(target + '.incoming'), false, '暂存目录必须被清理');
});

test('非 UTF-8 源文件被两个检查器一致拒绝，且提示可执行', t => {
  const dir = workspace(t);
  write(dir, 'ok.py', 'value = 1\n');
  // 用 Python 写入 GBK 字节：合法源文件，但不符合 UTF-8 强制要求
  const gbk = spawnSync(python, ['-c',
    "import pathlib,sys; pathlib.Path(sys.argv[1]).write_bytes('# 中文\\ndef run():\\n    return 1\\n'.encode('gbk'))",
    path.join(dir, 'legacy.py')], { encoding: 'utf8' });
  assert.equal(gbk.status, 0, gbk.stderr);

  // 注释检查器：read-error，且退出码为 1
  const comments = scanComments(dir);
  assert.ok(comments.codes.includes('read-error'),
    `注释检查器应报 read-error:\n${comments.output}`);
  assert.equal(comments.status, 1, comments.output);

  // 抽象检查器：列出 unreadable，退出码 2，且 count 仍只表示坏味道
  const smell = scan(dir, '--lang', 'python', '--json');
  const report = JSON.parse(smell.stdout);
  assert.equal(report.count, 0, '坏味道数量不受影响');
  assert.deepEqual(report.unreadable.map(u => u.file), ['legacy.py'],
    `抽象检查器应列出无法解码的文件:\n${smell.stdout}`);
  assert.match(report.unreadable[0].reason, /UTF-8/);
  assert.equal(smell.status, 2, '无法解码时退出码应为 2');
});

test('Git Bash hook 实际调用检查器并传递严重程度阈值', t => {
  const dir = workspace(t);
  git(dir, 'init', '-q');
  write(dir, '中文 wrapper.py', 'def run():\n    return service.run()\n');
  git(dir, 'add', '.');
  const bash = process.env.READABILITY_BASH || (process.platform === 'win32'
    ? 'C:/Program Files/Git/bin/bash.exe' : 'bash');
  const hook = path.join(root, 'skills/code-dev/scripts/pre-commit-check.sh');
  for (const [threshold, expected] of [['none', 0], ['warning', 0], ['info', 1]]) {
    const result = spawnSync(bash, [hook], {
      cwd: dir, encoding: 'utf8',
      env: { ...process.env, READABILITY_PYTHON: python, READABILITY_FAIL_ON: threshold },
    });
    assert.equal(result.status, expected, result.stderr || result.error?.message);
    assert.match(result.stdout, /python_pass_through|pass-through/i);
  }
});
