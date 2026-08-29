# Repo Architect Skill

[![Version](https://img.shields.io/badge/%E7%89%88%E6%9C%AC-v0.1.0-blue)](https://github.com/anyuer678/repo-architect-skill) [![License](https://img.shields.io/badge/License-MIT-green)](LICENSE) [![Engine](https://img.shields.io/badge/%E5%BC%95%E6%93%8E-repo--intel--core%3E%3D0.1-6db3f2)]() [![Hosts](https://img.shields.io/badge/%E5%AE%BF%E4%B8%BB-dsh%20%C2%B7%20ClaudeCode%20%C2%B7%20opencode-8a2be2)]()

> **架构体检报告生成器** —— 模块职责、依赖耦合、数据流、mermaid 架构图、风险与分级建议，一份报告说清一个仓库的骨架。

**不做**重构执行（只体检与规划），**不做**泛泛而谈的"代码评价"，而是**基于依赖图证据的架构叙事**：

```
扫描：模块划分 → 依赖图(weight) → 框架/构建 → 热点指标
        ↓
报告：八节结构 + mermaid 图 + 每条建议【高/中/低置信】+ 证据字段引用
```

## 功能特性

| 能力域 | 说明 |
|---|---|
| 🧩 模块分析 | 顶层模块 × 文件数 × 内聚度三态；职责句由 LLM 归纳并强制标注"据扫描结果推断" |
| 🕸️ 架构图 | `architectureMermaid` 现成渲染——节点=模块、边=依赖权重 |
| 🔗 耦合解读 | 内部边按权重排序逐条解读；外部依赖按 runtime/dev 分面 |
| ⚠️ 风险引用制 | 第 6 节每条风险必须挂 metrics/warnings 字段；无证据判断集中到附录"纯推测区" |
| 💡 建议分级 | 【高/中/低置信】+ 证据引用；杜绝拍脑袋重构建议 |
| 🖥️ 三宿主通用 | dsh · Claude Code · opencode |

## 快速开始

```bash
# 前置：安装引擎（本 Skill 无降级模式，ADR-001）
pip install "repo-intel-core>=0.1"

python skill/scripts/scan.py scan <仓库路径> --pretty   # 扫描（含 architectureMermaid）
# 随后按 SKILL.md 工作流让 agent 撰写 ARCHITECTURE_REPORT.md
```

宿主接入：

```text
dsh          加入技能路径 → 对 agent 说「给当前仓库做一次架构体检」
Claude Code  cp -r skill ~/.claude/skills/repo-architect/
opencode     cp -r skill ~/.config/opencode/skills/repo-architect
```

> 为什么硬依赖引擎：架构报告的价值核心是模块依赖图，lite 级启发式给不出可信耦合结论。

## 报告结构

```
1 项目概览 → 2 技术栈 → 3 模块分析 → 4 内部依赖与数据流(mermaid)
→ 5 入口与构建 → 6 架构风险 → 7 优化建议(分级)
+ 附录 A 数据来源说明（含纯推测区）
```

## 文档

- `skill/SKILL.md` 工作流 · `templates/ARCHITECTURE_REPORT.template.md` · `prompts/system.md`
- 引擎：[repo-intel-core](https://github.com/anyuer678/repo-intel-core) · 姊妹：[repo-onboarding-skill](https://github.com/anyuer678/repo-onboarding-skill)

## 常见问题

| 症状 | 排查 |
|---|---|
| 提示未检测到引擎 | `pip install "repo-intel-core>=0.1"` 后重试（退出码 3 = 缺引擎） |
| modules 全为 null | 仓库过小或语言未覆盖——报告会如实说明而非硬写 |
| 和 Onboarding 有什么区别 | 一个给人入门地图，一个给维护者看骨架；共用同一引擎不同叙事 |

## 贡献

欢迎参与！所有贡献默认按本项目 MIT 许可证发布。

## 免责声明

本项目仅供学习交流与演示用途，不构成任何形式的商业服务或技术承诺。软件按「现状」提供，不作任何明示或暗示的保证。您理解并同意：使用本项目即表示您自行承担全部风险；作者不因使用本软件所直接或间接产生的任何损失承担责任。本项目不适用于生产环境或关键业务场景。

## License

本项目按 **MIT** 协议提供。完整协议文本见 [LICENSE](LICENSE)。

详细版本历史见 [CHANGELOG.md](CHANGELOG.md)。
