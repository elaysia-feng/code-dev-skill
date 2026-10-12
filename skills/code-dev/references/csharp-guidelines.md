# C#/.NET 开发规范

本文件适用于 C#/.NET 实现、审查和重构，与主 skill 的通用规则共同执行。

- 遵循项目确定的目标框架、C# 版本和应用类型，不把 ASP.NET Core 的约定强制套用到桌面、游戏或类库项目。
- ASP.NET Core 配置使用 `appsettings.json` 和环境文件；相关配置优先通过 Options 模式绑定并验证，需启动时验证时采用项目支持的启动校验机制。其他 .NET 应用使用现有配置入口。所有配置遵循 [配置规范](configuration-guidelines.md)。
- 适合框架职责的 attributes 应合理使用，例如已有 Web 框架中的路由和模型校验；确认其运行管线实际执行，不假设声明 attribute 就已生效。
- 使用项目原生依赖注入并核对生命周期，禁止单例直接持有作用域服务。不强制每个类创建接口；接口用于实际契约、替换边界或测试需求。
- 异步 I/O 使用 `async` / `await` 并传播 `CancellationToken`；避免 `.Result`、`.Wait()` 阻塞，除事件处理器等签名要求外不使用 `async void`。不以 `Task.Run` 包装普通异步 I/O。
- 使用 `using` / `await using` 释放可释放资源，明确可空性和所有权；不使用空 `catch` 或伪造成功结果掩盖失败。
- `if`、`else if`、`else` 的分支体必须使用 `{}`，包括单行分支和提前返回。固定业务值使用领域常量或枚举，可变配置不得藏入 `const` / `static readonly`。
- 注释使用简体中文；公共 API 使用 XML 文档说明有意义的参数、返回值、异常和取消语义，不为简单属性堆积注释。
- 修改后使用项目现有 `dotnet build` 和相关测试，遵循已有分析器配置。现有 skill 的 Python 检查器不扫描 C#，不可当作 C# 验证证据。
