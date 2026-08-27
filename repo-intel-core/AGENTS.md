# AGENTS.md — repo-intel-core

## 项目一句话
把任意代码仓库变成结构化 RepoProfile JSON：纯静态启发式，零 LLM、零网络。

## 命令
- 安装: `pip install -e ".[dev]"`
- 全量测试: `pytest`（改任何代码后必须运行）
- lint: `ruff check src tests && ruff format --check src tests`
- 单测某文件: `pytest tests/test_language_detect.py`
- CLI 冒烟: `repo-intel scan . --pretty`

## 架构地图
- `src/repo_intel/schema/profiles.py` — pydantic 模型 = JSON Schema 单一来源（camelCase 别名输出）
- `src/repo_intel/rules/` — yaml 规则表 + loader（表驱动：加语言/排除项优先改 yaml 而非代码）
- `src/repo_intel/detect/` — 语言识别、结构扫描
- `src/repo_intel/scanner.py` — 编排器：单趟 os.walk 产出 FileRecord 流，喂给各检测器
- `src/repo_intel/cli.py` — argparse CLI（scan 命令）
- `tests/fixtures.py` — 内存构造迷你仓库树；golden 快照体系 M0 之后引入

## 当前状态
- 已完成: M0 + M1 + M2 + M3（GitMeta / 月度信号包 signals 子命令 / golden 快照基线 / 框架内容消噪）——85 测试全绿，ruff 零告警。A 线对 02/03 号项目的引擎承诺全部就绪
- 挂起（需人工）: G2 构建命令抽查、M1 五仓库模块划分确认、真实 25 仓库 golden 扩充（待本地克隆）
- 下一步: A 线收尾 → 切 B 线 repo-onboarding-skill 骨架（完整模式直接消费 core）

## 硬约束（违反即返工，无例外）
1. `schema/profiles.py` 已有字段不得改名/删除/改类型——只能新增可选字段；JSON 输出字段名为 camelCase 别名，保持与计划书 Schema v1.0 一致
2. 不新增第三方依赖，除非任务卡明确允许（当前仅 pydantic + PyYAML）
3. `src/` 内禁止出现任何网络请求或 LLM 调用——本项目是纯静态引擎
4. 对垃圾输入的唯一合法反应是降级并写 warnings，不允许抛异常中断整个扫描
5. 所有路径处理必须容忍中文与空格（Windows 主力环境）
6. 注释与文档用中文；commit 用 Conventional Commits（type(scope): 摘要）

## 禁改区
- `docs/tasks/*.md` 的"验收命令"一经批准不得修改（只能由新卡替代旧卡）

## 完成定义
新代码有对应测试 + `pytest` 全绿 + ruff 零告警 + 本卡验收命令通过。
