# Developer Intelligence Platform

> 让 AI Agent 深度理解你的代码仓库——从静态分析到 GitHub 全景，本地优先，零 LLM 依赖。

[![License](https://img.shields.io/badge/License-GPL--3.0-orange)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab)](https://www.python.org/)

## 架构总览

```
repo-intel-core（底层引擎）
    ├── repo-onboarding-skill（新人引导文档）
    ├── repo-architect-skill（架构健康报告）
    └── github-intelligence（GitHub 全景分析 → lumen Agent）
```

## 子项目

| 项目 | 说明 | 状态 |
|---|---|---|
| [repo-intel-core](repo-intel-core/) | 跨语言仓库静态解析引擎，输出结构化 RepoProfile JSON | v0.1.0a0 |
| [repo-onboarding-skill](repo-onboarding-skill/) | 新人入门指南生成器，双模式（lite/full） | v0.1.0 |
| [repo-architect-skill](repo-architect-skill/) | 架构体检报告生成器，含 mermaid 图 | v0.1.0 |
| [github-intelligence](github-intelligence/) | 个人 GitHub 分析，SQLite + FTS5 + MCP 工具 | v0.0.1a0 |

## 快速开始

```bash
# 安装核心引擎
pip install -e "repo-intel-core[dev]"

# 扫描任意仓库
repo-intel scan <仓库路径> --pretty

# 查看模块依赖图
repo-intel graph <仓库路径> --format mermaid

# 查看月度演化信号
repo-intel signals <仓库路径> --months 6
```

## 设计原则

- **本地优先**：核心引擎零网络、零 LLM 依赖
- **幻觉防护**：所有声称追溯到扫描证据，缺失数据标注"未检测到"
- **表驱动扩展**：新语言/框架只需添加 YAML 规则文件
- **引擎/表现分离**：core 产出事实，LLM 解读交给上层消费者

## 技术栈

- Python 3.11+、pydantic v2、PyYAML
- SQLite（WAL）+ FTS5 全文搜索
- 可选：tree-sitter（AST 解析）

## License

GPL-3.0
