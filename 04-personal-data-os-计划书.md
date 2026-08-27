# 04 · Personal Data OS 计划书 —— 连接器架构愿景

> 性质：架构愿景 · **不是第三个项目，而是 03 号产品的自然延伸**
> 状态：本文档在 03 的 M0 跑通之前只维护不实现
> 终局宿主：lumen（Personal Agent Runtime）
> 核心命题：让 AI 理解你的全部数字资产，而不是一个知识库

---

## 一、定位澄清（本计划书最重要的一节）

**Data OS 不是要新建一个大项目。**

它是对 03 github-intelligence 的一次重新描述：

> 当"GitHub 连接器 + 本地数据库 + 分析层"这套架构，开始接纳第二个、第三个数据源时，
> 它就自然长成了 Data OS。

因此本计划书的性质是：

| 内容 | 性质 |
|---|---|
| 统一数据模型 | **现在就要定**的接口契约（03 建表时必须遵守，否则将来返工） |
| 连接器框架与规格 | 03 M0 之后逐步实现的设计蓝图 |
| 各连接器优先级 | 路线图（受总路线图 Gate 制约束） |
| 反模式清单 | 强约束，防止范围失控 |

### 与竞品的关系（为什么个人能做）

Rewind / Mem0 / Khoj 都在做"个人数据操作系统"，但它们是通用产品，必须服务所有人。
你的版本只需要服务一个人：**你自己**。这意味着：

- 不需要账号体系、不需要云端同步、不需要跨平台
- 连接器只为自己的真实工具链而写（Windows + 浏览器 + VSCode + GitHub）
- 数据质量标准是"对自己有用"，不是"对所有人正确"

这是个人项目对抗公司产品的唯一优势，也是必须死守的边界。

## 二、总体架构

```
 ┌─────────── Connectors（连接器层）────────────┐
 │  GitHub ✅(=03) │ Files │ Browser │ PDF │    │
 │  Notes │ Calendar │ Images │ ...按需扩展      │
 └──────────────────┬──────────────────────────┘
                    ▼  各自负责抽取为统一实体
 ┌──────────── Data Layer（数据层）─────────────┐
 │  SQLite: entities + relations + content     │
 │  (FTS5 关键词索引 + embeddings 语义索引)      │
 └──────────────────┬──────────────────────────┘
                    ▼
 ┌────────── Knowledge Graph（知识图谱视图）─────┐
 │  实体-关系查询 / 时间线 / 相似关联推荐         │
 └──────────────────┬──────────────────────────┘
                    ▼
 ┌──────────── Memory & Agent 层 ──────────────┐
 │  检索 API(MCP tools) → lumen 直接调用        │
 │  主动智能: 规则触发的观察报告                 │
 └────────────────────────────────────────────┘
```

## 三、统一数据模型（现在就定的契约）

### 实体类型

```jsonc
// 所有实体共用骨架：id, type, title, created_at, source_connector,
// source_uri(回溯原文件的指针), content_hash(去重), privacy(public/private)

Person      { name, aliases[], github_login?, email? }
Project     { name, status, repo_ids[], path? }          // 可对应 repo/本地目录/纯想法
Repository  { full_name, ... }                            // = 03 repos 表, 复用同一 id 规范
Commit      { sha, repo_id, authored_at, message }
File        { path, ext, size, mtime, project_id? }
Document    { kind: md/pdf/note, text_extract, summary? } // summary 由 LLM 生成,带模型版本
WebPage     { url, domain, title, visited_at?, bookmarked_at? }
Image       { path, caption? }                            // caption 参考 picren 经验
Task        { text, status, due?, source }                // 来源: todo-list/issue/calendar
Event       { kind: commit/release/meeting/study, at }
```

### 关系类型（封闭枚举，防止关系爆炸）

