# Repo Onboarding Skill

[![Version](https://img.shields.io/badge/%E7%89%88%E6%9C%AC-v0.1.0-blue)](https://github.com/anyuer678/repo-onboarding-skill) [![License](https://img.shields.io/badge/License-MIT-green)](LICENSE) [![Mode](https://img.shields.io/badge/lite-%E9%9B%B6%E4%BE%9D%E8%B5%96-success)]() [![Hosts](https://img.shields.io/badge/%E5%AE%BF%E4%B8%BB-dsh%20%C2%B7%20ClaudeCode%20%C2%B7%20opencode-8a2be2)]()

> **《新人入门指南》生成器** —— 对任何仓库说一句话，产出让人或 AI Agent 十分钟上手的 PROJECT_GUIDE.md。

**不做**通用 Code Review，**不做**聊天机器人，而是**给新人和 AI 的项目地图**：

```
问题：接手新项目 → 翻目录猜架构 → 试命令踩坑 → 半小时没了
        ↓
方案：静态扫描（证据链）→ LLM 只组织语言 → 七节指南 + 来源附录
```

## 功能特性

| 能力域 | 说明 |
|---|---|
| 🗺️ 七节指南 | 项目是什么 / 技术栈 / 五分钟跑起来 / 目录地图 / 核心流程 / 改动从哪进 / 已知风险 |
| 🔬 双模式 | lite 零依赖开箱即用；装 repo-intel-core 自动升级 full（+模块依赖图/框架/构建推断） |
| 🛡️ 幻觉防线 | 事实只允许来自扫描 JSON；缺失写"未检测到"；附录 A 逐节标注数据来源 |
| 🖥️ 三宿主通用 | dsh · Claude Code · opencode——一个 SKILL.md 通吃，不绑专有 API |
| 🔌 LLM 可插拔 | DeepSeek 默认，OpenAI 兼容协议，支持 Ollama 本地模型 |

## 快速开始

**方式一：宿主接入**（推荐）

```text
dsh          把 skill/ 加入技能路径 → 对 agent 说「给当前仓库生成入门指南」
Claude Code  cp -r skill ~/.claude/skills/repo-onboarding/
opencode     cp -r skill ~/.config/opencode/skills/repo-onboarding
```

**方式二：直接跑扫描器**

```bash
python skill/scripts/scan.py scan <仓库路径> --pretty     # lite 模式（零依赖）
python skill/scripts/scan.py scan <仓库路径> --debug      # 完整 JSON 走 stderr（issue 反馈用）
pip install "repo-intel-core>=0.1"                        # 可选：升级 full 模式
```

> 前置要求：Python 3.11+。lite 模式纯标准库；隐私——扫描全本地，LLM 仅接收 JSON 摘要。

## 工作原理

```
用户一句话
   │
scan.py ──auto──▶ lite 内置启发式 │ full(repo-intel-core)
   │      RepoProfile JSON（字段契约逐字一致）
   ▼
LLM 按 templates/PROJECT_GUIDE.template.md 七节撰写
   │  prompts/system.md 反幻觉铁律 + 自检清单
   ▼
PROJECT_GUIDE.md（附录 A 标注每节来源）
```

## 文档

- `skill/SKILL.md` 工作流 · `templates/` 输出模板 · `prompts/` 冻结稿
- 引擎侧：[repo-intel-core](https://github.com/anyuer678/repo-intel-core) · 姊妹：[repo-architect-skill](https://github.com/anyuer678/repo-architect-skill)

## 常见问题

| 症状 | 排查 |
|---|---|
| 装了 core 还是显示 lite | 确认安装在同一 Python 环境；`SCAN_MODE` warning 显示当前实际模式 |
| 某条命令在指南里跑不通 | 该命令必然来自扫描证据——提 issue 附 JSON（`--debug`）定位规则缺口 |
| 中文仓库乱码？ | 不应发生；全程 UTF-8 处理 |

## 贡献

欢迎参与！报告 Bug、补宿主接入示例、改进模板均可。所有贡献默认按本项目 MIT 许可证发布。

## 免责声明

本项目仅供学习交流与演示用途，不构成任何形式的商业服务或技术承诺。软件按「现状」提供，不作任何明示或暗示的保证，包括但不限于适销性、特定用途适用性与非侵权性。

您理解并同意：使用本项目即表示您自行承担全部风险。如您在使用过程中发现缺陷或问题，欢迎通过 GitHub Issues 反馈，但作者不因使用本软件所直接或间接产生的任何损失（包括但不限于数据丢失、业务中断、第三方索赔）承担责任。

本项目以功能演示与学习交流为主要目的，不适用于生产环境或关键业务场景；由此产生的任何直接或间接不良后果，开发者均不承担任何责任。

## License

本项目按 **MIT** 协议提供。完整协议文本见 [LICENSE](LICENSE)。

详细版本历史见 [CHANGELOG.md](CHANGELOG.md)。
