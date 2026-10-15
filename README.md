# code-dev

面向 **Java/Spring、Python/FastAPI/LangGraph、TypeScript/JavaScript/Node.js、C++、C#/.NET** 的开发规范 skill，用于实现、审查和重构。

版本以 [package.json](package.json) 和 [plugin.json](plugin.json) 为准，变更见 [CHANGELOG.md](CHANGELOG.md)。完整规则以 [SKILL.md](skills/code-dev/SKILL.md) 及其按需加载的参考文档为准。

## 规则如何生效

- 明确用户要求和授权范围优先；项目或公司明确制定的规范优先于本 skill。已有代码的位置或风格本身不构成例外。
- 审查任务只报告问题，不自动改代码。既有结构迁移按已确认范围执行；范围未确定时先说明并询问，不扩大为全仓库迁移。
- 不同语言遵循各自框架约定，不把 Java 的接口和 `impl/` 套到 Python、前端或 .NET 项目。
- 安装 skill 不会自动运行检查、安装 Git hook 或执行测试。agent 必须实际阅读适用参考、执行检查，并说明未验证部分。
- WARNING 必须逐项修正或给出豁免依据，不能把静态检查退出码 `0` 当成全面合规证明。

## 安装到 Codex 和 Claude Code

需要 Git 和 Node.js 执行安装器；使用检查脚本时另需 Python 3.10 或以上。安装器使用 Node.js 内置模块，从源码安装无需先执行 `npm install`。

先取得仓库，后续安装命令均在仓库根目录执行：

```sh
git clone https://github.com/elaysia-feng/code-dev-skill.git
cd code-dev-skill
```

按目标客户端选择命令；同时使用两端时分别执行一次：

| 目标 | 安装命令 | 安装位置 |
| --- | --- | --- |
| Claude Code 用户级 | `node bin/install.js --global` | `~/.claude/skills/code-dev/` |
| Codex 用户级 | `node bin/install.js --target-dir "$HOME/.agents/skills/code-dev"` | `~/.agents/skills/code-dev/` |
| Claude Code 指定项目 | `node bin/install.js /path/to/project` | 指定项目的 `.claude/skills/code-dev/` |
| 自定义位置 | `node bin/install.js --target-dir /path/to/code-dev` | 指向 skill 目录本身 |

`$HOME` 写法适用于 PowerShell 和常见 Unix shell。不带目标参数时，默认安装到**当前工作目录**的 `.claude/skills/code-dev/`；在本仓库运行就会安装到本仓库下，不会自动找到其他业务项目。

安装后在新会话中使用 Codex 的 `$code-dev` 或 Claude Code 的 `/code-dev`。复制安装时必须保留完整 `skills/code-dev/`，不能只复制 `SKILL.md`，因为规则引用了同目录的文档和脚本。

也可以通过 npm 从 GitHub 获取安装器。以下方式会修改当前目录的 npm 依赖文件，适合明确希望将其作为项目依赖的场景：

```sh
npm install github:elaysia-feng/code-dev-skill
npx readability-first-install --global
```

`readability-first-coding` 是兼容保留的 npm 包标识；skill 名始终为 `code-dev`。上述命令从 GitHub 获取，不依赖 npm 注册表中的同名发布。

## 当前重点规则

| 领域 | 要求 |
| --- | --- |
| Java 业务边界 | 业务组件采用接口与 `impl/`，调用方依赖接口；DTO、实体、值对象、枚举和配置类不强加接口。 |
| MP 持久化 | 新 Spring 项目选择 Mapper 持久化时使用 MyBatis-Plus（MP）。`BaseMapper<Entity>` 是框架代理，不需要手写 `MapperImpl`；已有其他明确选型按项目约定处理。 |
| 类型归属 | `service/` 不是模型容器；内部契约、领域值对象、持久化实体和外部协议对象按职责归属，公开嵌套 `record` 也要检查。 |
| 配置与硬编码 | 使用框架原生机制隔离开发、测试、生产环境；统一维护公共默认值。地址、超时、重试等可调参数不能仅换成常量就算外置。 |
| 事务与集成 | 原子写操作由业务边界拥有事务；验证代理调用路径，避免事务内慢 IO，不另写一套调用绕过已有集成组件。 |
| 注释 | 新增或修改的说明性注释使用简体中文；多阶段流程按真实层级编号，短方法、私有方法不因行数少自动豁免。 |
| 编码 | 源码必须是 UTF-8；已保存的 U+FFFD 替换字符同样要恢复原文，故意使用该字符的测试用 Unicode 转义表达。 |
| SQL | 表与字段具备数据库支持的元数据说明，每个字段定义还要有行尾 `-- ` 中文解释；已应用的迁移不随意重写。 |
| Java/TS/JS 分支 | 所有 `if`、`else if`、`else` 分支使用花括号，包括单行守卫和提前返回。 |

