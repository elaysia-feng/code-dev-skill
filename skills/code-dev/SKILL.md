---
name: code-dev
description: >-
  用于 Java/Spring、Python/FastAPI/LangGraph 和 TypeScript/Node.js 项目的实现、审查与重构。
  沿用项目约定，保持业务流程清楚，并按需应用代码注释和 TypeScript npm 包规范。
license: MIT
---

# Code Dev

正确性是前提。之后按 **用户明确要求 → 当前项目约定 → 最简单清楚的实现** 决策。

- 先读相关模块、调用关系和现有模式，再决定代码与目录结构。
- 不只为减少重复行数增加公共方法、父类、共享模块或额外层次。
- 仅在用户要求、项目既有架构、稳定共享规则、明确扩展点或框架边界需要时抽取结构。
- 用户明确要求重构或抽取时，按其范围完成；不要以“可读性优先”为由拒绝，也不要顺带扩大改动。
- 用户只要求审查时，只报告发现的问题，不自动修改代码。
- 审查薄委托、单实现接口和继承时，先确认其是否承载事务、安全、并发、资源管理或公开契约。

## Java 业务接口

Java 业务行为组件遵循 [`references/java-guidelines.md`](references/java-guidelines.md) 的接口优先约定：先判断是否有专用 `*.biz` 模块，再按对应项目形态放置接口与实现。DTO、实体、枚举、异常、配置等定义类型不因此新增接口。

## 按需加载

只读当前任务相关的参考文档：

| 场景 | 参考文档 |
|---|---|
| Java/Spring 后端 | [`references/java-guidelines.md`](references/java-guidelines.md) |
| Java 微服务边界 | [`references/microservice-guidelines.md`](references/microservice-guidelines.md) 与 Java 指南 |
| Python、FastAPI 或 LangGraph | [`references/python-guidelines.md`](references/python-guidelines.md) |
| 新建项目或调整目录/模块 | [`references/project-structure.md`](references/project-structure.md) |
| 新增或修改 Java、Python、TypeScript 注释 | [`references/code-comment-guidelines.md`](references/code-comment-guidelines.md) |
| 创建或维护 TypeScript npm 包、导出入口或发布内容 | [`references/typescript-package-guidelines.md`](references/typescript-package-guidelines.md) |
| 抽取边界或组织方式不明确 | 只读 [`references/examples.md`](references/examples.md) 中相关示例 |

## 可选检查

需要辅助审查抽象时，可运行 `scripts/check-abstraction-smell.py`。它只提供启发式线索；须结合项目约定人工判断，不能据此自动改写架构。
新增或修改 Java/Python 文件后，如有帮助，可运行 `scripts/check_comments.py`；该检查器不覆盖 TypeScript，WARNING 需人工判断，不要求为清零而堆注释。

完成前确认需求已落实、相关行为已核对，并说明尚未验证的部分。
