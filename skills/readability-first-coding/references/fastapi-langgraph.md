# FastAPI + LangGraph

仅在实际使用该栈时加载，适用 [入口规则](../SKILL.md)。

- 路由处理协议输入输出，业务沿用现有 Service 或函数；Pydantic 模型各自声明字段约束。
- 可按图分文件，图专用 state、node、tool 就近放置；仅将已有或明确要求共享的内容放入 `core/langgraph/` 等公共位置。
- 不主动建立 `BaseGraph`、`BaseState`、`BaseAgent` 或通用 graph builder。
- 编译和初始化时机沿用现有生命周期，依赖外部连接的初始化不为缩短代码而移到模块导入阶段。
