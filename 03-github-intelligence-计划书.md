# 03 · Personal GitHub Intelligence 计划书 —— 核心产品

> 性质：核心产品 · 路线的中枢
> 上游：01 repo-intel-core（M0-M1 即可开工）、GitHub API、keyvault
> 并入资产：stargrave（Star 清理逻辑）
> 下游：04 personal-data-os 的第一连接器；yuer.dev 展示出口；lumen 数据源
> 原始需求来源：2026-08 头脑风暴（Developer Dashboard / Repository Intelligence / Git 历史理解 / AI Analyst 等七项能力）

---

## 一、一句话定位

**一个理解开发者 GitHub 世界的本地 AI 分析系统：不只是数 commit，而是回答"我做过什么、怎么成长、哪个项目值得继续"。**

## 二、问题定义与产品哲学

### 普通工具和本产品的分界线

| 普通工具回答 | 本产品回答 |
|---|---|
| "你提交了 500 次" | "这个项目经历了 Demo→重构→Agent 化→稳定化四个阶段" |
| "你用了 TypeScript" | "你的技术重心 2025 在 Web，2026 转向 AI Agent 方向" |
| "你有 25 个仓库" | "这 3 个值得继续，这 5 个可以归档，理由如下" |

**核心哲学：从统计到叙事。** 数字谁都能算，叙事必须理解上下文——这就是 LLM + 本地数据库的价值所在。

### 差异化定位（竞品分析）

| 竞品 | 它做什么 | 它不做 | 我们的差异点 |
|---|---|---|---|
| GitHub 自带 Insights/Profile | 贡献图、语言条、活动流 | 无历史解读、无项目画像、不可问答 | Evolution Timeline + AI Analyst |
| OSS Insight | 全网仓库数据分析 | 面向项目不面向个人成长 | 个人视角 + 本地私有 |
| 各类 GitHub Wrapped（年度总结） | 一次性炫酷海报 | 用完即走，无沉淀 | 持续演进的本地数据库，越用越准 |
| github-profile-summary 类卡片 | 静态指标卡 | 同上 | 叙事层 |

**护城河排序：① Evolution Timeline（无人做好）② Developer Timeline ③ 本地 SQLite 可查询沉淀 ④ AI Analyst。** 前两项是宣传主卖点。

## 三、目标与非目标

### 目标

| # | 目标 | 验证标准 |
|---|---|---|
| G1 | 完整采集自己的 GitHub 世界 | 25 仓库全量入库：commit/issue/PR/release/star/依赖/语言 |
| G2 | 项目画像可用 | 每个 repo 一张 Project Profile 卡：定位/优势/风险/建议，自评 ≥80% 认可 |
| G3 | Timeline 卖点成立 | Gate 3：能准确说出自己每个项目的演化阶段 |
| G4 | 决策支持 | 对"哪些项目值得继续"给出有理由的清单，与自己的直觉对照 |
| G5 | 成本可控 | 单次全量分析 API 费用 ≤ 一杯奶茶钱（DeepSeek 计价下估算 <¥5） |

### 非目标

- ❌ 不做多人/团队版（个人数字世界是前提）
- ❌ 不做 SaaS / 云端存储（local-first 是前提）
- ❌ 不做实时监控（增量同步按天级即可）
- ❌ v1 不做组织账号分析（只做个人 + 其贡献过的开源仓库）
- ❌ 不重复造 README 生成器（那是 02 号 Skill 的事）

## 四、功能规格（七大能力 → 收敛为六模块）

> 原始头脑风暴的七项能力收敛：Dashboard 与 Developer Dashboard 合并；AI Analyst 与项目决策助手合并为一个问答层的两种问法。

### 模块 A · Data Collector（采集器）

```
GitHub Token（经 keyvault 取用）
   │  GraphQL 批量查询（一次拉多仓库关键字段，省 rate limit）
   ▼
全量首扫 ──▶ 增量同步（记录 last_synced_at，条件请求 ETag 缓存）
   │
   ├─ repos: 元数据/描述/topics/fork/archived
   ├─ commits: sha/message/时间/additions/deletions/文件列表
   ├─ issues & pulls: 标题/状态/标签/时间线
   ├─ releases & tags
   ├─ stars: 我 star 过的仓库 + 我的仓库被 star 数
   ├─ languages & dependencies
   └─ contributors（自己仓库）
```

关键设计：
- **速率限制策略**：GraphQL points 预算制；5000/h REST 配额下，25 仓库全量首扫应 < 30 分钟，增量 < 1 分钟
- **fork 归属规则**：默认排除纯 fork；有实质 commit 的 fork 标记 `contribution: true` 保留
- **Token 安全**：keyvault 存取；DB 中永不存 token

### 模块 B · Local Database（SQLite Schema v1）

