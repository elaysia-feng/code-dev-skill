# Project Structure

本文目录规范适用于新增代码、目录和模块；既有项目的全量迁移必须先按 [`../SKILL.md`](../SKILL.md) 的“既有项目迁移”规则询问用户。用户同意后全量迁移；不同意则保留既有结构，仅新增部分遵循本规范。标记 `optional` 的目录仅在应用确有需要时创建，不照搬空目录模板。

## Java Backend

### Ordinary monolithic Spring project

For a normal single-module Spring Boot application, keep business services under `service/`, and use interface + `impl/`:

```text
com.example.project/
├── controller/
├── dto/
│   ├── request/
│   └── response/
├── service/
│   ├── OrderService.java
│   ├── UserService.java
│   └── impl/
│       ├── OrderServiceImpl.java
│       └── UserServiceImpl.java
├── mapper/
├── entity/
├── config/
└── exception/
```

Responsibilities:

- `controller/` — HTTP boundary: parse/validate request, call service contract, return response.
- `dto/request/` — incoming API models.
- `dto/response/` — outgoing API models.
- `service/` — business contracts; implementations live in `impl/`.
- `mapper/` — persistence access when using MyBatis/MyBatis-Plus style mappers.
- `entity/` — persistence models.
- `config/` — framework/infrastructure configuration.
- `exception/` — project/domain exceptions when they have clear ownership.

新增包使用上述单数名称 `service/`。既有 `services/` 仅在用户同意全量迁移后改为 `service/`。

### Multi-Maven / multi-module project with dedicated `*.biz`

When a multi-module Maven project separates business logic into modules such as `community.biz`, the `biz` module owns business contracts and implementations:

```text
middleware-arena-community/
├── community.dto/
├── community.web/
└── community.biz/
    └── src/main/java/com/mware/community/biz/
        ├── favorite/
        │   ├── FavoriteService.java
        │   ├── FavoriteRedisStore.java
        │   ├── FavoriteStreamRelay.java
        │   └── impl/
        │       ├── FavoriteServiceImpl.java
        │       ├── FavoriteRedisStoreImpl.java
        │       └── FavoriteStreamRelayImpl.java
        ├── follow/
        │   ├── FollowService.java
        │   └── impl/
        │       └── FollowServiceImpl.java
        └── like/
            ├── LikeService.java
            ├── LikeRedisStore.java
            ├── LikeStreamRelay.java
            └── impl/
                ├── LikeServiceImpl.java
                ├── LikeRedisStoreImpl.java
                └── LikeStreamRelayImpl.java
```

Rules:

- Interfaces stay in the domain package.
- Implementations stay in that domain package's `impl/`.
- Other packages/modules depend on interface types, not `*Impl`.
- In a dedicated `biz` module, apply this pattern to business-behavior collaborators such as Service, Store, Relay, Manager, Handler, Processor, and adapters.
- DTO/entity/enums/config/exceptions are not forced into interface + impl pairs.

Optional domain-specific packages such as `enums/`, `event/`, `validation/`, or `client/` should be added only when the domain actually needs them.

## Java Microservices

Prefer domain/service ownership over one global shared module:

```text
project-parent/
├── order-service/
├── product-service/
├── user-service/
└── common-api/             # optional; only if the project genuinely needs one
```

新建共享模块使用 `common-api/`。既有 `base-service`、`common`、`platform-core` 或 `shared-kernel` 仅在用户同意全量迁移后改为 `common-api/`；不同意时保留并复用已有模块，不另建重复模块。

If an individual microservice is a normal Spring module, use its `service/` + `impl/` business structure. If the Maven project instead separates a dedicated `*.biz` module, use the `biz` layout described above.

See `microservice-guidelines.md` for cross-service rules.

## Python Backend (FastAPI + LangGraph)

新建后端默认使用 `src/app/` 包布局，配置包发现、开发安装及启动入口，验证从不同工作目录也能正常导入；不要仅搬文件后依赖临时修改 `sys.path`。已有 `app/` 平铺布局的调整受迁移选择约束。

```text
src/
└── app/
    ├── __init__.py
    ├── main.py
    ├── api/
    │   └── v1/                    # optional; API 确需版本化时创建
    ├── core/
    │   ├── config.py
    │   ├── llm.py                 # optional; 使用 LLM 时创建
    │   └── middleware.py          # optional
    ├── graphs/                    # optional; 使用 LangGraph 时创建
    ├── schemas/
    ├── services/
    ├── models/                    # optional; 拥有数据库模型时创建
    ├── repositories/              # optional; 有明确数据访问边界时创建
    └── memory/                    # optional
```

Do **not** create `utils/`, `common/`, `base/`, or a generic `core/langgraph/` just because they appear in another template. Add them only when the project has a concrete need. 既有包仅在用户同意全量迁移后调整到上述布局。

Typical repository-root files:

```text
pyproject.toml
.env.example
tests/
alembic/                 # only when SQL migrations are used
langgraph.json            # only when LangGraph CLI/Studio deployment needs it
```

