# 01 · repo-intel-core 计划书 —— 跨语言仓库解析引擎

> 性质：基础设施 · 路线的真资产
> 上游：无（依赖链最底端）
> 下游消费者：02 onboarding-skill、03 github-intelligence、evocode（转型后）
> 能力母体：evocode（从中抽取核心）

---

## 一、一句话定位

**把任意代码仓库变成一份结构化、可版本化、可离线生成的 RepoProfile JSON——不调 LLM、不起服务、一条命令完成。**

## 二、背景与问题

### 为什么要做

1. **重复造轮子困局**：分析类工具每做一个都要重写一遍"扫目录→认语言→找入口→分模块"。你已经有 evocode（扫描+体检）、stargrave（扫 star 仓库）、upgrademate（跨语言升级）三个项目碰过同一类问题。
2. **evocode 绑死在平台上**：它的分析能力藏在 Spring Boot + FastAPI 的平台流程里，无法被 Skill 或 CLI 单独复用。
3. **上层三个项目的共同前提**：02 需要它生成入门文档的事实依据；03 需要它给每个仓库建 Project Profile；未来 lumen 需要"看懂一个陌生目录"的能力。

### 问题定义

> 输入：本地仓库路径（或 GitHub URL，由调用方负责 clone）
> 输出：符合版本化 Schema 的 RepoProfile JSON
> 约束：纯静态启发式 + tree-sitter AST，零网络请求，零 LLM 调用

## 三、目标与非目标

### 目标

| # | 目标 | 可验证标准 |
|---|---|---|
| G1 | 主流语言全覆盖识别 | Python / JS / TS / Go / Java / Vue / HTML / CSS 准确识别；未知语言给出"unknown + 特征指纹"而不是崩溃 |
| G2 | 入口点与构建命令推断 | 对自己 25 个仓库，install/dev/test 命令推断正确率 ≥ 80% |
| G3 | 模块划分与内部依赖图 | 中型仓库（≤500 文件）输出人工可认可的模块划分 |
| G4 | 单机快速 | 25 个仓库全量扫描 < 10 分钟，单仓库典型 < 30s |
| G5 | Schema 版本化稳定 | v1.0 发布后只增不改；破坏性变更升 major 并带迁移说明 |

### 非目标（出现即拒绝）

- ❌ 不做 UI / 报告渲染（消费者的活）
- ❌ 不做任何 LLM 调用（"模块职责是什么"这种语义判断交给上层）
- ❌ 不做代码修改 / 重构执行（upgrademate 的领域）
- ❌ 不做 GitHub API 采集（03 的领域）
- ❌ 不追求 IDE 级精度（要的是"80 分的全面"，不是"100 分的单语言"）

## 四、核心产出：RepoProfile 数据模型

### Schema 全貌（v1.0 草案）