```sql
-- 核心表（节选主干，全部带 created_at/updated_at）
repos(id PK, full_name UNIQUE, description, primary_language,
      stars, forks, is_fork, is_archived, visibility,      -- public/private
      created_at, pushed_at, topics JSON, my_role)          -- owner/contributor/viewer

commits(id PK, repo_id FK, sha, authored_at, message,
        additions, deletions, files_changed, is_my_commit)

issues(id PK, repo_id FK, number, title, state, labels JSON,
       opened_at, closed_at, is_pr BOOLEAN)

releases(id PK, repo_id FK, tag_name, name, published_at, notes)

my_stars(repo_id FK, starred_at, verdict)          -- verdict 继承 stargrave: dead/revisit/keep

repo_languages(repo_id FK, language, pct)

dependencies(repo_id FK, name, version, kind)      -- kind: runtime/dev

sync_state(entity, last_synced_at, cursor)         -- 增量游标
```

原则：
- **事实表与分析表分离**：`repos/commits/...` 只存 API 原始事实；Project Profile、Timeline 存入 `_analysis` 后缀表并带模型版本——换 LLM 重跑不污染原始数据
- **FTS5 全文索引**建在 commits.message / issues.title / repos.description 上，供 Analyst 检索

### 模块 C · Repository Intelligence（项目画像）

每个 repo 自动生成 Project Profile 卡片：

```
┌─ lumen ───────────────────────────────────────────┐
│ 定位: 个人 Agent Runtime（Go+React）               │
│ 技术栈: Go 71% · Vue 22% · gin/vue3              │ ← core RepoProfile
│ 规模/活跃度: 486 commits · 月均 40+ · 近 30 天活跃 │ ← DB 统计
│ 演化阶段: Demo→MCP接入→Runtime化（见 Timeline）    │ ← 模块 E
│ 优势: 模块化清晰; MCP 支持完整                     │ ← LLM(证据=profile+metrics)
│ 风险: 权限系统薄弱(test ratio 低+auth 模块小)      │ ← LLM(证据=metrics)
│ 建议: 增加 sandbox 层                             │ ← LLM
└───────────────────────────────────────────────────┘
```

铁律同 02 号 Skill：**LLM 输出的每条结论必须引用证据字段**（RepoProfile 字段名或 DB 查询），无证据的推断标 `[推测]`。

### 模块 D · Dashboards（双形态）

| 形态 | 技术 | 受众 |
|---|---|---|
| CLI 报告（先做） | 终端表格 + mermaid 导出 | 自己日常 |
| Web Dashboard（后做） | kb-ui 组件库 + Vite 静态页，读同一 SQLite | 自己 + 可部署到 yuer.dev/GitHub Pages 的脱敏公开版 |

内容分区：开发概览（累计项目/commit/语言/活跃周期）→ 技术画像（方向聚类）→ 项目矩阵（横轴成熟度纵轴活跃度的散点图，一眼看出该砍谁）

### 模块 E · Evolution Timeline ⭐（核心卖点，算法详案）

**输入**：单仓库的 commit 流 + core 的月度切片信号包（01 号 M3 提供）
**输出**：阶段化叙事 JSON

```
算法流水线:
1. 切片: commit 流按月切（稀疏仓库按季度合并）
2. 信号提取（每片向量）:
   - 结构信号: 新增/删除的顶层目录、新语言出现
   - 依赖信号: dependencies 表月度 diff（新增框架=强信号）
   - 主题信号: commit message 关键词频次 top-N（去 stopword）
   - 规模信号: loc 曲线斜率突变点
3. 边界检测: 相邻切片信号余弦相似度 < θ → 候选边界
   （θ 初始 0.6，对自己的 25 仓库人工校准）
4. LLM 命名: 把每段[起止时间+信号摘要]交给 LLM，
   要求输出: 阶段名(≤8字) + 一句话概括 + 判断依据引用
5. 全局校对: 第二次 LLM 调用检查阶段命名连贯性、合并碎段(<2个月)
6. 渲染: JSON → 横向时间轴（CLI 文本版 + Web 版 + mermaid gantt 导出）
```

成本估算：每仓库 2 次 LLM 调用 × 25 仓库 = 50 次，DeepSeek 计价下忽略不计。

**为什么这是卖点**：所有竞品停在"贡献热力图"，没人做"项目断代史"。它是截图传播力最强的功能，也是 04 知识图谱的时间维度地基。

### 模块 F · Developer Timeline + AI Analyst

