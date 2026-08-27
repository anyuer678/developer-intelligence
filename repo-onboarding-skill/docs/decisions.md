# 决策日志（ADR-lite）

格式：`日期 | 决定 | 落选方案 | 理由 | 复盘信号`

---

- 2026-08-26 (B线) | lite 扫描器零第三方依赖、单文件 ≤300 行 | 直接依赖 core | Gate 1 成败取决于 clone 即用；降级是第一印象的底线 | 若 lite 产物质量投诉集中，提前把部分规则下沉 core 并要求装包
- 2026-08-26 (B线) | lite 字段名与 RepoProfile v1.0 子集逐字一致 | 自造简化格式 | 上层模板/prompt 零改动兼容两模式；契约测试可机械执行 | schema 升版时同步本仓契约测试
- 2026-08-26 (B线) | 完整模式用 importlib.find_spec 探测 pip 安装的 core | subprocess 调 CLI / vendored 复制 | 同进程拿 pydantic 对象最稳；vendored 会双份漂移 | 用户反馈"装了 core 仍是 lite"时加版本握手打印
- 2026-08-26 (B线) | prompts 以文件形式入库并冻结版本 | prompt 写死在 SKILL.md 正文 | prompt=产品需走审批门；分离后可单独 diff 与回滚 | 每次改 prompt 必须附评测对比（3 标准仓库 checklist）
- 2026-08-26 (M3后) | 自举验证#1：用本 skill 为 repo-intel-core 生成 PROJECT_GUIDE | 仅人工抽检 | 发现并回修两个引擎问题：入口点内容信号未排除 tests/ 目录；buildRun 在缺 requirements.txt 时仍推荐该安装命令。狗粮闭环成立 | 每次核心发版前对自有仓库重跑一轮自举
- 2026-08-26 (B线) | stdlib 守卫只约束模块级导入，函数内条件导入（full 分支探测 core）豁免 | 一刀切禁止任何第三方 import 名出现 | lite 零依赖承诺针对的是运行路径；条件导入在未装 core 时永不执行 | 若发现守卫被滥用绕过，改为白名单机制
