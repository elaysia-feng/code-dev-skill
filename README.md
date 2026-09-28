# code-dev

面向 Java/Spring、Python/FastAPI/LangGraph 和 TypeScript/Node.js 项目的开发技能。除项目结构与抽象取舍外，合并了中文代码注释规范，并为可发布的 TypeScript npm 包提供入口、类型声明和打包建议。

技能名、目录名和主动触发名统一为 `code-dev`：Codex 使用 `$code-dev`，Claude Code 使用 `/code-dev`。`package.json` 中的包名暂保留 `readability-first-coding` 作为兼容标识；安装从 GitHub 获取，不依赖 npm registry 上的同名包。

## 安装与调用

在目标项目目录从 GitHub 安装包并执行安装器：

```sh
npm install github:elaysia-feng/code-dev-skill
npx readability-first-install
```

默认安装到项目的 `.claude/skills/code-dev/`，可直接用 `/code-dev` 调用技能。Codex 的全局技能目录可将 `skills/code-dev/` 安装到 `.agents/skills/code-dev/`，然后用 `$code-dev` 触发。

需要用户级安装时执行：

```sh
npx readability-first-install --global
```

自定义安装目录使用 `--target-dir`，路径指向技能目录本身。具体参数处理见 [安装器](bin/install.js)。

## 适用范围

- 实现和审查 Java / Python 后端及 TypeScript/Node.js 代码。
- 根据已有项目选择服务、接口、数据访问层的组织方式。
- 在微服务、FastAPI 和 LangGraph 项目中控制职责与依赖。
- 修改代码时维护本次涉及的注释；创建或维护 TS npm 包时按需阅读包规范。
- 判断何时直接内联，何时需要可复用的独立组件。

项目明确规则优先于技能的通用建议；技能不是格式化工具，也不会替代编译、测试或人工审查。

## 检查更新

检查与更新是两个独立操作：

```sh
npx readability-first-check
npx readability-first-install --update
```

检查器支持 `--json`。退出码 `0` 表示已是最新，`1` 表示有更新，`2` 表示网络或工具错误，`3` 表示本地未安装。

## 仓库结构与验证

| 路径 | 内容 |
| --- | --- |
| [技能入口](skills/code-dev/SKILL.md) | 适用场景与核心规则 |
| `skills/code-dev/references/` | Java、Python、TypeScript 包及注释细则 |
| `skills/code-dev/scripts/check_comments.py` | Java/Python 注释启发式检查器 |
| `bin/` | 安装、更新检查与文件处理 |
| `tests/` | 安装和更新行为测试 |

修改安装器后运行 `npm test`；发布前可用 `npm pack --dry-run --ignore-scripts` 检查实际打包内容。
