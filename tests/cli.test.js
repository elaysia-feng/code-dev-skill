const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

test('update 下载一次并替换两端内容，清理过期文件', () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'code-dev-cli-test-'));
  try {
    // 1. 隔离用户目录，模拟已有安装和上游删除的文件。
    for (const client of ['.claude', '.agents']) {
      const target = path.join(temp, client, 'skills', 'code-dev');
      fs.mkdirSync(target, { recursive: true });
      fs.writeFileSync(path.join(target, 'SKILL.md'), '---\nname: code-dev\n---\nold');
      fs.writeFileSync(path.join(target, 'stale.md'), 'old');
    }
    const preload = path.join(temp, 'preload.cjs');
    fs.writeFileSync(preload, `
      const fs = require('node:fs');
      const path = require('node:path');
      require('node:os').homedir = () => ${JSON.stringify(temp)};
      require('node:child_process').execSync = (command, options) => {
        fs.appendFileSync(${JSON.stringify(path.join(temp, 'downloads'))}, 'download\\n');
        const root = path.join(options.cwd, 'node_modules', 'readability-first-coding');
        fs.mkdirSync(path.join(root, 'skills', 'code-dev'), { recursive: true });
        fs.writeFileSync(path.join(root, 'package.json'), JSON.stringify({name:'readability-first-coding',version:'9.0.0'}));
        fs.writeFileSync(path.join(root, 'skills', 'code-dev', 'SKILL.md'), '---\\nname: code-dev\\n---\\nfresh');
      };
    `);
    // 2. 从任意目录调用真实入口，核对两端结果和下载次数。
    const result = spawnSync(process.execPath, ['--require', preload, path.resolve('bin/code-dev.js'), 'update'], { cwd: temp, encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(fs.readFileSync(path.join(temp, 'downloads'), 'utf8'), 'download\n');
    for (const client of ['.claude', '.agents']) {
      const target = path.join(temp, client, 'skills', 'code-dev');
      assert.match(fs.readFileSync(path.join(target, 'SKILL.md'), 'utf8'), /fresh/);
      assert.equal(fs.existsSync(path.join(target, 'stale.md')), false);
    }
  } finally {
    fs.rmSync(temp, { recursive: true, force: true });
  }
});

test('不支持的命令返回非零且不执行更新', () => {
  const result = spawnSync(process.execPath, [path.resolve('bin/code-dev.js'), 'invalid'], { encoding: 'utf8' });
  assert.equal(result.status, 2);
  assert.match(result.stderr, /code-dev update/);
});
