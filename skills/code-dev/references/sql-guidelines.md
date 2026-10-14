# SQL schema documentation

These mandatory rules apply to SQL initialization files such as `init.sql`, schema creation and migrations. Determine the database dialect and supported version before choosing syntax. Keep skill prose in English; write table/column descriptions and SQL explanatory comments in Simplified Chinese.

- Describe each table's business purpose with a `-- ` comment before its definition and database metadata: MySQL/MariaDB table `COMMENT`, PostgreSQL `COMMENT ON TABLE`, SQL Server extended properties, or the dialect's equivalent. Do not invent unsupported syntax; for engines without metadata comment support, retain source comments and explicitly state that limitation.
- Give every column a database metadata description, including primary keys, status, counters, timestamps and foreign-key identifiers. For MySQL/MariaDB use inline `COMMENT '...'`; other engines use their native metadata mechanism. This is SQL metadata, not a Java-style annotation.
- Add a trailing `-- ` explanation to **every column definition line**, including columns that already have a metadata comment. Explain what the field is used for, meaningful units, states, null semantics or relationships where relevant; do not merely repeat the identifier. Each definition occupies its own line. Put commas before `-- ` so they are not commented out. Keep the required space after `--`.
- Use table-level constraints on separate lines; do not mistake constraints for columns. If a migration adds or changes a column or its semantics, update both its metadata comment and source explanation. Do not edit an already-applied shared migration merely to add comments; create a follow-up migration using supported comment-alteration syntax.
- Preserve the existing schema, names and defaults unless the requested change requires otherwise. Do not copy default expressions across dialects or alter timestamp semantics solely to add documentation.

For MySQL, the following example documents every field and the table. Its inline comments are not portable to all SQL engines; verify timestamp defaults against the target version.

```sql
-- 保存语义体检报告及其检查结果汇总。
CREATE TABLE lint_reports (
    id VARCHAR(36) NOT NULL COMMENT '报告主键 UUID', -- 唯一标识一次体检报告，供查询和关联结果使用。
    status VARCHAR(16) NOT NULL COMMENT '体检状态', -- 记录体检生命周期状态，取值遵循应用的状态枚举。
    checked_page_count INTEGER NOT NULL COMMENT '检查的页面数', -- 记录本次已检查页面的数量，单位为页。
    issue_count INTEGER NOT NULL COMMENT '问题总数', -- 汇总本次体检发现的问题数量，单位为条。
    summary TEXT COMMENT '语义检查的整体结论', -- 保存整体结论；尚未生成结论时可为空。
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '体检开始时间', -- 记录体检开始时间，便于追踪执行耗时。
    finished_at DATETIME COMMENT '体检结束时间', -- 记录体检结束时间；未结束时为空。
    PRIMARY KEY (id)
) COMMENT = '语义体检报告，记录检查进度、问题数量及整体结论';
```

Review table descriptions, every column's metadata and trailing explanation, comma placement and dialect correctness. Execute affected DDL against an isolated database of the project's actual dialect/version when available; otherwise report that SQL execution is unverified. Do not claim execution validation from text inspection alone. Existing source checkers do not validate these SQL rules.