```
belongs_to     File/Document → Project
authored       Person → Commit/Document
references     Document → Entity(任意)
derived_from   Document → Document   (笔记抄自论文等)
co_occurs      Entity ↔ Entity       (同文档/同时段共现, 权重衰减)
precedes       Event → Event         (时间因果线索)
duplicate_of   Entity → Entity       (content_hash/embedding 相似)
```

### ID 与去重契约（03 必须现在遵守的两条）

1. **全局实体 ID 格式**：`{connector}:{type}:{native_id}`，如 `github:repo:anyuer678/lumen`、`file:doc:D%3A%2Fnotes%2Fagent.md`。03 建 SQLite 时主键即用此格式或保留映射列。
2. **content_hash 必填**：SHA256 of normalized content。没有它，未来文件连接器无法与 GitHub 内容对齐。

## 四、连接器规格与路线（一次只开一个）

每个连接器的最小形态定义（MVP 标准）：**能把自己领域的对象变成统一实体入库，且有一条 CLI 查询命令证明可用。**

| 优先级 | 连接器 | 数据源 | MVP 抽取物 | 现有经验复用 |
|---|---|---|---|---|
| P0 ✅ | github | GitHub API | repos/commits/issues/releases/star | 就是 03 本体 |
| P1 | files-md | 本地 Markdown/PDF 目录 | 文档实体+文本提取+FTS | evocode 文档解析 |
| P2 | browser | 浏览器历史+书签(JSON 导入) | WebPage 实体+域名统计 | — |
| P3 | images | 图片目录 | Image+caption | picren 直接迁移 |
| P4 | calendar/todo | todo-list 导出/日历 ICS | Task/Event | todo-list 数据 |
| P5 | notes-app | 笔记软件导出 | Document | — |

**开闸条件**（继承总路线图 Phase 3 规则）：上一个连接器达到"自用黏性"——连续 2 周、每周 ≥3 次主动使用其查询命令——才允许开下一个。P1 未达标则整个 Data OS 冻结在 GitHub Intelligence 形态，这同样是合法结局。

## 五、三层搜索设计

| 层 | 技术 | 回答的问题 | 成本 |
|---|---|---|---|
| L1 关键词 | SQLite FTS5 | "SQLite 出现过在哪" | 零 |
| L2 语义 | embedding 列 + 余弦检索（Ollama 本地模型 or DeepSeek embedding） | "以前研究数据库优化的资料" | 低（本地推理） |
| L3 关系 | 图遍历 SQL（relations 表递归 CTE） | "和 OpenClaw 相关的所有资料" | 零 |

入口统一为一条命令：`pdo find "<query>" --mode kw|sem|rel|auto`。auto 模式先用 L1，结果不足自动升级 L2。

**明确不做**：独立向量数据库（Milvus/Qdrant）。embedding 存 BLOB 列 + numpy 暴力余弦在十万级实体内完全够用。

## 六、主动智能（规则先行，不做自主 Agent）

原需求中的"AI 主动发现你连续研究 Agent，建议合并方向"，落地为**观察报告生成器**：

```
每周日(或手动)触发:
  规则库(yaml, 可增删):
    R1 连续性: 同一主题词连续 N 天出现在 ≥2 个连接器 → 提示"方向聚焦"
    R2 重复学习: 高相似 Document 对(embedding>0.95)跨时段出现 → 提示"重复研究"
    R3 孤岛提醒: Project 无任何 references 入边 → 提示"被遗忘的资产"
    R4 冲突检测: 同一问题两个 Document 结论矛盾(LLM 比对) → 提示"决策未收敛"
  输出: OBSERVATIONS.md + `pdo observe` 查看
```

红线：**只生成报告，绝不自主执行动作**（不改文件、不发消息）。执行能力属于 lumen，且必须由人确认。

## 七、Memory 接口（给 lumen 的契约）

Data OS 对 lumen 的最终交付形态是一组 MCP tools：