```jsonc
{
  "schemaVersion": "1.0",
  "generatedAt": "2026-08-26T12:00:00Z",
  "tool": { "name": "repo-intel-core", "version": "0.3.0" },

  "repo": {
    "path": "/path/to/repo",
    "name": "lumen",
    "vcs": { "type": "git", "headBranch": "main", "isDirty": false }
  },

  // ---- M0 交付 ----
  "languages": [
    { "name": "go", "pct": 71.2, "files": 84, "loc": 12300 },
    { "name": "typescript", "pct": 22.1, "files": 45, "loc": 3800 },
    { "name": "css", "pct": 6.7, "files": 12, "loc": 1150 }
  ],
  "structure": {
    "topLevelDirs": [
      { "path": "cmd", "fileCount": 6, "role": "guessed-entry" },
      { "path": "internal", "fileCount": 40, "role": null },
      { "path": "web", "fileCount": 57, "role": "guessed-frontend" }
    ],
    "configFiles": ["go.mod", "package.json", ".github/workflows/ci.yml"]
  },

  // ---- M1 交付 ----
  "entryPoints": [
    { "file": "cmd/lumen/main.go", "type": "server",
      "confidence": 0.9, "evidence": ["package main + http.ListenAndServe"] },
    { "file": "web/src/main.ts", "type": "gui",
      "confidence": 0.85, "evidence": ["createApp(", "vite.config.ts"] }
  ],
  "modules": [
    { "name": "auth", "rootPath": "internal/auth", "files": 8,
      "responsibility": null,        // 留空：语义判断归 LLM 层
      "cohesionScore": 0.82 },       // 启发式内聚度
    { "name": "mcp-server", "rootPath": "internal/mcp", "files": 14, "...": "..." }
  ],
  "dependencyGraph": {
    "internal": [                     // 模块级有向边
      { "from": "api", "to": "auth" },
      { "from": "auth", "to": "storage" }
    ],
    "external": [
      { "name": "gin-gonic/gin", "version": "v1.10", "kind": "runtime", "usageFiles": 12 },
      { "name": "vue", "version": "3.4", "kind": "runtime", "usageFiles": 40 }
    ]
  },

  // ---- M2 交付 ----
  "frameworks": [
    { "name": "vue", "version": "3.4.x", "category": "frontend-framework",
      "confidence": 0.95, "evidence": ["package.json dependency", "*.vue files"] },
    { "name": "gin", "version": "v1.10", "category": "web-framework",
      "confidence": 0.9, "evidence": ["go.mod", "import scan"] }
  ],
  "buildRun": {
    "buildSystem": ["go-modules", "pnpm"],
    "installCmd": ["go mod download", "pnpm install"],
    "devCmd": ["go run ./cmd/lumen", "pnpm dev"],
    "testCmd": ["go test ./...", "pnpm test"],
    "confidence": 0.8,
    "evidence": ["Makefile", "package.json scripts", ".github/workflows/*.yml"]
  },
  "metrics": {
    "totalLoc": 17250, "totalFiles": 141,
    "largestFiles": [{ "path": "internal/api/router.go", "loc": 870 }],
    "complexityHotspots": [{ "path": "internal/agent/scheduler.go", "signal": "max-nesting=7,long-func-count=4" }],
    "testEvidence": { "testFileCount": 22, "ratioToSource": 0.31,
                      "frameworks": ["go-test", "vitest"] },
    "todos": { "todoCount": 34, "fixmeCount": 7 }   // 技术债线索
  },

  // ---- M3 交付（可选模块，git 不存在时整体缺省）----
  "git": {
    "firstCommitAt": "2025-11-02", "lastCommitAt": "2026-08-22",
    "commitCount": 486, "contributorCount": 1,
    "activityByMonth": { "2025-11": 42, "2025-12": 61, "...": "..." },
    "branchCount": 3, "tagCount": 2
  },

  "warnings": [
    { "code": "MIXED_MONOREPO", "detail": "检测到 go.mod 与 package.json 共存，按 monorepo 处理" },
    { "code": "PARSE_SKIPPED", "detail": "vendor/ 目录已跳过（382 文件）" }
  ]
}
```

### 设计原则

1. **事实与解释分离**：`structure` / `dependencyGraph` 是事实；`modules[].responsibility` 留空等 LLM 填；每个推断字段都带 `confidence` + `evidence`。
2. **永远部分成功**：任何单块解析失败 → 写入 `warnings`，其余照常输出。引擎对垃圾输入的唯一合法反应是降级，不是报错退出。
3. **字段三态**：`null`（没测）/ 数值（测到了）/ 缺省（该模块未启用）。消费方必须能区分这三种。

## 五、技术方案

### 语言选型：Python（已定，理由如下）

| 候选 | 优势 | 劣势 | 结论 |
|---|---|---|---|
| **Python** ✅ | tree-sitter 绑定最成熟；evocode 已有 FastAPI 分析栈可搬；stargrave/logtimeline 同栈经验；数据处生态（jsonschema 等）齐全 | 打包分发略麻烦（用 `uv`/`pipx` 解决）；性能一般但够用（G4 只要求分钟级） | **选定** |
| TypeScript | 若未来 Skill 内嵌逻辑可同构 | tree-sitter 各语言 grammar 在 Node 下配置繁琐；与 evocode 存量代码异构 | 否 |
| Go | 与 lumen 同栈 | AST 生态弱（tree-sitter 有绑定但 grammar 管理差）；重写 evocode 存量逻辑成本高 | 否 |

### 关键技术决策

| 决策点 | 选择 | 理由 |
|---|---|---|
| 解析深度 | **tree-sitter 只用于关键文件**（入口候选、import 提取），其余走正则/启发式 | 全量 AST 太慢且没必要；80/20 原则 |
| 语言识别 | 三级信号融合：扩展名统计 → manifest 文件（package.json/go.mod/pom.xml…）→ shebang/内容指纹 | 单一信号都会被 monorepo 骗 |
| 模块划分算法 | 自顶向下：顶层目录聚类（按 import 连通性合并散目录）→ 小仓库回退为"平铺文件列表" | 图聚类算法（社区发现）放 M3 之后再说，YAGNI |
| 排除规则 | 内置默认集（node_modules/vendor/dist/.git/target/__pycache__…）+ `.gitignore` 尊重 + `.repointelignore` 用户自定义 | 必须在第一版就有，否则 vendor 会毁掉一切 |
| CLI 形态 | `repo-intel scan <path> [-o profile.json] [--with-git] [--fail-fast]`；库形态 `from repo_intel import scan_repo` | 库和 CLI 同包双出口，Skill 用库、人用 CLI |
| 测试基线 | **自己的 25 个仓库就是测试集**：CI 里 clone 自己跑快照对比（golden file） | 真实、免费、永不过期 |

