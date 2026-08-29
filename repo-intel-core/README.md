# Repo Intel Core

[![Version](https://img.shields.io/badge/%E7%89%88%E6%9C%AC-v0.1.0a0-blue)](https://github.com/anyuer678/repo-intel-core) [![License](https://img.shields.io/badge/License-MIT-green)](LICENSE) [![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab)](https://www.python.org/) [![Tests](https://img.shields.io/badge/%E6%B5%8B%E8%AF%95-110%20%E9%A1%B9%E5%85%A8%E7%BB%BF-brightgreen)]() [![LLM](https://img.shields.io/badge/LLM-%E9%9B%B6%E4%BE%9D%E8%B5%96-lightgrey)]()

> **跨语言仓库静态解析引擎** —— 把任意代码仓库变成结构化、可版本化、可离线生成的 RepoProfile JSON。

**不做** AI 写代码工具（区别于 Cursor / Copilot），**不做** LLM 封装层，而是**一切分析类工具的地基**：

```
仓库：扫描 → 语言识别 → 结构理解 → 工程体检 → 时间线信号
        ↓         ↓          ↓          ↓           ↓
产出：RepoProfile JSON（事实 + 置信度，零 LLM · 零网络 · 一条命令）
```

## 功能特性

| 能力域 | 说明 |
|---|---|
| 🗣️ 语言识别 | 三级信号融合：扩展名统计 → manifest → 无扩展名 shebang 指纹；monorepo 显式判定 |
| 🚪 入口点检测 | 规则表驱动：`__main__` / FastAPI / Flask / Django / Go main / node bin / createApp / Electron |
| 🧩 模块依赖图 | 三语言 import 解析 → 模块级有向边（weight 聚合）+ cohesion 三态；mermaid 导出 |
| 🏗️ 框架识别 | 36 条 yaml 规则（前端/Web×3生态/AI-LLM/ORM/测试/工具链），声明依赖 > glob > 内容三路信号 |
| 🔧 buildRun 推断 | package.json scripts > Makefile > CI `run:` 三源交叉 + 锁文件判包管理器 + 置信分级 |
| ⏱️ GitMeta + 信号包 | 首末提交/贡献者/月度活跃；`signals` 月度切片（deps_added/new_dirs/top_terms）供 Timeline 使用 |
| 🩺 质量指标 | 复杂度热点启发式 / 测试证据 / TODO-FIXME 字节计数 |
| 🛡️ 排除体系 | 默认清单剪枝 + `.repointelignore` + 超大文件降级——永远部分成功，不抛异常 |

## 快速开始

```bash
pip install -e ".[dev]"

repo-intel scan <仓库路径> --pretty            # 终端摘要（语言/框架/构建命令）
repo-intel scan <仓库路径> -o profile.json     # 完整 RepoProfile JSON
repo-intel graph <仓库路径> --format mermaid   # 模块依赖图
repo-intel signals <仓库路径> --months 6       # 月度信号包（Timeline 输入）
repo-intel evolution <仓库路径> --days 30      # numstat 演化统计+热点规则
```

可选参数：`--skip-git` 跳过 git 元数据；`.repointelignore` 自定义排除（语法同 gitignore 子集）。

> 前置要求：Python 3.11+。运行时仅依赖 pydantic 与 PyYAML；规则表全部外置 yaml，加语言/框架不改代码。

## 系统架构

```
CLI (repo-intel scan|graph|signals)
        │
   scanner.py 单趟 os.walk（剪枝式排除）
        │
 detect/ 语言三级信号 · 入口模式表 · 模块划分 · 框架 · buildRun · 质量
        │
 rules/*.yaml 表驱动（加语言不改代码）    gitmeta/ 只读 git 命令
        │
 schema/profiles.py —— pydantic 单一来源 = JSON Schema v1（camelCase 别名输出）
```

## 技术栈

| 层 | 技术 |
|---|---|
| 语言/运行时 | Python 3.11+（Windows 中文路径一等公民） |
| Schema | pydantic v2（别名序列化）+ JSON Schema 版本化 |
| 解析 | 启发式规则表 + tree-sitter（预留增强位） |
| 测试 | pytest + ruff + golden 快照基线（自有仓库回归集） |
| LLM | **零依赖**——语义判断留给上层消费者 |

## 文档

- [PROJECT_GUIDE.md](PROJECT_GUIDE.md) —— 新人/AI 入门指南（由姊妹 Skill repo-onboarding 自举生成）
- [AGENTS.md](AGENTS.md) —— AI 协同开发约束 · [docs/tasks/](docs/tasks/) 里程碑任务卡 · [docs/decisions.md](docs/decisions.md) 决策日志
- 全景路线与计划书见母目录 `00~06` 号文档

## 常见问题

| 症状 | 排查 |
|---|---|
| 输出里出现 `PARSE_SKIPPED` / `BIG_FILE_SKIPPED` | 正常降级：超大文件只计数不解析，不影响其余字段 |
| monorepo 语言占比"不对" | 已按 workspace 切分告警（MIXED_MONOREPO）；细粒度子 profile 在路线图中 |
| 未识别的语言/框架 | 规则表驱动——直接提 PR 往 `rules/*.yaml` 加一条即可 |
| Windows 中文路径报错？ | 不应发生；路径处理默认 UTF-8，遇到即提 issue |

## 贡献

欢迎参与！报告 Bug、补规则表、改进文档均可。所有贡献默认按本项目 MIT 许可证发布。

## 免责声明

本项目仅供学习交流与演示用途，不构成任何形式的商业服务或技术承诺。软件按「现状」提供，不作任何明示或暗示的保证，包括但不限于适销性、特定用途适用性与非侵权性。

您理解并同意：使用本项目即表示您自行承担全部风险。如您在使用过程中发现缺陷或问题，欢迎通过 GitHub Issues 反馈，但作者不因使用本软件所直接或间接产生的任何损失（包括但不限于数据丢失、业务中断、第三方索赔）承担责任。

本项目以功能演示与学习交流为主要目的，其架构设计、安全基线、容错机制与性能表现均未按生产级标准进行验证与加固，不适用于实际生产环境或关键业务场景。任何将本项目部署于生产系统、对外提供服务、或将其接入真实业务工作流的做法，均属使用者的自主决策行为；由此产生的任何直接或间接不良后果，开发者均不承担任何责任。

## License

本项目按 **MIT** 协议提供。完整协议文本见 [LICENSE](LICENSE)。

详细版本历史见 [CHANGELOG.md](CHANGELOG.md)。
