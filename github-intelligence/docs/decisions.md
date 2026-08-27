# 决策日志（ADR-lite）

- 2026-08-26 (P0) | 提前进入 P0 准备阶段（schema/契约） | 等 Gate 1 | 03 计划书时序锁原文明确允许"M0 准备(schema 设计)"；用户指示离线继续开发 | 锁内文件若出现网络 import 即违规自查
- 2026-08-26 (P0) | 实体 ID 采用 04 §三契约 `{connector}:{type}:{native_id}` | 自造整数主键体系 | 04 DS-0 要求"现在就定"；字符串 ID 免映射表且跨连接器唯一 | 性能瓶颈出现时再加内部自增代理键
- 2026-08-26 (P0) | FTS5 用 external content + AFTER INSERT 触发器 | 应用层双写 | 单一写入路径防漏同步；SQLite 原生机制零维护成本 | 删除/更新同步 bug 出现时补 BEFORE/AFTER UPDATE|DELETE 触发器（v1 先 INSERT 场景）
- 2026-08-26 (P0) | 分析表现在只冻结 `_analysis` 后缀命名约定，不建任何表 | 预建空表 | YAGNI；模型版本列格式待首个分析模块定型时一并设计 | M1 Profile 落库时兑现
- 2026-08-26 (P0) | FTS5 中文按 unicode61 整串成 token，v1 按完整短语匹配 | 引入 jieba/ICU 自定义分词 | 零依赖优先；中文检索是 L1 兜底层，语义层(embedding)才是主力 | Analyst 中文查询召回率不足时升级 tokenizer
- 2026-08-26 (P0) | FTS 触发器补全 UPDATE/DELETE 三表全量（取代前条 INSERT-only 决定） | 维持 INSERT-only | 删除/更新不同步是数据正确性缺陷而非边缘场景；external-content 官方触发器范式成本极低 | 无
- 2026-08-26 (P0) | Timeline 算法引擎提前至锁内实现 | 等采集器就绪再写 | 输入仅依赖 core signals JSON(本地 git 可产)，纯函数零网络——不违反时序锁字面与精神；核心卖点因此可立即对任意本地仓库演示 | 无
- 2026-08-26 (P0) | LLM 阶段命名外置为 --labels 注入钩子 | 内置 provider 调用 | 引擎零 LLM 原则延续；命名质量迭代不应阻塞确定性切片边界算法 | M2 接 Analyst 时统一 provider 抽象
- 2026-08-26 (P0) | 子进程调用兄弟仓 CLI 强制 PYTHONIOENCODING=utf-8 | 依赖控制台代码页 | Windows 中文环境 GBK stdout 会污染 JSON 管道；显式 env 一行根治 | 所有跨仓 subprocess 沿用此模式
- 2026-08-26 (P0) | Analyst v1 分词用「CJK 串去停用词余段」而非 jieba | 引入分词库 | 零依赖纪律；检索层有 L2 embedding 兜底，L1 只需够用的召回 | 中文查询召回率不足时升级 tokenizer（与 FTS 条目同一触发器）
- 2026-08-26 (P0) | 「近N个月」实现为滚动窗口(锚定今日日) | 整月自然月窗口 | 与「最近N天/周」口径一致，符合口语直觉 | 用户反馈偏好整月口径时切换
- 2026-08-26 (P0) | MCP 面用自写最小 stdio JSON-RPC（initialize/tools.list/call/ping） | 引入官方 mcp SDK | 锁内禁第三方依赖；五工具消息面极小，自写约百行可控 | 接 lumen 需要资源/订阅/sampling 时换官方 SDK（届时锁已解）
- 2026-08-26 (P0) | memory_observe v1 诚实输出 R0 能力边界声明 | 硬编规则假装工作 | 主动智能红线=只报告不执行；假观察比无观察更伤信任 | 连接器>=2 时逐条激活 R1-R4