### 项目结构草案

```
repo-intel-core/
├── src/repo_intel/
│   ├── schema/          # pydantic 模型 = JSON Schema 单一来源
│   ├── detect/          # 语言/框架/入口/构建命令
│   ├── graph/           # 模块划分 + 依赖图
│   ├── gitmeta/         # M3: git 元数据
│   ├── rules/           # 规则表（yaml）：框架特征/排除清单/入口模式 —— 表驱动，加语言不改代码
│   └── cli.py
├── tests/golden/        # 25 个自有仓库的快照基线
└── docs/schema-v1.md
```

## 六、与现有项目的关系

```
evocode ──抽取──▶ repo-intel-core ──作为库──▶ 02 onboarding-skill
   ▲                    │
   └──转型为 Web UI ◀───┘            repo-intel-core ──作为库──▶ 03 github-intelligence
                                     （Project Profile + Evolution Timeline 的原始信号）
```

- **从 evocode 抽什么**：语言识别规则表、目录角色启发式、技术债信号（TODO 扫描、超大文件）。抽完 evocode 改为 pip 依赖 core。
- **stargrave 不依赖 core**（它扫的是 star 列表不是代码），但在 03 内会与 core 产物汇合。

## 七、分阶段路线（M0 → M3）

### M0 —— 能看见（最小可用）
- [ ] 项目骨架 + pydantic Schema 定稿 v1.0-draft
- [ ] 语言识别（三级信号）+ 结构扫描 + 规模统计
- [ ] 默认排除规则 + `.repointelignore`
- [ ] CLI `scan` 命令 + JSON 输出
- **验收**：25 个自有仓库 100% 出 profile、零崩溃；语言占比与 GitHub 语言条基本一致

### M1 —— 能理解结构
- [ ] 入口点识别（main/bin/scripts/路由注册等模式表）
- [ ] import/require 解析 → 模块划分 + 内部依赖图
- [ ] 外部依赖清单（含 kind: runtime/dev）
- **验收**：对自己任选 5 仓库，模块划分经本人确认"说得过去"；依赖图能画出 mermaid

### M2 —— 能读懂工程
- [ ] 框架识别规则表（前端/AI/Web/测试框架 ≥ 30 条常见规则起步）
- [ ] buildRun 推断（manifest + Makefile + CI yml 三源交叉）
- [ ] metrics：复杂度热点 / 测试证据 / TODO 密度
- **验收**：G2 达标（构建命令 ≥80% 正确）；02 号 Skill 可以完全基于 core 输出写文档

### M3 —— 能看见时间（可选模块）
- [ ] gitmeta：提交时间线 / 月度活跃 / 贡献者 / tag
- [ ] 为 03 的 Evolution Timeline 提供"月度切片信号包"（每月新增目录、依赖变更、主题词频）
- **验收**：03 号项目 M2 开工时此模块就绪

## 八、验收指标汇总与止损线

| 指标 | 标准 |
|---|---|
| 稳定性 | 25 仓库零崩溃（warning 允许，error 不允许） |
| 语言识别 | 与 GitHub 语言条对比 top3 一致率 ≥ 90% |
| 构建命令 | 人工判定 ≥ 80% 正确 |
| 性能 | 全量 25 仓库 < 10 min |
| 成本 | ¥0（全程无 LLM、无网络） |

**止损线：本项目不设止损。** 它是基础设施，最坏情况也是 evocode 重构的技术债偿还；即使 02/03 全部转向，core 本身仍是净收益。

## 九、风险与对策

| 风险 | 对策 |
|---|---|
| 语言/框架规则表无限膨胀 | 规则全部外置 yaml 表驱动；未识别语言输出指纹让用户提 issue，而不是自己追着补 |
| tree-sitter grammar 安装在某些环境失败 | AST 仅作增强路径；grammar 加载失败自动降级为纯正则模式并记 warning |
| monorepo 把模块划分搞乱 | 显式 monorepo 检测（多 manifest 共存）→ 按 package/workspace 切分为多个子 profile |
| 过早优化图算法 | M1 只做连通性聚类；社区发现算法推迟到真实需求出现之后 |

---

## 附录 A · Manifest 识别表（M0 内置）

