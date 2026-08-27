# Changelog

## [Unreleased]

## [0.0.1a0] - 2026-08-26

### Added
- P0 准备阶段（时序锁合规：无任何网络/采集代码）
  - 实体 ID 契约 `{connector}:{type}:{native_id}` 与 content_hash（NFC+CRLF 归一）
  - SQLite Schema v1：repos/commits/issues/releases/my_stars/dependencies/sync_state
  - FTS5 外部内容表 + AFTER INSERT 触发器（commits/issues/repos）
  - db 工具层：WAL、foreign_keys、幂等 init_db、schema_meta/user_version 双版本记录
### Added (锁内先行)
  - Evolution Timeline 算法引擎：稀疏月合并 / 特征余弦边界(含日历缺口强制切分) / 小阶段并邻 / summary·json·gantt 渲染 / --labels 命名注入钩子
  - pgi timeline 子命令；timeline_analysis 表（_analysis 约定首例）
- 跨仓集成冒烟：repo-intel signals → pgi timeline
  - Analyst 检索层 pgi ask：FTS 关键词召回 + 中文时间表达式解析(v1 十类) + 来源标签证据块组装；LLM 回答外置
  - lumen 接入层：memory_search/get/timeline/related/observe 五工具 + 最小 stdio JSON-RPC 调度器（pgi mcp）
- 测试 17 → 30 → 46 → 57 项

[0.0.1a0]: https://github.com/anyuer678/github-intelligence/releases/tag/v0.0.1a0
