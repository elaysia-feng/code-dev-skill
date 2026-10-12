# C#/.NET Guidelines

These rules apply to C#/.NET implementation, review and refactoring alongside the skill's general rules.

- Follow the project's target framework, C# version and application type. Do not force ASP.NET Core conventions onto desktop, game or library projects.
- ASP.NET Core uses `appsettings.json` and environment files. Prefer Options binding and validation for related settings; use the project's supported startup validation when validation must occur at startup. Other .NET applications use their existing configuration entry point. Follow the [configuration guidelines](configuration-guidelines.md).
- Use attributes appropriate to existing framework responsibilities, such as web routing and model validation. Verify the execution pipeline actually applies them; declaring an attribute alone does not prove it works.
- Use native dependency injection and check service lifetimes. Singletons must not directly retain scoped services. Interfaces serve actual contracts, replacement boundaries or testing needs; not every class requires one.
- Use `async` / `await` for asynchronous I/O and propagate `CancellationToken`. Avoid blocking with `.Result` or `.Wait()`. Use `async void` only where signatures require it, such as event handlers. Do not wrap ordinary asynchronous I/O in `Task.Run`.
- Release disposable resources with `using` / `await using` and make nullability and ownership explicit. Do not hide failures with empty `catch` blocks or fabricated success results.
- Every `if`, `else if` and `else` branch body must use `{}`, including single-line branches and early returns. Fixed business values use domain constants or enums; mutable configuration must not be hidden in `const` / `static readonly`.
- Write code comments in Simplified Chinese. Public APIs use XML documentation for meaningful parameters, return values, exceptions and cancellation semantics; do not burden simple properties with redundant comments.
- Validate changes with the project's existing `dotnet build` and relevant tests, following its analyzer configuration. The skill's Python checkers do not scan C#; they are not C# validation evidence.