| 语言/生态 | manifest 文件 | 关键判定信号 |
|---|---|---|
| Go | `go.mod` | module 声明；`go.work` = monorepo 标志 |
| Python | `pyproject.toml` > `setup.py` > `requirements.txt`（优先级递减） | PEP 621 project 表 |
| Node.js | `package.json` + 锁文件判包管理器：`pnpm-lock.yaml` / `yarn.lock` / `package-lock.json` | `workspaces` 或 `pnpm-workspace.yaml` / `lerna.json` / `turbo.json` = monorepo |
| Rust | `Cargo.toml` | workspace 表 = monorepo |
| Java | `pom.xml` / `build.gradle(.kts)` | `<modules>` / settings.gradle = monorepo |
| Vue 项目 | `package.json` 且 dependencies 含 `vue@3` | 配合 `*.vue` 文件计数确认 |
| 纯前端 | 仅 html/css/js 无 manifest | 按入口 index.html 识别 |

## 附录 B · 入口点模式库（M1 内置，yaml 表驱动）

```yaml
# rules/entrypoints.yaml（节选示意）
- id: node-bin
  type: cli
  language: javascript,typescript
  evidence: "package.json 的 bin 字段"
  confidence: 0.9
- id: python-main
  type: cli
  language: python
  evidence: '文件含 if __name__ == "__main__"'
  confidence: 0.7
- id: go-http-server
  type: server
  language: go
  evidence: ["http.ListenAndServe", "gin.New()", "echo.New()"]
  confidence: 0.85
- id: fastapi-app
  type: server
  language: python
  evidence: ["FastAPI(", "uvicorn.run"]
  confidence: 0.9
- id: vue-createapp
  type: gui
  language: typescript,javascript
  evidence: ["createApp(", "vite.config."]
  confidence: 0.85
- id: electron-main
  type: gui
  language: javascript,typescript
  evidence: ["electron", "BrowserWindow"]
  confidence: 0.9
```

规则冲突时取 confidence 最高者并列输出全部候选——**宁可多报候选，不可漏报入口**。

## 附录 C · 默认排除清单（M0 内置）

```
目录: node_modules/ vendor/ dist/ build/ target/ out/ .git/ .venv/ venv/
      __pycache__/ coverage/ .next/ .nuxt/ .cache/ .idea/ .vscode/
文件: *.min.js *.min.css *.map *.lock package-lock.json pnpm-lock.yaml
      poetry.lock *.pb.go *_gen.go *.generated.*
上限: 单文件 > 2MB 只计 loc 不做内容解析；单仓库文件数 > 20000 强制要求显式 include 白名单
```

## 附录 D · 性能预算表（单仓库 < 30s 分解）

| 阶段 | 预算 | 说明 |
|---|---|---|
| 目录遍历 + hash | ≤ 3s | os.walk 单遍完成，hash 用 blake3 |
| 语言统计 | ≤ 2s | 与遍历同趟流水线化 |
| AST 解析 | ≤ 15s | **只解析关键文件前 50 个**（入口候选 + 最大文件） |
| import 提取 | ≤ 8s | 正则优先；仅 import 语句模糊匹配即可满足模块划分精度 |
| Schema 组装输出 | ≤ 1s | pydantic 校验一次 |
| 余量 | ~1s | 应对慢磁盘 |

超预算即触发降级：跳过 AST、只出正则级结果并记 warning。

## 附录 E · 规则表示例（frameworks 片段）

```yaml
# rules/frameworks.yaml —— 一条完整规则的形态
- id: vue3
  name: Vue
  category: frontend-framework
  any_of:                       # 满足任一证据即命中
    - file: package.json
      jsonpath: "$.dependencies.vue"
      version_from: value       # 版本号直接取依赖值
    - glob: "**/*.vue"
      min_count: 3              # 且至少存在 3 个 .vue 文件才算强信号
  confidence_base: 0.9
  notes: "Vue2 判定: dependencies.vue 主版本为 2"
```

## 附录 F · Golden Test 流程

1. `tests/golden/<repo-name>.json` 为基线快照；来源固定为本账号 25 个仓库的 pinned commit
2. CI 步骤：clone（浅克隆 + 缓存）→ 扫描 → 过滤不稳定字段（`generatedAt`/`tool.version`/`git.lastCommitAt` 类时间戳用 jq 等价物剔除）→ diff 基线
3. 有意变更输出时：跑 `scripts/update-golden.py` → **人工逐仓 review diff** → 基线与 schema 同一个 PR 提交
4. 新增自有仓库 = 自动扩充测试集；外部贡献者可提交自己仓库的匿名化指纹作为补充样本

---

> **AI 开发须知**：本项目由 AI 协同开发，任务卡拆解、AGENTS.md 实例化与验证闭环要求见 [06-AI协同开发手册.md](./06-AI协同开发手册.md)，项目特定要点见其 §八。