### Java 类型放在哪里

普通分层 Spring 项目的默认归属如下；有明确等价项目约定时复用既有归属，不生成第二套结构：

| 类型 | 默认归属 |
| --- | --- |
| HTTP 请求与响应 | `dto/request/<domain>/`、`dto/response/<domain>/` |
| 跨组件传递的内部命令、上下文、结果 | `dto/internal/<domain>/` |
| 非持久化领域值对象与不变量 | `domain/<domain>/model/` |
| ORM 映射实体 | `entity/<domain>/` |
| 领域枚举与固定常量 | 已有领域归属；否则 `domain/<domain>/enums/`、`domain/<domain>/constants/` |
| 外部提供方的载荷与原始结果 | `integration/<provider>/model/` 或已有集成契约归属 |

例如，传给多个处理器的字段型 `TaskContext` 是内部契约；承载归一化和比较不变量的 `MetadataFingerprint` 是领域值对象。不能因为它们被服务使用，就全部放进 `service/`。

仅供单个实现使用、不暴露契约且不具有独立领域或集成职责的私有临时元组，可以保留为嵌套类型，不要求每个局部结果都拆文件。详见 [结构规范](skills/code-dev/references/project-structure.md#java-type-ownership)。

## 三个检查器

以下命令在本仓库根目录运行，`/path/to/project` 替换为业务项目路径；`python` 应指向你选定的 Python 环境。

### 注释检查

检查 Java/Python 的注释、文档、待办和流程编号，严格模式同时阻断 WARNING：

```sh
python skills/code-dev/scripts/check_comments.py /path/to/project --fail-on warning
```

简单 JavaBean getter/setter 按实际方法体豁免；仅方法名类似、内部却执行校验、调用或业务逻辑时不豁免。该工具不覆盖 TS、C++、C# 的注释语义。

### 抽象检查

检查 Java/Python 的可疑抽象、继承和转发，识别 MP Mapper、Spring Controller 及部分框架注解边界：

```sh
python skills/code-dev/scripts/check-abstraction-smell.py /path/to/project --lang auto --fail-on warning
```

支持 `--json`、`--files` 和 `--staged`。默认阈值为 `none`，只报告；INFO 不会被 `--fail-on warning` 阻断。不能按“只有一个实现”或“只有一行”机械删除真实边界。

### Java 运行边界与源码编码检查

检查直接事务自调用、重复配置默认值、疑似硬编码、集成未接入及同领域 HTTP 绕过，同时检查受支持源码、SQL 和配置文件的编码：

```sh
python skills/code-dev/scripts/check-java-boundaries.py /path/to/project --fail-on warning
```

支持 `--json` 和 `--staged`，默认阻断 WARNING。诊断不打印配置值或源码凭据。

它是词法启发式检查，不能解析完整 Java 类型系统、间接调用链、全部 Spring 配置绑定或反射装配。有类型引用也不证明业务链路已正确接入。跨文件检查应传项目根目录；仍需验证真实代理、回滚、环境加载和集成行为。完整范围及限制见 [SKILL.md](skills/code-dev/SKILL.md#checks)。

### 退出码怎么理解

| 检查器 | `0` | `1` | `2` |
| --- | --- | --- | --- |
| 注释 | 未达到阈值；默认仍可能有 WARNING | 有 ERROR 或达到 WARNING 阈值 | 无匹配 Java/Python 文件或检查失败 |
| 抽象 | 未达到阈值；默认只报告 | 达到指定阈值 | 读取、编码、参数或执行失败 |
| Java 边界与编码 | 未达到阈值 | 有 ERROR 或达到 WARNING 阈值 | 无匹配文件、参数或执行失败 |

暂存模式没有相应受支持变更时可返回 `0` 并提示未检查文件，这不表示审查了其他语言。分支花括号、SQL 文档、类型归属和规则豁免仍需人工核对，不能声称三个检查器覆盖全部规范。

## 可选 Git 提交门禁

[pre-commit-check.sh](skills/code-dev/scripts/pre-commit-check.sh) 是可合并到现有 hook 的模板，安装 skill 不会自动启用它，也不要覆盖已有 hook。

三个检查器读取 Git **索引**内容；工作区改干净不能绕过仍在暂存区的问题。默认阻断 ERROR 和检查失败，包括 SQL、配置文件中已保存的替换字符；普通 WARNING 默认仅提示。

| 环境变量 | 作用 |
| --- | --- |
| `READABILITY_PYTHON` | hook 和仓库 Node 测试使用的 Python 路径。 |
| `READABILITY_FIRST_STRICT=1` | 三个检查器的 WARNING 都阻断；缺解释器或检查器也失败。 |
| `READABILITY_FAIL_ON=warning` | 抽象和边界 WARNING 阻断，不单独提升注释阈值。 |
| `COMMENT_FAIL_ON=warning` | 单独让注释 WARNING 阻断。 |
| `READABILITY_BASH` | Python 回归测试使用的 Bash 路径；Windows 上可指定 Git Bash。 |

门禁放行只表示未达到当前阈值，不代表运行功能或所有规范已验证。

## 检查版本与更新安装

版本检查比较的是**本地源码包或 npm 包的版本**与 GitHub `main` 的 `package.json`，不会逐一检查全局 skill 目录是否同步，也不会自动更新文件：

```sh
node bin/check-update.js --json
```

版本检查退出码：`0` 已是当前版本或更高，`1` 有更新，`2` 网络或执行失败，`3` 未找到本地包版本。npm 方式对应 `npx readability-first-check --json`。

源码安装方式更新时，先拉取最新仓库，再分别更新两个实际使用的目标目录：

```sh
git pull --ff-only
node bin/install.js --global
node bin/install.js --target-dir "$HOME/.agents/skills/code-dev"
```

npm 安装器也支持直接下载 GitHub `main` 的新包并更新指定目标；不带目标参数仍会落到当前项目的 `.claude/skills/code-dev/`：

```sh
npx readability-first-install --update --global
npx readability-first-install --update --target-dir "$HOME/.agents/skills/code-dev"
```

更新会整体替换目标 skill 目录，清理上游删除的旧文件，**本地自定义修改也会被替换**。安装器先暂存，再切换并保留失败恢复路径；遇到其他技能名、链接或不安全文件会拒绝覆盖。`--force` 仅用于明确覆盖另一技能名称，不用于绕过文件安全检查。两端各有安装副本，必须分别更新。

## 仓库验证与维护

仓库测试覆盖安装器、版本比较、文档完整性和 Python 检查器回归。以下命令运行测试并检查打包清单，不发布 npm 包：

```sh
npm test
npm pack --dry-run --ignore-scripts
```

Windows PowerShell 中，可显式指定 Python 和 Git Bash。请把示例路径替换为本机实际位置；不使用 `py` 启动器隐式选择解释器：

```powershell
$env:READABILITY_PYTHON = 'C:\path\to\python.exe'
$env:READABILITY_BASH = 'C:\path\to\Git\bin\bash.exe'
npm test
```

也可以单独运行 Python 回归测试；它们在临时夹具上验证检查结果与索引门禁，不连接业务数据库：

```sh
python -X utf8 -B -m unittest discover -s skills/code-dev/evals -p "test_*.py"
```

[`skills/code-dev/evals/`](skills/code-dev/evals/) 保留在 Git 仓库中，但从 npm 包排除；三个检查器及 hook 模板会进入包。打包检查应在测试结束后运行，核对没有临时文件或缓存进入包。格式验证可使用已安装的 Agent Skills 验证工具，但不替代行为测试。

涉及可分发 skill 或安装器变更时，同步调整 `package.json` 与 `plugin.json` 版本，并更新变更记录；单纯 README 修订不必制造新版本。提交前同步远端并检查差异，发布后核对远端提交与实际安装内容。需要打标签时使用本次真实版本，不复制旧版本号；推送 GitHub 不等于发布 npm 包。

## 文件入口

| 路径 | 用途 |
| --- | --- |
| [SKILL.md](skills/code-dev/SKILL.md) | 规则入口、优先级和按需阅读索引 |
| [references/](skills/code-dev/references/) | 各语言、结构、配置、运行边界、SQL 和注释细则 |
| [scripts/](skills/code-dev/scripts/) | 三个检查器及可选 hook 模板 |
| [evals/](skills/code-dev/evals/) | 行为评估场景和可执行 Python 回归测试 |
| [assets/ide-settings.json](skills/code-dev/assets/ide-settings.json) | 避免编辑器自动改写规范代码的设置参考 |
| [bin/](bin/) | 安装器、版本检查及版本比较实现 |
| [tests/](tests/) | 安装、更新、检查器及内容完整性测试 |
| [plugin.json](plugin.json) | Agent Plugins 1.0.0 插件元数据 |
| [LICENSE](LICENSE) | MIT 许可证 |

支持 Agent Plugins 1.0.0 的客户端可把含 `plugin.json` 的仓库根目录作为插件入口；单独安装 skill 时使用 `skills/code-dev/`。本仓库不提供 MCP 服务。具体客户端是否支持该插件格式，以其实际能力为准，不能把两种安装入口混为一谈。
