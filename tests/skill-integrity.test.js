const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const skillRoot = path.resolve(__dirname, '../skills/code-dev');
const python = process.env.READABILITY_PYTHON || 'python';

function filesUnder(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
    const file = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      return filesUnder(file);
    }
    return /\.(md|json|py|sh|yaml|yml)$/.test(entry.name) ? [file] : [];
  });
}

test('技能文本必须是 UTF-8，且不能包含未解决的合并冲突', () => {
  for (const file of filesUnder(skillRoot)) {
    const text = new TextDecoder('utf-8', { fatal: true }).decode(fs.readFileSync(file));
    assert.doesNotMatch(text, /^(?:<{7}|={7}|>{7}|\|{7})(?:\s|$)/m, file);
  }
});

test('评估 JSON 可读取，每个用例保留唯一标识和必要内容', () => {
  const cases = JSON.parse(fs.readFileSync(path.join(skillRoot, 'evals/evals.json'), 'utf8')).evals;
  assert.ok(cases.length > 0);
  assert.equal(new Set(cases.map(item => item.id)).size, cases.length, '评估 ID 重复');
  assert.equal(new Set(cases.map(item => item.prompt)).size, cases.length, '评估场景重复');
  for (const item of cases) {
    assert.ok(Number.isInteger(item.id) && item.id > 0);
    assert.ok(item.prompt.trim() && item.expected_output.trim());
  }
  const triggers = JSON.parse(fs.readFileSync(path.join(skillRoot, 'evals/trigger-evals.json'), 'utf8'));
  assert.ok(triggers.length > 0);
  for (const item of triggers) {
    assert.equal(typeof item.should_trigger, 'boolean');
    assert.ok(item.query.trim() && item.reason.trim());
  }
});

test('技能 Markdown 的本地引用必须指向实际文件', () => {
  for (const file of filesUnder(skillRoot).filter(file => file.endsWith('.md'))) {
    const text = fs.readFileSync(file, 'utf8');
    for (const match of text.matchAll(/\[[^\]]*\]\(([^)]+)\)/g)) {
      const target = match[1].split('#')[0];
      if (!target || /^[a-z]+:\/\//i.test(target) || target.startsWith('/')) {
        continue;
      }
      assert.ok(fs.existsSync(path.resolve(path.dirname(file), target)), `${file}: ${target}`);
    }
  }
});

test('项目结构中的 Python 示例可以解析，防止缩进损坏', () => {
  const file = path.join(skillRoot, 'references/project-structure.md');
  const text = fs.readFileSync(file, 'utf8');
  const examples = [...text.matchAll(/```python\r?\n([\s\S]*?)\r?\n```/g)];
  assert.ok(examples.length > 0);
  for (const match of examples) {
    const result = spawnSync(python, ['-B', '-c', 'import ast, sys; ast.parse(sys.stdin.read())'], {
      input: match[1], encoding: 'utf8', env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    });
    assert.equal(result.status, 0, result.error?.message || result.stderr);
  }
});
