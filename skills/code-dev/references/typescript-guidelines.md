# TypeScript/JavaScript Application Guidelines

Before creating or moving files, read [cross-language ownership decisions](project-structure.md#cross-language-ownership-decisions) and determine the actual responsibility and domain.

These rules cover application and Node.js code; publishable packages also follow [package guidelines](typescript-package-guidelines.md).

- Follow the project's framework, runtime, module format and existing type-check/lint setup. Keep business ownership explicit; do not copy Java's mandatory interface/implementation pairs into TS/JS.
- Separate UI/HTTP boundaries, domain behavior and infrastructure according to the application type. Do not put database access, server secrets or server-only dependencies into browser code; browser applications call the project's API boundary.
- Static types do not validate network, configuration or persisted data at runtime. Validate untrusted inputs at the owning boundary using existing schema/validation mechanisms. Avoid `any`, unchecked casts and non-null assertions used merely to hide an unknown contract; narrow values or validate them instead.
- Await or explicitly manage promise lifecycles. Handle errors and cancellation for background work, and avoid blocking CPU-heavy or synchronous I/O on a Node.js request path. Do not add worker infrastructure unless the requirement warrants it.
- Every `if`, `else if` and `else` branch body uses `{}`, including single-statement guards. Write code comments in Simplified Chinese using applicable JSDoc/TSDoc syntax.
- Follow [configuration guidelines](configuration-guidelines.md) and the relevant [runtime boundaries](runtime-boundaries.md). Do not turn configurable values into exported constants.
- Validate changes with the project's type-check/build and relevant tests. A transpiler that strips types is not evidence that TypeScript type checking passed. Existing Python checkers do not scan TS/JS.