- **Developer Timeline**：把所有仓库的 Evolution Timeline 投影到同一条个人时间轴上，叠加"语言占比迁移曲线"，产出年度叙事（"2025: Web 开发期 → 2026: AI 应用期 → Agent 系统期"）。这是 yuer.dev 公开页的主角。
- **AI Analyst**：对 DB 的 RAG 问答层。检索链路：问题 → FTS5 关键词召回 + 时间表达式解析（复用 dsh-logtimeline 的中文时间解析经验！）→ 组装上下文 → LLM 回答（强制引用数据行）。预设问法即原需求六问：主要研究什么/哪项值得继续/技术方向/哪些烂尾/短板/重复学习。
- **stargrave 并入点**：`my_stars.verdict` 字段 + "Star 资产体检"命令 `pgi stars clean`。

## 五、系统架构总图

```
GitHub API(GQL/REST)
      │ collector (Python, token via keyvault)
      ▼
SQLite(local.db) ◀── 增量同步(每日/手动)
      │
      ├──▶ stats 引擎(纯 SQL, 零成本)
      ├──▶ repo-intel-core(clone 本地仓库→RepoProfile)   [可选增强]
      ├──▶ Timeline 引擎(切片+边界+LLM×2)
      └──▶ Analyst(RAG: FTS5 + 时间解析 + LLM)
                 │
     provider 抽象层: DeepSeek │ Ollama │ OpenAI 兼容
                 │
      ┌──────────┴──────────┐
      ▼                     ▼
  CLI(pgi 命令组)      Web Dashboard(kb-ui/Vite, 读同一 db)
                              └──▶ 脱敏静态导出 → yuer.dev
```

CLI 命令面（先于 UI 冻结）：

```
pgi sync                    # 增量采集
pgi profile <repo>          # 单仓画像
pgi timeline <repo|--all>   # 演化时间轴
pgi dev-timeline            # 个人成长轨迹
pgi ask "<问题>"            # AI Analyst
pgi decide                  # 项目决策助手(继续/归档建议)
pgi stars clean             # stargrave 功能并入
pgi export --public         # 脱敏导出给 yuer.dev
```

## 六、分阶段路线

### M0 —— 自用数据底座（对应 Phase 1）
- [ ] collector 全量+增量、SQLite schema v1 落库
- [ ] `pgi sync` / `pgi stats`（纯统计报告，无 LLM）
- **验收**：Gate 2 黏性闸门（连续 2 周每周主动打开 ≥3 次）

### M1 —— 画像与面板
- [ ] Project Profile（接 core M2 + LLM 证据链输出）
- [ ] CLI 报告美化 + 项目矩阵图
- **验收**：G2 自评 ≥80%

### M2 —— 卖点打磨
- [ ] Evolution Timeline（含 θ 校准与 25 仓库实测）
- [ ] Developer Timeline 年度叙事
- **验收**：Gate 3 卖点闸门

### M3 —— 分析师与开源
- [ ] AI Analyst RAG + `pgi decide` 决策助手
- [ ] Web Dashboard（kb-ui）+ 脱敏导出 yuer.dev
- [ ] 开源打包（README GIF 用真实 Timeline 截图）
- **验收**：对外发布，收集 issue 进入迭代循环

## 七、验收指标汇总

| 维度 | 标准 |
|---|---|
| 数据完整性 | 25 仓库字段缺失率 < 2%（fork 排除后）；增量同步 ≤ 1 min |
| 画像质量 | G2 ≥ 80%；结论证据引用率 100% |
| Timeline 质量 | Gate 3 人工评判 ≥ 80% |
| 成本 | G5：全量分析 < ¥5（DeepSeek）；Ollama 路径 ¥0 |
| 隐私 | 私有仓库数据不出本机；导出默认剥离 private 内容 |

## 八、止损与收缩预案

- Gate 2 不过 → 收缩为"CLI + Timeline only"，放弃 Dashboard 线，把自己当唯一用户
- Timeline 效果差（Gate 3 不过）→ 检查是边界检测问题（调算法）还是命名质量问题（换 prompt/模型），两轮迭代仍差则 Timeline 降级为"手动标注辅助视图"，产品主线退守 Profile + Analyst
- API 成本超预期 → 强制 Ollama 默认档 + 分级调用（统计免费、叙事才花钱）

## 九、风险与对策

| 风险 | 对策 |
|---|---|
| GraphQL rate limit 卡死全量扫描 | points 预算调度器 + 断点续传（sync_state.cursor）+ 夜间批处理 |
| commit message 太烂导致主题信号失真 | 信号加权：结构/依赖信号权重 > 主题词；烂消息仓库自动降权 |
| 私有仓库心理顾虑 | 默认仅采公开；private 显式 opt-in；`pgi export --public` 白名单机制 |
| LLM 幻觉污染决策 | 全链路证据引用制 + `[推测]` 标注 + 分析结果存独立表可随时重算 |
| 与 02 Skill 抢精力 | 时序锁死：02 过 Gate 1 之前，本项目最多做到 M0 准备（schema 设计），不写采集代码 |

## 十、与其他项目的接口契约

