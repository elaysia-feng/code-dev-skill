# C++ Guidelines

Before creating or moving files, read [cross-language ownership decisions](project-structure.md#cross-language-ownership-decisions) and determine the actual responsibility and domain.

These rules apply to C++ implementation, review and refactoring alongside the skill's general rules.

- Follow the project's C++ standard, toolchain and build system; do not upgrade language versions or replace build systems merely to apply these rules.
- Use RAII for memory, files, locks and other resources; prefer value semantics and standard containers. Use `std::unique_ptr` for exclusive dynamic ownership and `std::shared_ptr` only when shared ownership is required. Make borrowing and lifetimes explicit for raw pointers and references.
- Express read-only constraints with `const`; represent fixed business values with domain constants or `enum class`. Do not place mutable configuration in `constexpr` or preprocessor macros. Follow the [configuration guidelines](configuration-guidelines.md).
- Do not apply Java's interface and `impl/` requirements. Introduce abstract base classes only for actual polymorphic contracts, replacement boundaries or testing needs.
- Every `if`, `else if` and `else` branch body must use `{}`, including single-line branches and early returns.
- Check object lifetimes, bounds, dangling references, integer conversions and concurrent access. Destructors must not propagate exceptions. Follow the project's exception or return-value contract; do not silently discard errors.
- Write code comments in Simplified Chinese. Public API documentation describes ownership, lifetimes, failure conditions and concurrency constraints using the project's Doxygen or equivalent format.
- Validate changes with the project's build and relevant tests. Use appropriate sanitizers for memory or concurrency issues when supported by the toolchain. The skill's Python checkers do not scan C++; they are not C++ validation evidence.
