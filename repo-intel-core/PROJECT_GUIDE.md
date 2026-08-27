# PROJECT_GUIDE — repo-intel-core

> 由 repo-onboarding 生成于 2026-08-26 · 基于 完整(full) 模式扫描

## 1. 这个项目是什么

把任意代码仓库变成一份结构化、可版本化、可离线生成的 **RepoProfile JSON**。
纯静态启发式引擎：零 LLM 调用、零网络请求，一条命令完成；是 Developer Intelligence 路线的地基资产。

据扫描结果推断：本项目为上层工具（onboarding-skill / github-intelligence）提供"看懂仓库"的能力，自身刻意不含任何 AI 逻辑。

<!-- 来源: README.md 提取 + structure.configFiles -->

## 2. 技术栈速览

| 语言 | 占比 | 文件数 | 行数 |
|---|---|---|---|
| python | 100.0% | 42 | 3110 |

框架：Pydantic @>=2.7（数据校验，Schema 单一来源）

<!-- 来源: languages / frameworks -->

## 3. 五分钟跑起来

```bash
# 安装（开发模式，含测试工具）
pip install -e ".[dev]"
# 运行测试
pytest
```

⚠️ devCmd 未检测到显式脚本——本项目无长驻服务，日常入口是 CLI：

```bash
repo-intel scan <仓库路径> --pretty
```

<!-- 来源: buildRun.installCmd/testCmd + entryPoints(scripts/update-golden.py, src/repo_intel/cli.py) + README 安装节 -->

## 4. 目录地图

| 目录 | 职责猜测 | 关键文件 |
|---|---|---|
| src/ | 引擎主包 repo_intel（31 文件） | scanner.py / cli.py / schema/profiles.py |
| tests/ | 测试与 fixture 构建（24 文件） | conftest.py / test_golden.py |
| docs/ | 任务卡与决策日志（5 文件） | tasks/M0~M3.md / decisions.md |
| scripts/ | 工具脚本（1 文件） | update-golden.py |
| (root) | 配置与文档（7 文件） | pyproject.toml / CHANGELOG.md |

<!-- 来源: structure.topLevelDirs + 据扫描结果推断（关键文件取自 metrics.largestFiles 与 entryPoints） -->

## 5. 核心流程走读

1. **CLI 入口**：`src/repo_intel/cli.py`（含 `__main__`）解析 `scan / graph / signals` 三个子命令
2. **编排**：`src/repo_intel/scanner.py` 单趟 os.walk 剪枝排除 → 语言三级信号 → 结构与规模统计
3. **增强层**：detect/ 下各模块依次填充入口点、模块依赖图、框架、buildRun、质量指标
4. **时间线**：gitmeta/ 输出 GitMeta 与月度信号包（供上游 Evolution Timeline 使用）
5. **防回归**：tests/golden/ 快照对比任何输出格式变化

<!-- 来源: entryPoints + 据阅读 cli.py/scanner.py 推断 -->

## 6. 改动从哪进

| 想改什么 | 动哪里 |
|---|---|
| 加语言/框架/入口识别规则 | src/repo_intel/rules/*.yaml（表驱动，不改代码） |
| 新增检测能力 | src/repo_intel/detect/ 新模块 + scanner.py 接线 |
| 输出字段 | src/repo_intel/schema/profiles.py —— **add-only**，已有字段禁改 |
| 新 CLI 子命令 | src/repo_intel/cli.py |
| 输出格式变更 | 同步再生 tests/golden/ 并人工 review diff |

<!-- 来源: AGENTS.md 硬约束 + 目录地图，据扫描结果推断 -->

## 7. 已知风险与注意点

- 复杂度热点（deep-nesting=24）：`src/repo_intel/detect/entrypoints.py` · `frameworks.py` · `scanner.py`
- TODO/FIXME 存量：7 / 3
- 测试证据：19 个测试文件（占代码文件 45%）但未声明测试框架依赖——环境需预装 pytest
- 最大文件：`tests/conftest.py`（316 行），fixture 构建集中于此
- 硬约束提醒：schema 字段 add-only；src/ 内禁止网络与 LLM 调用

<!-- 来源: metrics.complexityHotspots/todos/testEvidence/largestFiles + AGENTS.md -->

## 附录 A · 数据来源说明

- 扫描模式：**full**（已安装 repo-intel-core，全字段输出）
- 第 1/4 节职责描述、第 5/6 节链路与对照表为 LLM 结合实际文件阅读后的归纳，均已就地标注
- 其余数字类结论全部来自 RepoProfile JSON 对应字段，见各节尾部 `<!-- 来源 -->`