| 对象 | 我们提供 | 我们需要 |
|---|---|---|
| 01 core | 无 | RepoProfile JSON（v1 schema）、M3 月度信号包 |
| 02 skill | 真实用户反馈、潜在导流 | 错峰（Gate 时序） |
| 04 data-os | GitHub 连接器的全部表结构与同步器（第一个连接器实现直接复用 collector） | 统一实体 ID 规范（见 04 §三） |
| yuer.dev | `pgi export --public` 静态 JSON | 展示组件（可用 kb-ui 快速搭） |
| lumen | local.db 只读访问 + `pgi ask` 作为 MCP tool | 无 |

---

## 十一、GraphQL 采集骨架（collector 实现参照）

```graphql
query($login: String!, $repoCursor: String, $commitCursor: String) {
  user(login: $login) {
    repositories(first: 50, after: $repoCursor, ownerAffiliations: [OWNER]) {
      pageInfo { hasNextPage endCursor }
      nodes {
        nameWithOwner  description  isFork  isArchived  visibility
        stargazerCount  pushedAt  createdAt
        repositoryTopics(first: 10) { nodes { topic { name } } }
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 100, after: $commitCursor) {
                pageInfo { hasNextPage endCursor }
                edges { node {
                  committedDate  messageHeadline  additions  deletions
                  changedFiles  author { user { login } }
                } }
              }
            }
          }
        }
      }
    }
  }
}
```

实现要点：仓库列表与 commit 历史两级游标独立管理，写入 `sync_state.cursor`；单次请求 points 预算 ~1+50×(1+history页数)，调度器按剩余限额决定本批发车数量。

## 十二、LLM 成本明细表（G5 的依据）

| 模块 | 调用次数 | 单次上下文估算 | 首次全量成本(DeepSeek 计价) |
|---|---|---|---|
| Project Profile ×25 | 25 | 输入 ~3k tok（RepoProfile+统计）输出 ~0.8k | ≈¥0.15 |
| Evolution Timeline ×25 | 50（每仓 2 次） | 输入 ~4k（切片信号包）输出 ~1k | ≈¥0.60 |
| Developer Timeline | 2 | 全局信号汇总 | ≈¥0.05 |
| Analyst | 按问计费 | 每问 ~5k | ≈¥0.02/问 |
| **合计** | — | — | **首次 < ¥1；日常月增量 < ¥3** |

冗余系数按 5× 预留仍满足 G5。Ollama 路径全部归零。

## 十三、`pgi decide` 决策评分模型

```
ValueScore(repo) =
    0.25 × 动量      近90天 commit 指数衰减和, 归一化
  + 0.20 × 独占度    是否承载独特方向(与路线关键词重合度反向去重后剩余价值)
  + 0.20 × 势头      Timeline 最近阶段的信号斜率(上行/平台/下行)
  + 0.20 × 战略契合  与 Developer Intelligence 路线主题词重合度
  + 0.15 × 完成度    metrics 完整性: testEvidence/入口清晰/docs 存在
输出:
  继续清单 top-N   每项附五维分数条 + 一句话理由(引用证据字段)
  归档候选 bottom-M 附条件: 连续 N 月动量<阈值 且 非战略契合 → 建议 archive 而非 delete
```

模型权重 v1 由人工拍定，跑通后用"自己是否认同结论"的复盘记录逐步校准——**先有可用序，再追准。**

## 十四、Web Dashboard 信息架构

```
Overview    KPI卡(项目数/总commit/语言top3/活跃年) + 贡献热力图 + 年度一句话
Projects    矩阵散点(x=成熟度 y=近90天动量) + 卡片流(Project Profile)
Timeline    个人主时间轴(Developer Timeline) + 点击下钻单仓 Evolution 视图
Stars       stargrave 三分类视图(dead/revisit/keep) + 清理建议队列
Ask         对话式 AI Analyst; 消息内嵌数据引用卡片(点击展开来源行)
导出        `pgi export --public` 预览 + 白名单管理入口
技术: kb-ui + Vite 静态站; 数据经只读 JSON API(本地小服务)或构建期烘焙
```

## 十五、脱敏导出规则细则

- **白名单字段制**：repos 仅导出 `name/description/language/stars/pushed_at/topics`；commits 仅导出月度聚合计数，**永不导出 message 原文**
- private 仓库的存在本身即敏感 → 默认从导出集中消失（连条目都不出现，而非打码）
- issues/PR 只导出公开仓库的计数统计
- 导出文件头部带 schema 版本 + 生成时间指纹，便于 yuer.dev 端校验新鲜度

---

> **AI 开发须知**：本项目由 AI 协同开发；VCR 式 fixture 先行、隐私规则进 AGENTS.md 硬约束等要点见 [06-AI协同开发手册.md](./06-AI协同开发手册.md) §八。
