# Code Comment and Documentation Guidelines

## Scope and principles

- **Always write comments and documentation in Simplified Chinese**, keeping the necessary English terms (identifiers, framework names, protocol names). A project whose comments are in English must be rewritten to Chinese as well; this is mandatory.
- Comment scope is limited to the files touched by the current change: comments at the change site must be Chinese; pre-existing English comments in the same file are rewritten too; do not sweep the whole repository on the side.
- Comments state the contract the caller needs to know, the business reason, boundary conditions, ordering dependencies, units, null values, special values, side effects, or the exceptions that are actually thrown; never restate the variable name, the type, or obvious code steps.
- When a method or function contains multiple ordered business stages, it must be documented with numbered comments that follow the real structure: sibling steps use `1.`, `2.`, `3.`; sub-steps use hierarchy levels such as `1.1`, `1.2`, `1.2.1`. The numbering levels must correspond to real parent/child steps, not a fixed template. Number only meaningful stages and conditions, never every query or assignment; single-step methods, getters/setters, and simple forwarders take no numbering.
- Simple getters/setters, properties, and forwarder methods may omit documentation; never pile on comments just to silence static-analysis warnings.
- Never infer thread safety, transactional behavior, idempotency, asynchrony, or exception guarantees from a name; record only the behavior that the implementation and the project contract actually guarantee.
- To decide what a specific comment should contain, read [Code comment examples](code-comment-examples.md).

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

## TODO markers

- Always record genuinely unfinished work as `TODO(owner): reason or next step`. A TODO without an owner does not conform to this standard. `FIXME` and `XXX` must also carry an owner.
- The marker must appear at the start of the comment; mentioning "there is a TODO here" inside a sentence is explanatory prose and does not count as a TODO marker.
- The owner must come from the user or the project convention; when it is unknown, write "to be confirmed" — never invent a name, and never add a TODO just to satisfy the format.

## Checker

This standard is mandatory; run the checker after changing Java/Python files:

```sh
python <skill-dir>/scripts/check_comments.py <changed-file-or-dir>
```

Exit codes:

| Code | Meaning | Action |
| --- | --- | --- |
| 0 | No ERROR; WARNINGs may still be present | Judge each WARNING by hand |
| 1 | ERRORs are present | Must be fixed, then rerun |
| 2 | No `.java` / `.py` files matched | **Not the same as "no problems"** — check that the path is correct |

There are only two kinds of ERROR: the file cannot be parsed or read (a tool failure), and a TODO marker is missing its owner or its description. Fix the file in the first case; in the second, complete the marker into `TODO(owner): description` — never delete the TODO itself.

The checker covers Java and Python, heuristically flags complex methods for numbering review based on method length/branch count, and checks whether comments are in Simplified Chinese. Short methods that genuinely contain multi-stage logic must still be numbered by hand according to this standard. A WARNING never proves that a comment is semantically correct; never pile on comments to satisfy a meaningless warning. TypeScript comments are reviewed by hand against the TSDoc conventions above.

## Official references

- [Oracle: Javadoc documentation comments specification](https://docs.oracle.com/en/java/javase/22/docs/specs/javadoc/doc-comment-spec.html)
- [Python PEP 257: docstring conventions](https://peps.python.org/pep-0257/)
- [Microsoft TSDoc: standard tags](https://tsdoc.org/pages/spec/tag_kinds/)
- [TypeScript: JSDoc tag support](https://www.typescriptlang.org/docs/handbook/jsdoc-supported-types.html)