```
memory_search(query, mode)      # 三层搜索
memory_timeline(entity, range)  # 实体时间线(复用 03 Timeline 引擎)
memory_related(entity_id)       # 图邻居
memory_observe()                # 最新观察报告
memory_get(entity_id)           # 实体详情+原文回溯(source_uri)
```

lumen 侧改造需求（届时立项）：MCP server 注册这五个工具 + 权限门（参考 voiceconsole 的安全门设计）决定哪些工具可被自动调用。

## 八、分阶段路线

| 阶段 | 内容 | 开闸条件 |
|---|---|---|
| DS-0 | 只定契约：ID 格式 + content_hash 写进 03 的 schema | 现在 |
| DS-1 | 连接器框架抽象（connector 接口 + 注册机制），github 连接器重构接入 | 03 过 Gate 2 |
| DS-2 | P1 files-md 连接器 + L1/L2 搜索 | DS-1 稳定 |
| DS-3 | 观察报告生成器（R1/R2 先行） | P2 达黏性 |
| DS-4 | browser/images/calendar 按 P2-P5 逐个开闸 | 各自前一闸通过 |
| DS-5 | MCP tools 交付 lumen，进入 Agent Runtime 合流 | ≥3 个连接器达黏性 |

## 九、反模式清单（出现任何一条即停下复盘）

1. ❌ 为"未来可能的数据源"预写代码（连接器只在开闸时写）
2. ❌ 上独立向量数据库 / 图数据库 / 消息队列
3. ❌ 自建云同步（备份用 git 或网盘即可）
4. ❌ 追求"全覆盖我所有数字足迹"——只接自己真的会回头查的东西
5. ❌ 让 Agent 自动执行变更
6. ❌ 把 Data OS 做成开源产品再抽象一层——它是私人器官，开源的是 01/02/03

## 十、长期验收愿景（终局画面）

> 对着电脑说（经 lumen / voiceconsole）：
> "我去年暑假做了什么？"
>
> 它回答：7 月学 Linux（files-md: 学习笔记 ×14）、8 月开发 Agent（github: lumen 首批 commit）、9 月做知识库（browser: 相关检索 47 次）——并附上每条结论的可回溯来源。

这一幕发生之时，整条 Developer Intelligence 路线宣告闭环。

## 十一、风险与对策

| 风险 | 对策 |
|---|---|
| 范围失控（本项目最大风险） | 本文 §九反模式清单 + 总路线图一次一连接器铁律 |
| embedding 本地模型效果差 | 允许 DeepSeek embedding 云端档；L1/L3 保底，L2 只是增强 |
| 隐私事故（个人数据聚合后极敏感） | 全程 local-first；DB 文件整库加密选项；永不 export 明文聚合包 |
| 03 尚未成功就开始幻想 DS | DS-0 只改两行 schema；DS-1 之前无任何代码——用制度锁住冲动 |

---

## 十二、Connector 协议代码契约（DS-1 冻结）

```python
from typing import Protocol, Iterator
from dataclasses import dataclass

@dataclass
class Cursor:
    connector: str
    position: str          # 不透明游标: 文件 mtime/GitHub endCursor/浏览器历史 offset

class EntitySink(Protocol):
    def upsert(self, entity: dict) -> None: ...        # 必含 id/title/type/source_uri/content_hash
    def relate(self, a_id: str, rel: str, b_id: str,
               props: dict | None = None) -> None: ...
    def checkpoint(self, cursor: Cursor) -> None: ...

class Connector(Protocol):
    name: str                                          # "github" / "files-md" / ...
    entity_types: tuple[str, ...]                      # 声明能产出的实体类型(§三枚举的子集)
    def full_sync(self, sink: EntitySink) -> str: ...      # 返回 SyncReport 摘要
    def incremental(self, sink: EntitySink, since: Cursor) -> str: ...
    def watch(self) -> Iterator[dict]: ...             # 可选: 实时变更流; 默认 NotImplemented
```

