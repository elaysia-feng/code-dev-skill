#!/usr/bin/env node

const os = require('node:os');
const path = require('node:path');
const { doUpdate } = require('./install.js');

/** 从 GitHub 更新两端的用户级 skill；任一目标失败时返回非零退出码。 */
function main() {
  const args = process.argv.slice(2);
  if (args.length !== 1 || args[0] !== 'update') {
    console.error('用法：code-dev update');
    process.exitCode = 2;
    return;
  }
  doUpdate([
    path.join(os.homedir(), '.claude', 'skills', 'code-dev'),
    path.join(os.homedir(), '.agents', 'skills', 'code-dev'),
  ]);
}

try {
  main();
} catch (error) {
  console.error('更新失败：' + error.message);
  process.exitCode = 2;
}
