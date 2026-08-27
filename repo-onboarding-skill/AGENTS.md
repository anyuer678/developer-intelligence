# AGENTS.md — repo-onboarding-skill

## 项目一句话
对任何仓库生成《PROJECT_GUIDE.md》，让新人或 AI Agent 十分钟上手——dsh / Claude Code / opencode 通用的 Skill。

## 命令
- 全量测试: `pytest`（dev 依赖仅 pytest；scan.py 本体零第三方依赖）
- lint: `ruff check skill tests`（若安装了 ruff）
- 冒烟: `python skill/scripts/scan.py . --pretty`
- 再生 golden: 无（本仓库暂无快照基线）

## 架构地图
- `skill/SKILL.md` — agent 读的技能说明书（frontmatter: name/description）
- `skill/scripts/scan.py` — 双模式扫描入口：探测到已安装 repo-intel-core → full 模式；否则内置 lite 启发式
- `templates/PROJECT_GUIDE.template.md` — 输出文档七节结构（与 prompts 附录 A 对应）
- `prompts/system.md` + `prompts/user-skeleton.md` — LLM 层冻结稿（prompt=产品，改动走人工审批）
- `tests/` — lite 扫描器行为 + 与 core 的字段契约 + SKILL 文件 lint

## 当前状态
- 已完成: v0.1 全部六卡——双模式扫描器 / SKILL.md / 模板与 prompts 冻结稿 / 契约测试，14 测试全绿
- 挂起（需人工）: README 第一屏 GIF 录制
- 已完成自举验证#1: 为 repo-intel-core 生成 PROJECT_GUIDE（full 模式），发现并回修引擎两问题——详见 docs/decisions.md
- 下一步: Gate 1 发布动作（见母目录 02 号计划书 §十三发布日清单）；v0.2 卡（GitHub URL 直达/英文输出）待 Gate 结果

## 硬约束（违反即返工，无例外）
1. `skill/scripts/scan.py` **只允许标准库**——lite 模式承诺"clone 即用，不装任何东西"
2. lite 输出的字段名必须与 RepoProfile Schema v1.0 子集**逐字一致**（camelCase）；契约测试守护
3. `prompts/*.md` 与 `skill/SKILL.md` 属产品本体：任何修改需在 docs/decisions.md 记 ADR 并经人批准
4. 不绑定任何宿主专有 API；三宿主接入只靠 SKILL.md 约定 + 一个 python 脚本调用
5. 幻觉防线不可绕过：事实内容只能来自扫描 JSON，缺失写"未检测到"
6. 注释与文档用中文；commit 用 Conventional Commits

## 完成定义
新代码有对应测试 + pytest 全绿 + 冒烟命令正常输出 JSON。
