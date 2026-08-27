# Changelog

## [Unreleased]
- （暂无）

## [0.1.0] - 2026-08-26

### Added
- 双模式扫描入口 `skill/scripts/scan.py`：
  - lite（零第三方依赖）：语言统计 / manifest 与根标记收集 / 入口粗判（bin、`__main__`、FastAPI、Go main、createApp）/ buildRun 推断（scripts+Makefile+生态默认，置信度固定 0.6）/ 默认排除 + `.repointelignore`
  - full 自动升级：探测到 `repo-intel-core>=0.1` 时切换引擎，输出全字段
- `skill/SKILL.md`：五步工作流（扫描→校验→按模板撰写→来源附录→交付）与禁止事项
- `templates/PROJECT_GUIDE.template.md`：七节结构 + 每节数据来源注释
- `prompts/system.md` 反幻觉铁律与自检清单（v1 冻结稿）、`prompts/user-skeleton.md`
- 测试 14 项：lite 行为、双模式调度、字段契约（键集 ⊆ Schema v1.0）、SKILL 文件 lint

[0.1.0]: https://github.com/anyuer678/repo-onboarding-skill/releases/tag/v0.1.0
