# Code Comment and Documentation Guidelines

## Scope and principles

- 新增和修改的说明性注释、文档使用简体中文，保留必要英文术语、标识符和工具指令。未修改的历史注释不顺带翻译，除非用户明确要求。
- Comments state the contract the caller needs to know, the business reason, boundary conditions, ordering dependencies, units, null values, special values, side effects, or the exceptions that are actually thrown; never restate the variable name, the type, or obvious code steps.
- When a method or function contains multiple ordered business stages, it must be documented with numbered comments that follow the real structure: sibling steps use `1.`, `2.`, `3.`; sub-steps use hierarchy levels such as `1.1`, `1.2`, `1.2.1`. The numbering levels must correspond to real parent/child steps, not a fixed template. Number only meaningful stages and conditions, never every query or assignment; single-step methods, getters/setters, and simple forwarders take no numbering.
- Simple getters/setters, properties, and forwarder methods may omit documentation; never pile on comments just to silence static-analysis warnings.
- Never infer thread safety, transactional behavior, idempotency, asynchrony, or exception guarantees from a name; record only the behavior that the implementation and the project contract actually guarantee.
- To decide what a specific comment should contain, read [Code comment examples](code-comment-examples.md).

### 必须覆盖的内容

- 新增、修改或审查代码时必须加载本文，不能等到用户要求“写注释”才加载。
- 有多个有序业务阶段的函数必须编号，与行数、可见性、是否已有 docstring/Javadoc 无关；私有辅助函数、异步函数、前端事件处理函数也适用。
- 单步函数、简单访问器和纯转发无需编号；长函数也不一定有多个业务阶段，按实际职责判断。
- 同级从 `1.` 连续递增；子步骤从父编号后的 `.1` 开始，必须先有父步骤。没有真实子步骤时不强凑 `1.1`。
- 完成前逐个核对本次新增或修改函数的文档契约、阶段覆盖和关键边界。检查器的行数阈值不能作为短函数豁免依据。

### Comments exempt from the Simplified Chinese requirement

The following stay as they are and are not language-checked:

- shebangs (`#!/usr/bin/env python3`) and encoding declarations (`# -*- coding: utf-8 -*-`)
- linter / type-checker directives: `# type:`, `# noqa:`, `# pylint:`, `# flake8:`, `# eslint-disable`, `# prettier-ignore`, `# spotless`
- code-generator headers (`Code generated ... DO NOT EDIT`)
- licence and copyright headers (`Copyright`, `Licensed under`, `SPDX-License-Identifier`)
- Javadoc `@author` (a person's name), `@see`, `@since`
- index comments consisting of nothing but a URL

Translating or deleting any of these is wrong: their content is fixed by the tool or by law.

## Java

- Use Javadoc on externally exposed business interfaces and public APIs to state their responsibility and the constraints callers must follow.
- Write `@param`, `@return`, and `@throws` only when they add semantics, such as units, ranges, null values, special return values, or failure conditions; never repeat the Java types.
- An override that has the same behavior as the interface must always use `@inheritDoc` instead of copying the contract; when the behavior differs, document the difference on the override.
- Multi-stage Java business methods must organize the method-body comments with the hierarchical numbering above; the numbers describe stages or business constraints and never replace the Javadoc contract.
- Line comments inside an implementation explain business reasons, concurrency conditions, or constraints that are easy to break by mistake; never translate the code line by line.

## Python

- Always use Google-style docstrings, regardless of what the repository currently does. Use triple-quoted docstrings. Document `Args`, `Returns`, and `Raises` on a function or method whenever the contract needs them; class and module documentation describes their responsibility and useful public content.
- Short, self-evident functions and properties are not required to have a docstring.

## TypeScript

- Externally exported package APIs use `/** ... */` documentation comments written in a form TSDoc recognizes; ordinary implementation notes use `//` or short block comments.
- Express types with TypeScript declarations and never repeat them in comments. `@param`, `@returns`, and `@throws` only add parameter semantics, return contracts, and real failure conditions.
- Put multi-part contracts, business context, or limitations in `@remarks`; add `@example` only when it helps consumers call the API correctly; for a deprecated API use `@deprecated` and state the replacement.
- Internal comments explain reasons, boundaries, or ordering constraints. Avoid restating the implementation line by line, and never apply a boilerplate template to every private member just to satisfy a documentation tool.

## C++ and C#

- C++ public APIs use the project's Doxygen or equivalent format to document ownership, lifetimes, errors and threading constraints.
- C# public APIs use XML documentation comments to describe meaningful parameters, return values, exceptions and cancellation semantics.
- Both languages follow this document's Simplified Chinese, stage numbering and comment scope rules. Do not apply Javadoc, TSDoc or Python docstring syntax. Preserve fixed generator and analyzer directives.

## TODO markers

- Always record genuinely unfinished work as `TODO(owner): reason or next step`. A TODO without an owner does not conform to this standard. `FIXME` and `XXX` must also carry an owner.
- The marker must appear at the start of the comment; mentioning "there is a TODO here" inside a sentence is explanatory prose and does not count as a TODO marker.
- The owner must come from the user or the project convention; when it is unknown, write "to be confirmed" — never invent a name, and never add a TODO just to satisfy the format.

## Checker

This standard is mandatory; run the checker after changing Java/Python files:

```sh
python <skill-dir>/scripts/check_comments.py <changed-file-or-dir> --fail-on warning
```

Exit codes:

| Code | Meaning | Action |
| --- | --- | --- |
| 0 | 未达到阻断阈值；默认模式仍可能有 WARNING | 逐条处理 WARNING，不能据此宣称规范通过 |
| 1 | 有 ERROR，或指定 `--fail-on warning` 时有 WARNING | 修正真实问题后重跑；豁免项说明源码依据 |
| 2 | No `.java` / `.py` files matched | **Not the same as "no problems"** — check that the path is correct |

There are only two kinds of ERROR: the file cannot be parsed or read (a tool failure), and a TODO marker is missing its owner or its description. Fix the file in the first case; in the second, complete the marker into `TODO(owner): description` — never delete the TODO itself.

检查器覆盖 Java/Python，根据行数和分支数提示疑似缺少阶段注释，并检查已写编号的重复、跳号及父子顺序。步骤检查独立于公开契约文档检查，也覆盖私有函数；它不能证明业务阶段完整、说明正确或中文确为简体。短函数、嵌套内部函数、Java 无修饰符或复杂声明等启发式解析未覆盖的情况必须人工核对。TypeScript 的契约与流程编号均人工核对，不假称工具覆盖。

WARNING 必须修正或记录适用豁免及源码依据；不为消除提示机械增加 `Args`、`Returns` 或逐行注释。暂存模式没有 Java/Python 变更时返回 `0` 并提示未检查文件，这不代表审查过其他语言。

## Official references

- [Oracle: Javadoc documentation comments specification](https://docs.oracle.com/en/java/javase/22/docs/specs/javadoc/doc-comment-spec.html)
- [Python PEP 257: docstring conventions](https://peps.python.org/pep-0257/)
- [Microsoft TSDoc: standard tags](https://tsdoc.org/pages/spec/tag_kinds/)
- [TypeScript: JSDoc tag support](https://www.typescriptlang.org/docs/handbook/jsdoc-supported-types.html)
