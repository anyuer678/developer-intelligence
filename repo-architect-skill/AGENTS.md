# AGENTS.md — repo-architect-skill

## 项目一句话
对任何仓库生成《ARCHITECTURE_REPORT.md》：模块职责、依赖耦合、数据流、架构风险与优化建议——dsh / Claude Code / opencode 通用 Skill。

## 命令
- 全量测试: `pytest`
- 冒烟: `python skill/scripts/scan.py scan <仓库路径> --pretty`

## 架构地图
- `skill/SKILL.md` — 技能说明书
- `skill/scripts/scan.py` — **薄包装器**：硬依赖已安装的 repo-intel-core（无 lite 降级，ADR-001）
- `templates/ARCHITECTURE_REPORT.template.md` — 八节报告结构（沿用原始需求规格）
- `prompts/` — 架构师角色 system prompt（反幻觉铁律同源）+ user 骨架
- `tests/` — 包装器契约 + mermaid 渲染 + 文件 lint

## 当前状态
- v0.1 开发中，见 `docs/tasks/v0.1.md`

## 硬约束（违反即返工）
1. 本包装器**必须依赖 repo-intel-core>=0.1**——架构分析的核心输入是模块依赖图，lite 无此数据；缺失时明确报错并给安装指引，禁止静默降级
2. 报告七节 + 附录 A 结构不得增删一级标题；每条建议必须引用证据字段并标注置信
3. `prompts/*.md` 属产品本体：修改需记 ADR 并经人批准
4. 不绑定宿主专有 API；中文文档；Conventional Commits

## 完成定义
新代码有对应测试 + pytest 全绿 + 冒烟输出含 flowchart。
