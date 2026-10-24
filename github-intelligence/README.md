# GitHub Intelligence (pgi)

[![Status](https://img.shields.io/badge/%E7%8A%B6%E6%80%81-P0%20%E5%87%86%E5%A4%87%E9%98%B6%E6%AE%B5-blue)]() [![License](https://img.shields.io/badge/License-MIT-green)](LICENSE) [![Tests](https://img.shields.io/badge/%E6%B5%8B%E8%AF%95-57%20%E9%A1%B9%E5%85%A8%E7%BB%BF-brightgreen)]() [![Storage](https://img.shields.io/badge/%E5%AD%98%E5%82%A8-SQLite%20%2B%20FTS5-003b57)]()

> **理解个人 GitHub 世界的本地 AI 分析系统** —— 不只是数 commit，而是回答"我做过什么、怎么成长、哪个项目值得继续"。

**不做**团队协作平台，**不做**云端 SaaS，而是**个人视角的本地-first 数字档案**：

```
GitHub API ──采集──▶ SQLite(事实) ──▶ Timeline / Analyst / 观察报告
                                          │
                              CLI(pgi) · MCP(memory.* 五工具 → lumen)
```

## 功能特性

| 能力域 | 状态 | 说明 |
|---|---|---|
| 🗝️ 实体 ID 契约 | ✅ | `{connector}:{type}:{native_id}` + content_hash（跨连接器唯一，04 号 DS-0） |
| 🗄️ Schema v1 | ✅ | repos/commits/issues/releases/my_stars/dependencies + FTS5 外部内容表全触发器 |
| 📈 Evolution Timeline | ✅ | 稀疏月合并 · 特征余弦边界（含日历缺口强制切分）· summary/json/gantt 渲染 · LLM 命名外置钩子 |
| 💬 Analyst 检索层 | ✅ | FTS 安全召回 + 中文时间表达式解析（十类）+ 来源标签证据块——LLM 回答外置 |
| 🔌 lumen 接入层 | ✅ | `memory.search/get/timeline/related/observe` 五工具 + 最小 stdio JSON-RPC 调度器 |
| ✅ 采集器 | 已实测 | REST 分页 + 限流重试 + UPSERT 增量（2026-10-24 实测：37 仓 / 1395 commits / 321 issues / 35 releases） |

## 快速开始

```bash
pip install -e ".[dev]"

pgi init --db pgi.db                                  # 初始化本地库（幂等，WAL）
repo-intel signals <任意本地git仓库> -o pack.json      # 引擎侧产信号包（姊妹仓）
pgi timeline --signals pack.json --format gantt       # 演化阶段甘特图
pgi ask "最近一个月 sandbox 相关的提交"                 # Analyst 检索层
pgi mcp                                               # stdio JSON-RPC：lumen 接入点
```

> 采集器已于 2026-10-24 实测打通（37 仓全量同步，记录见 docs/pgi-lumen-integration.md）；MCP 五工具完成 stdio 协议级预验，lumen 侧动态注册复验待做。pip wheel 分发待 fix/pgi-packaging 合入（schema.sql 随包）。隐私红线不变：Token 经 keyvault 存取、永不入库不入日志。

## 系统架构

```
GitHub API ──collector(🔒时序锁)──▶ SQLite(local.db)
                                        │
                    ┌───────────────────┼────────────────────┐
              timeline.py          analyst.py           tools.py
          切片/边界/渲染        FTS召回+时间解析+证据块   memory.* 五工具
                    └───────────────────┼────────────────────┘
                                   cli (init/timeline/ask/mcp)
                                        └──▶ lumen (Agent Runtime 宿主)
```

## 技术栈

| 层 | 技术 |
|---|---|
| 存储 | SQLite（WAL）+ FTS5 外部内容表 + `_analysis` 表约定 |
| 语言 | Python 3.11+ 标准库为主（零第三方运行时依赖） |
| 检索 | FTS5 关键词层（L1）；L2 embedding / L3 关系遍历预留 |
| 接口 | stdio JSON-RPC 最小调度器（MCP 兼容面） |
| 上游 | repo-intel-core（信号包）· keyvault（密钥，未来） |

## 常见问题

| 症状 | 排查 |
|---|---|
| 采集器可用了吗？ | 是：`pgi sync`（2026-10-24 实测 37 仓全量；wheel 安装待 fix/pgi-packaging 合入，源码 `pip install -e .` 即可用） |
| 中文搜索搜不到词中间的内容 | FTS5 unicode61 对中文整串成 token——v1 按完整短语匹配，语义层由 embedding 兜底 |
| `pgi ask` 只出证据不给答案 | 设计如此：检索与生成解耦，答案由你选择的 LLM 层基于证据块产出 |

## 贡献

欢迎参与！所有贡献默认按本项目 MIT 许可证发布。

## 免责声明

本项目仅供学习交流与演示用途，不构成任何形式的商业服务或技术承诺。软件按「现状」提供，不作任何明示或暗示的保证。您理解并同意：使用本项目即表示您自行承担全部风险；作者不因使用本软件所直接或间接产生的任何损失承担责任。本项目不适用于生产环境或关键业务场景。

## License

本项目按 **MIT** 协议提供。完整协议文本见 [LICENSE](LICENSE)。

详细版本历史见 [CHANGELOG.md](CHANGELOG.md)。
