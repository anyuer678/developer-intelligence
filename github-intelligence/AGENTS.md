# AGENTS.md — github-intelligence (pgi)

## 项目一句话
理解个人 GitHub 世界的本地 AI 分析系统：采集 → SQLite → 分析 → Timeline → AI Analyst。

## 命令
- 全量测试: `pytest`
- lint: `ruff check src tests`（若安装）
- 重建本地库: `python -c "from pgi.db import init_db; init_db(':memory:')"` 冒烟

## 架构地图
- `db/schema.sql` — SQLite Schema v1 草案（事实表 + `_analysis` 预留命名 + FTS5 触发器）
- `src/pgi/ids.py` — 全局实体 ID 契约（04 号计划书 DS-0：{connector}:{type}:{native_id} + content_hash）
- `src/pgi/db.py` — 连接/init/meta 版本管理，WAL
- 未来: collector(🔒 时序锁) / timeline / analyst / cli

## 当前状态
- **P0 准备 + Timeline 先行**：schema/契约/工具层/Timeline 算法就绪；采集器仍锁
- 时序锁澄清（ADR）：纯函数分析层允许（Timeline/Analyst/MCP 工具层），网络/采集禁止
- 已知边界：memory_related 仅仓库依赖邻接；memory_observe 输出 R0 能力边界声明——均随连接器扩张兑现

## 硬约束（违反即返工，无例外）
1. 🔒 **时序锁**：02 号 Skill 过 Gate 1 之前，禁止编写任何 GitHub API/网络请求代码——本阶段只允许 schema、纯函数与本地工具
2. Schema 字段冻结规则：v1 定稿前可改但每改必记 ADR；定稿后 add-only
3. 分析结果一律进 `*_analysis` 后缀表并带 model 版本列，永不污染事实表
4. 实体 ID 必须经 `pgi.ids` 构造/校验，禁止手拼字符串
5. 密钥/Token 永不入库不入日志（未来接 keyvault）
6. 注释与文档用中文；commit 用 Conventional Commits

## 完成定义
新代码有对应测试 + pytest 全绿 + ruff 零告警。