约束：连接器**只写不读**（查询归 Data Layer）；实体必须自带 `source_uri` 保证可回溯；任何解析失败降级为 warning 记录，不允许中断整批同步。

## 十三、P1 files-md 连接器设计（第一个新连接器，DS-2 蓝图）

| 维度 | 设计 |
|---|---|
| 范围边界 | **目录白名单制**：只索引用户显式声明的根目录列表（如笔记库、学习目录），白名单即隐私边界 |
| Markdown 解析 | front-matter（tags/status/date）→ 实体 props；`[[wiki链接]]` 与标准链接 → `references` 关系 |
| PDF 解析 | pypdf 抽文本（可选依赖），失败则仅建壳实体记 warning |
| 实体产出 | Document(kind=md/pdf) + File + belongs_to(Project 若路径命中已知项目目录) |
| 去重 | content_hash 主防线；文件移动 = source_uri 更新而非新建 |
| 查询证明 | `pdo find "<关键词>" --mode kw` 能命中笔记并回溯打开原文件 |

## 十四、Embedding 选型对比（L2 层）

| 方案 | 质量(中文) | 成本 | 依赖 | 结论 |
|---|---|---|---|---|
| bge-small-zh 本地 | 好 | ¥0 | Python 包 ~100MB | **默认** ✅ |
| Ollama nomic-embed-text | 中(中文一般) | ¥0 | 需常驻 Ollama | 备选 |
| DeepSeek/OpenAI embedding API | 好 | 低但持续 | 网络+数据出境 | 敏感文档禁用档 |
| 接口抽象 | — | — | `embed(texts) -> vecs` 单函数 | 三实现可热切 |

十万级实体 × 512 维 ≈ 200MB BLOB 存储；numpy 批量余弦单次查询 < 50ms——**不需要向量数据库**（呼应 §九反模式 2）。

## 十五、隐私威胁建模

| 攻击面 | 后果 | 缓解 |
|---|---|---|
| 笔记本丢失/被借走 | 全部数字人格泄露 | 磁盘 BitLocker + DB 可选 SQLCipher 整库加密 |
| 恶意依赖投毒 | 本地数据外传 | 锁文件 + `pip-audit` 进 CI；连接器进程禁网(除声明需要者) |
| 云端 LLM 调用带出敏感内容 | 笔记原文出境 | 实体带 `privacy: high` 标记(files-md 白名单外自动标记)；云 provider 调用层强制过滤该级实体 |
| 导出物拼接攻击 | 公开导出+其他公开信息反推身份 | §十五(03 文档)白名单字段制 + 不导出时间精确到日以下 |

## 十六、终局合流架构（lumen ⇄ Data OS）

```
        [语音] voiceconsole ──┐
        [键盘] 用户输入 ──────┤
                              ▼
                     ┌─────────────────┐
                     │   lumen runtime  │  ← 常驻 · 权限门 · 工具执行
                     └───┬─────────┬───┘
                    MCP tools│         │动作执行(经人确认)
                             ▼         ▼
              ┌───────────────────┐  [电脑/文件/应用]
              │ memory.* (5 tools) │
              └─────────┬─────────┘
                        ▼
              ┌───────────────────┐
              │  Data OS 数据层    │
              │ SQLite+FTS5+emb   │
              └───┬───────────┬──┘
        github✅  │           │ files-md → browser → ...
              [GitHub API]  [本地目录]
```

分界原则：**lumen 管"做"，Data OS 管"知道"。** Data OS 永远不直接执行动作；lumen 的每次重要动作前可查记忆，事后把结果作为 Event 写回（经人确认的才入正式关系）。

---

> **AI 开发须知**：本项目由 AI 协同开发；协议冻结后的连接器复制式开发、EntitySink 内存 fake 等要点见 [06-AI协同开发手册.md](./06-AI协同开发手册.md) §八。
