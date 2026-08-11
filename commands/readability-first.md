---
name: readability-first
description: 可读性优先编码模式（Java / Python 后端）：禁止主动抽象、抽取和公共模块，除非明确要求
argument-hint: "[语言或任务描述，如 Java / Python (FastAPI + LangGraph) / Java 微服务]"
allowed-tools: Read,Write,Edit,Glob,Grep,Bash,Task,Agent,LSP
---

# /readability-first

用户输入：`$ARGUMENTS`

立即通过 Skill tool 激活 `readability-first-coding` 技能，并在本次实现 / 修改 / 审查 / 重构全过程中严格遵循它的全部规则：

1. **只实现用户要求的**，不主动抽取公共方法、工具类、父类、公共模块 —— 无论代码重复多少次。
2. **重复业务逻辑保持重复**，除非用户明确要求抽取。
3. 不创建 `common`、`util`、`utils`、`shared`、`framework`、`helpers`、`extensions`、`support`、`infrastructure`、`base` 模块。
4. 代码自上而下可读，业务逻辑内联，避免无谓的包装、分层和复杂语法。
5. 正确性优先，可读性绝不牺牲正确性。
6. 若用户明确要求抽取，仅抽取用户指定的部分。
7. 不改动与任务无关的代码，不引入新的架构层。

语言参考（实现前用 Read 加载对应文件）：

| 场景 | 参考文件 |
|---|---|
| Java 后端 | `references/java-guidelines.md` |
| Python 后端 (FastAPI + LangGraph) | `references/python-guidelines.md` |
| Java 微服务 | `references/microservice-guidelines.md` |

请按以上规则完成任务：`$ARGUMENTS`
