# Changelog

本项目的全部重要变更记录于此文件。
格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本遵循 [SemVer](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- M3 全量交付：
  - GitMeta：单次 git log 解析首末提交/总数/贡献者/月度活跃 + branch/tag 计数；无 .git 保持 null 三态，命令失败降级 `GIT_META_UNAVAILABLE` warning；`scan --skip-git` 可关闭
  - 月度信号包 `repo-intel signals <path> [--months N] [--format summary|json]`：commits / contributors / new_dirs / deps_added（月末 blob 差集）/ top_terms——Evolution Timeline 的直接输入
  - Golden 快照基线：三 fixture 归一化 JSON 对比 + `scripts/update-golden.py` 再生流程
  - 框架内容信号跳过测试文件（消噪）
- 测试扩充至 85 项

### Added (M2)
- M2 全量交付：
  - 框架识别：`rules/frameworks.yaml` 36 条规则（前端/Web·Py·Node·Go/Java/AI-LLM/数据校验/ORM/测试/工具链），信号三路（声明依赖带版本 · 文件 glob 计数 · 代码内容子串），证据链必填
  - buildRun 推断：package.json scripts > Makefile > CI `run:` 三源交叉 + 锁文件判包管理器 + 生态默认值降置信度
  - 质量指标：复杂度热点启发式（long-file ≥400 行 / deep-nesting 缩进阈值）、测试证据（计数+占比+框架名）、TODO/FIXME 字节级计数
  - Schema add-only 扩展：ComplexityHotspot / TestEvidence / TodoStats，Metrics 新增三组字段
  - `scan` 摘要新增 frameworks top3 与 install/dev/test 命令行
- 测试扩充至 71 项；新增 m2 集成 fixture

- evocode 对齐审计首轮下沉：
  - frameworks.yaml 新增 database 类目 7 条 + Java 生态 MyBatis/Lombok（规则总数 49）
  - gitmeta 子进程 Windows CREATE_NO_WINDOW 弹窗抑制

- M4#1 认知复杂度启发式（移植 evocode complexity_scan）：hotspots 新增 cognitive-complexity 信号（max/fn/over），python·go·ts·js 四语言，阈值 12/20 分档
- M4#2 依赖能力扩展：
  - 新增 Maven 根 pom.xml 直接依赖解析（剥离 dependencyManagement/parent，版本继承 project 版本）
  - EOL 规则表下沉为 rules/deps_eol.yaml（13 条，maven/npm/pip 三生态），ExternalDep 新增 risk/riskReason 可选字段（add-only）
  - 数值版清洗：^~>= 前缀剥除用于规则匹配；git/file URL 不提取
- M4#3 函数级调用图（可选能力 [arch] extra，移植 evocode arch/ 五语言 tree-sitter 解析器）：
  - 节点=类/顶层函数/Go接收者类型聚合；边=调用名规范化匹配（跨文件）；Tarjan SCC 环检测 + 分层违规 + 出入度指标
  - Schema add-only 新增 call_graph 块；缺 tree-sitter 保持 null 三态；golden 归一化剥离该输出
- M4#4 numstat 全量演化统计：
epo-intel evolution <path> 新子命令——周趋势/topFiles/authors/热点规则（HIGH·MEDIUM 阈值原版移植）；空仓库与 git 故障显式区分
### Fixed
- CI `run:` 正则支持 `- run:` 列表项形式；pathlib 花括号通配不支持问题改双模式遍历

### Added (M1)
- 入口点检测 / Python·JS·Go 导入解析 / 模块级内部依赖图(weight)与 cohesion 三态 / 外部依赖清单 / CLI `graph` 子命令

## [0.1.0a0] - 2026-08-26

### Added
- M0 全量交付：
  - RepoProfile Schema v1.0-draft（pydantic 单一来源，camelCase 别名输出，M1+ 字段三态预留）
  - 语言识别三级信号：扩展名统计 → manifest 信号 → 无扩展名文件 shebang 指纹
  - 结构扫描：顶层目录表（含 guessed-entry / guessed-frontend 粗判）+ 根标记文件收集
  - 规模统计：totalLoc / totalFiles / largestFiles top5
  - 排除体系：内置默认清单剪枝 + `.repointelignore` 用户模式 + 超大文件降级告警
  - CLI：`repo-intel scan <path> [-o out.json] [--fail-fast] [--pretty]`
- yaml 表驱动规则（加语言/排除项不改代码）与包内 loader
- 测试集：26 用例全绿；混合语言 fixture 埋入 node_modules / min.js / ignore 陷阱

[0.1.0a0]: https://github.com/anyuer678/repo-intel-core/releases/tag/v0.1.0a0