### `app/main.py`

Creates the `FastAPI` application and registers routers/middleware. Keep business logic out of the entry point.

### `api/`

HTTP route handlers. Organize by API version/domain only when the project is large enough to benefit from it.

Examples:

```text
api/
└── v1/
    ├── chat.py
    └── documents.py
```

A very small service may simply use `api/chat.py`; do not introduce version folders without a requirement.

### `core/`

Infrastructure/configuration used broadly by the application, such as:

```text
core/
├── config.py
├── llm.py
└── middleware.py
```

`core/` is not a dumping ground for business helpers.

### `graphs/`: small LangGraph agent

For a small graph, keep the graph and graph-specific logic together when it remains easy to read:

```text
graphs/
└── research_assistant.py
```

The file may contain its state type, a few nodes, routing functions, and graph composition.

### `graphs/`: complex LangGraph agent

When one graph has several meaningful nodes, use a package owned by that graph:

```text
graphs/
└── research_assistant/
    ├── __init__.py
    ├── graph.py
    ├── state.py
    ├── nodes/
    │   ├── __init__.py
    │   ├── plan.py
    │   ├── retrieve.py
    │   ├── grade_documents.py
    │   └── generate_answer.py
    ├── tools.py                 # switch to tools/ once it holds several substantial tools
    └── prompts.py               # optional; only when prompts are large enough to deserve a file
```

Rules:

- Prefer one primary LangGraph node per node file in a complex graph.
- Small private helpers used only by a node stay with that node.
- Graph-specific `state`, nodes, tools, routing, and prompts stay inside the graph package.
- `nodes/__init__.py` may be empty or contain lightweight imports/`__all__`; no business logic or side effects.
- Do not create a graph package for a graph with only one or two tiny nodes.

### Shared LangGraph infrastructure

Create shared LangGraph infrastructure only after multiple graphs genuinely share the same concern:

```text
core/
└── langgraph/
    ├── checkpoint.py
    ├── common_state.py
    └── common_tools.py
```

Avoid generic names such as `nodes.py` or `graph.py` in shared infrastructure unless their ownership is obvious. Similar-looking graph-specific nodes are not automatically shared nodes.

### `schemas/`

Pydantic request/response/application models. Keep validation with the model or domain that owns it.

### `services/`

Non-agent application/business logic such as database operations, external service calls, document ingestion, or orchestration outside the graph.

小项目可以由 service 直接进行简单数据库访问。有复用查询、复杂持久化规则、存储替换或需要隔离测试的明确边界时，可新增 `repositories/`；不要为单次 CRUD 添加纯转发层。已有 repository 时必须复用该边界，不能另建并行数据访问路径。事务由业务入口管理，repository 不自行提交会拆散同一业务操作的事务。

### `models/`

SQLModel/SQLAlchemy persistence models when the application owns relational persistence.

### `memory/`

Optional long-term memory implementations such as pgvector/mem0 adapters. Do not create this package unless the application actually uses long-term memory.

## TypeScript 前端应用

以下为无强制文件路由的 React/Vue 应用基线，按实际需要创建目录；Next.js 等框架使用其 `app/`、`pages/` 等保留目录，不能照搬 `pages/` 的含义。具体职责见 [frontend-guidelines.md](frontend-guidelines.md)。

```text
src/
├── main.ts / main.tsx      # 使用框架实际入口，不同时创建两套
├── App.vue / App.tsx       # 应用组合入口
├── pages/                 # 路由页面
├── features/              # optional; 较复杂业务按功能归属组织
│   └── orders/
│       ├── components/
│       ├── api.ts
│       ├── types.ts
│       └── useOrders.ts   # optional; React hook 或 Vue composable
├── components/            # optional; 跨功能通用组件
├── api/                   # optional; 共享请求客户端和协议处理
├── router/                # optional; 框架需要显式路由配置时创建
├── stores/                # optional; 确有共享状态时创建
├── assets/                # optional; 参与构建的资源
└── styles/                # optional; 全局样式和设计变量
```

小页面可直接组织在页面文件及相邻模块中；功能变复杂时再聚合到 `features/<功能>/`。功能内部不得直接依赖其他功能的私有组件；共享内容须有明确契约。不要同时在全局与功能目录中维护两套请求、状态或类型。既有结构迁移仍须先询问用户。

## Python 布局参考

- [PyPA：src 与平铺布局](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)：两种布局有不同的安装与导入行为，`src/` 需要配套安装配置。
- [FastAPI：多文件应用](https://fastapi.tiangolo.com/tutorial/bigger-applications/)：按职责组织包并组合路由；本规范的具体目录命名属于项目约定。

## `__init__.py`

Default rule for application packages:

- It may be empty.
- Use it for lightweight, intentional package-level exports when that improves imports.
- Do not put database connections, model loading, graph compilation, network calls, or other side effects in `__init__.py`.

Example lightweight export:

```python
from .retrieve import retrieve
from .generate_answer import generate_answer

    __all__ = ["retrieve", "generate_answer"]
```
