# 09 · evocode ↔ repo-intel-core 对齐审计

> 日期：2026-08-26 · 审计范围：`Desktop\烧token\analyzer\app\core\`（evocode 分析器）对照 repo-intel-core M0-M3
> 结论先行：**两仓互补大于重叠**。core 在契约化/测试/轻量形态上全面更优；evocode 有四件真金值得分批下沉，已下沉 2 件（本轮），其余列入 M4 候选。

---

## 一、逐模块对照表

| evocode 模块 | 对应 core 能力 | 判定 | 说明 |
|---|---|---|---|
| `langdetect.py` | detect/language.py 三级信号 | **core 优** | evocode 仅扩展名映射且把 md/json 计入语言；core 分离 data_ext、有 shebang 与 manifest 信号 |
| `filescanner.py` + `ignore.py` | scanner 剪枝遍历 + excludes.yaml | 同域 | 排除清单基本一致；core 多 `.repointelignore` 用户层 |
| `loc.py` | metrics 统计 | 同域 | — |
| `stackdetect.py` | rules/frameworks.yaml | **互有长短 → 已合并** | evocode 独有 DB_KEYWORDS（数据库识别）与 Java 生态条目——本轮下沉为 database 类目 7 条 + orm/tooling 2 条 |
| `dependency/depscan.py` | extdeps.py | 各缺一半 | evocode 支持 **pom.xml(Maven)** 且带 EOL 风险维度；core 支持 pyproject/requirements/go.mod。→ M4 合并口径 |
| `dependency/dep_eol_rules.py` | 无 | **evocode 独有，待下沉** | EOL 规则表结构清晰（ecosystem/name/version_prefix→risk），适合作为 core dependencies 表的 risk 扩展列 |
| `arch/`（5 语言 tree-sitter 解析器） | modules/dependencyGraph（模块级 import 边） | **evocode 强一档，M4 首位** | 函数级调用图、环检测、分层违规检测、线程安全 Parser 缓存——正是 core 推迟的"tree-sitter 增强"的现成实现 |
| `complexity_scan.py` | quality.py（long-file/deep-indent） | **evocode 强，待下沉** | 认知复杂度启发式（分支+嵌套惩罚），跨语言正则版零 AST 依赖——可直接并入 quality |
| `gitlog.py` | gitmeta/reader.py | **互有细节** | evocode 的两个防御点本轮已抄走：①Windows CREATE_NO_WINDOW 抑制弹窗 ②rev-parse 防"父仓库污染"思路（core 用 root/.git 存在性检查天然规避，但 worktree 场景待补） |
| `todomarker/security/style/duplication/bloated_scan` | quality.py 仅 TODO 密度 | evocode 独有 | 属于"体检站"12 类分析强项——建议保留在平台侧，按需逐个下沉 |
| `rag/ llm.py docgen explain prompts` | 无（原则性排除） | 定位外 | core 零 LLM 是硬约束；这些留在 evocode 平台侧正合适 |
| `sonar.py` | 无 | 定位外 | 可选外部组件集成 |

## 二、本轮已落地的下沉（2 项）

1. **frameworks.yaml 新增 9 条规则**：database 类目 7 条（SQLite/MySQL/PostgreSQL/Redis/MongoDB/MSSQL/H2）+ Java 生态 MyBatis/Lombok —— 规则总数 40→49
2. **gitmeta 子进程 Windows 弹窗抑制**：CREATE_NO_WINDOW（服务/pythonw 场景）

回归：88 测试全绿，ruff 零告警。

## 三、M4 候选清单（按价值排序，待排期）

| # | 候选 | 来源 | 工作量预估 | 价值 |
|---|---|---|---|---|
| 1 | 认知复杂度启发式并入 quality.py（替换 deep-indent 粗信号） | complexity_scan.py 正则版 | 小（单文件移植+测试） | 直接提升 Architect Skill 第 6 节报告质量 |
| 2 | pom.xml 依赖解析 + EOL 规则表进 extdeps | depscan + dep_eol_rules | 中 | 补 Java 生态短板；dependencies 表加 risk 列 |
| 3 | tree-sitter 函数级调用图（arch/ 五解析器移植） | arch/ | 大 | core 从模块级跃迁函数级；Architect Skill 质能齐升 |
| 4 | gitlog --numstat 全量演化统计（topFiles/authors/周趋势） | gitlog.py | 中 | 强化月度信号包，Timeline 增加"文件热点"维度 |

## 四、evocode 改造路径建议

```
阶段一（现在）：保持独立，仅输出格式对齐——evocode 前端可试点渲染 RepoProfile JSON
阶段二（core M4 后）：analyzer 的 langdetect/filescanner/stackdetect 替换为 pip 依赖 repo-intel-core
                    （arch/ 复杂度等平台专属能力保留）
阶段三（远期）：evocode = core 的旗舰 Web UI 消费者 + 持续健康档案；core CLI 服务 agent/轻场景
```

## 五、定位声明（写给人看的版本）

- **evocode**：给项目建"医院档案"——持续、全面、Web 界面、团队可用
- **repo-intel-core + Skills**：给开发者口袋里的"听诊器"——秒开、离线、agent 可调

同一套肌肉，两种用法。审计完毕，无重复建设焦虑。
