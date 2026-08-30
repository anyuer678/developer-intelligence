# pgi ↔ lumen 接入指南（方向 B 作为 lumen 插件）

> 采集器打通后，让 lumen 通过 MCP 调用 pgi 的 5 个 memory.* 工具——"理解仓库"成为 lumen 的能力。

## 前置

```bash
# 1. 安装 pgi（github-intelligence）
cd review3/developer-intelligence/github-intelligence
pip install -e ".[dev]"

# 2. 初始化库 + 采集（GITHUB_TOKEN 可选，匿名限流 60 次/小时）
pgi init --db ~/.pgi/pgi.db
GITHUB_TOKEN=xxx pgi sync --db ~/.pgi/pgi.db          # 全量采集
```

## lumen 注册 pgi MCP 服务器

lumen 通过 `POST /v1/mcp` 注册 stdio 服务器（`python` 在命令白名单内）：

```bash
curl -X POST http://127.0.0.1:18080/v1/mcp \
  -H "Authorization: Bearer $LUMEN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "pgi-memory",
    "command": "python",
    "args": ["-m", "pgi", "mcp", "--db", "<绝对路径>/pgi.db"],
    "transport": "stdio"
  }'
```

注册后 lumen 自动出现在 Tools 页：`mcp:pgi-memory/memory_search` 等 5 个工具。

> 注意：`args` 里的 `--db` 必须是绝对路径（lumen 子进程 cwd 不保证）。

## pgi 提供的工具（lumen 侧看到的名字）

| 工具 | 能力 | 典型问题 |
|---|---|---|
| `mcp:pgi-memory/memory_search` | FTS 召回 + 中文时间表达式 | "最近 7 天 lumen 的提交" |
| `mcp:pgi-memory/memory_get` | 实体详情 | "看这个 commit 详情" |
| `mcp:pgi-memory/memory_timeline` | 演化阶段甘特 | "这个项目分几个阶段" |
| `mcp:pgi-memory/memory_related` | 相关实体 | "还有谁是做 Agent 的" |
| `mcp:pgi-memory/memory_observe` | 写入观察 | "记一条观察" |

## 端到端路径

```
GITHUB_TOKEN=xxx pgi sync         # 1. 采集 28 仓的真实数据
pgi ask "本月提交密度"              # 2. CLI 直接问（无 lumen 也能用）
lumen 注册 pgi-memory              # 3. lumen 获得"理解仓库"能力
"lumen，分析我哪个仓库最有救"        # 4. lumen → mcp:pgi-memory/memory_search → 证据块 → LLM 总结
```

## 验证

```bash
# pgi 侧自检
pgi mcp --db ~/.pgi/pgi.db <<< '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

# lumen 侧
curl http://127.0.0.1:18080/v1/mcp -H "Authorization: Bearer $LUMEN_TOKEN"
# → 列表应含 pgi-memory
```

## 安全

- token 走 GITHUB_TOKEN 环境变量，不入库不写日志
- pgi MCP 只读查询（memory_observe 除外，写入 timeline_analysis）
- lumen 的 MCP command 白名单已包含 python，注册无额外风险