# 代码注释与文档规范

## 范围与原则

- 用户明确要求和项目既有约定优先；默认用简体中文写新增注释，保留必要英文术语，不翻译无关旧注释。
- 只维护本次新增或修改涉及的注释，不顺带补齐全仓库。修改行为时同步修正已经过时的相关注释。
- 注释说明调用者需要知道的契约、业务原因、边界条件、顺序依赖、单位、空值、特殊值、副作用或实际异常；不要复述变量名、类型或显而易见的代码步骤。
- 简单 getter/setter、属性和转发方法可省略文档；不要为了清空静态检查提示堆砌注释。
- 不根据名称猜测线程安全、事务、幂等、异步或异常保证，只记录实现和项目契约确实保证的行为。
- 需要判断具体注释取舍时，读取 [代码注释示例](code-comment-examples.md)。

## Java

- 对外业务接口和公共 API 用 Javadoc 说明职责及调用者需要遵守的约束。
- 参数、返回值和异常只在需要补充语义时写 @param、@return、@throws，例如单位、范围、空值、特殊返回值或失败条件；不要重复 Java 类型。
- 实现与接口行为相同的重写方法可沿用项目的 @inheritDoc 约定；行为有差异时写出差异。
- 实现内部的行注释用于解释业务原因、并发条件或容易误改的限制，不逐行翻译代码。

## Python

- 遵循仓库选择的 docstring 风格；没有约定时，本技能默认 Google 风格。
- 使用三引号 docstring。函数或方法在契约需要时记录 Args、Returns、Raises；类和模块文档描述其职责及有用的公开内容。
- 简短且含义明显的函数或属性不强制添加 docstring。

## TypeScript

- 对外导出的包 API 使用 /** ... */ 文档注释，采用 TSDoc 可识别的写法；普通实现说明使用 // 或短块注释。
- 用 TypeScript 声明表达类型，不在注释里重复类型。@param、@returns、@throws 仅补充参数语义、返回约定和真实失败条件。
- 多段契约、业务背景或限制放在 @remarks；只有能帮助消费者正确调用时才加 @example；弃用 API 时用 @deprecated 并说明替代方案。
- 内部注释解释原因、边界或顺序约束。避免逐行复述实现，也不要为了文档工具给每个私有成员套模板。

## 待办标记

- 用 TODO(负责人): 原因或下一步记录确实未完成的工作。
- 负责人必须来自用户或项目约定；未知时说明待确认，不编造姓名，也不为满足格式新增 TODO。

## 可选检查器

新增或修改 Java/Python 文件后，如有帮助，可运行：

    python <项目指定解释器> <skill目录>/scripts/check_comments.py <改动文件或目录>

检查器只覆盖 Java 和 Python，并以启发式规则提供复核提示；WARNING 不要求全部清零，也不能证明注释语义正确。TypeScript 注释按上面的 TSDoc 约定和项目现有工具人工检查。

## 官方资料

- [Oracle：Javadoc 文档注释规范](https://docs.oracle.com/en/java/javase/22/docs/specs/javadoc/doc-comment-spec.html)
- [Python PEP 257：Docstring 约定](https://peps.python.org/pep-0257/)
- [Microsoft TSDoc：标准标签](https://tsdoc.org/pages/spec/tag_kinds/)
- [TypeScript：JSDoc 标签支持](https://www.typescriptlang.org/docs/handbook/jsdoc-supported-types.html)
