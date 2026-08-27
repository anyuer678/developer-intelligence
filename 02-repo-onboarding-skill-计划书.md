# 02 · repo-onboarding-skill 计划书 —— 首发开源 Skill

> 性质：开源组件 · 路线的分发与验证探针
> 上游：01 repo-intel-core（有降级模式，可独立发布）
> 下游：为 03 github-intelligence 验证需求、积累首批用户
> 发布阵地参考：reasonix-skills（经验）、dsh-logtimeline（⭐4，运营参照物）

---

## 一、一句话定位

**对任何仓库说一句话，生成一份让新人（人或 AI Agent）10 分钟上手的《PROJECT_GUIDE.md》。**

## 二、背景与问题

### 为什么要做这个（而不是别的 Skill）

1. **自己的痛点最真实**：25 个仓库大量缺少像样的 README；每次切回旧项目，AI 和自己都要重新认识一遍。
2. **演示效果最直观**："输入 repo → 输出一份漂亮文档"是所有 Skill 里最容易做 GIF、最容易被转发的一类。对比 Developer Diary（要持续用才见效）和 Commit Intelligence（竞品成堆），Onboarding 是冷启动最优解。
3. **与 evocode 错位**：evocode 做的是"体检/技术债"（给维护者看病），本 Skill 做的是"入门指南"（给新人和 Agent 看地图）——不重叠。
4. **有现成渠道**：awesome-dsh-plugin 已 fork 待 PR；dsh-logtimeline 证明了生态内有真实反馈。

### 目标用户的三个场景

| 场景 | 用户 | 价值 |
|---|---|---|
| 接手别人的/自己很久前的项目 | 开发者 | 免去翻代码猜架构的半小时 |
| AI Agent 初始化项目上下文 | agent 用户（dsh / Claude Code / opencode 等） | 一份稳定的项目事实摘要，替代每次现场摸索 |
| 开源项目补文档 | 维护者 | 从"懒得写 README"到"有一份 80 分底稿" |

## 三、目标与非目标

### 目标

| # | 目标 | 可验证标准 |
|---|---|---|
| G1 | 开箱即用 | 不装 Python、不配 keyvault 也能跑（降级模式）；装了 core 则质量更高 |
| G2 | 文档质量 | 自己 25 个仓库全部生成，人工评审"可直接使用"比例 ≥ 80% |
| G3 | 幻觉可控 | 文档中所有"事实类"内容（命令/路径/依赖版本）必须来自扫描证据，LLM 只负责组织语言——每节标注来源 |
| G4 | 获得真实反馈 | 达到 Gate 1（见总路线图 §四）：4 周 Star ≥ 50 或 ≥ 3 个非本人 issue |

### 非目标

- ❌ 不做持续更新（不是 Project Memory，不做 `.memory/` 增量维护——那是后续姊妹 Skill）
- ❌ 不做多语言文档输出 v1（中文优先，英文其次）
- ❌ 不绑定 dsh 专有 API（做成通用 agent skill 形态，dsh 只是首发宿主）
- ❌ 不做 Web 服务

## 四、产品形态设计

### 双模式架构（关键决策）

```
                    ┌────────────────────────────┐
 用户: "给这个仓库   │      onboarding skill       │
 生成入门指南"  ──▶ │  (SKILL.md + scripts/)      │
                    └─────┬──────────────┬───────┘
                          │              │
              检测到 repo-intel-core?    否（或轻量仓库）
                          │              │
                 ┌────────▼───────┐ ┌───▼────────────────┐
                 │ 完整模式        │ │ 降级模式（内置）     │
                 │ pip 装 core     │ │ 内嵌 ~200 行纯启发式│
                 │ → RepoProfile   │ │ 扫描脚本（读 manifest│
                 │ 全字段          │ │ /目录/入口粗判）     │
                 └────────┬───────┘ └───┬────────────────┘
                          └──────┬──────┘
                                 ▼
                     LLM 按 PROJECT_GUIDE 模板组织语言
                     （provider 可插拔：DeepSeek 默认）
                                 ▼
                        PROJECT_GUIDE.md
```

为什么必须双模式：Skill 的第一印象取决于"clone 即用"。要求用户先装一个 Python 引擎会流失大部分人；而降级模式保证 60 分底线，完整模式提供 90 分体验——同时给 core 导流（README 写明"装 core 提升 X"）。

### SKILL.md 形态草案

```markdown
---
name: repo-onboarding
description: Generate a PROJECT_GUIDE.md for any repository so a new
  developer or AI agent can onboard in minutes. Use when entering an
  unfamiliar codebase, writing READMEs, or initializing project context.
---

# 工作流程
1. 运行扫描脚本（自动选择完整/降级模式），得到 RepoProfile JSON
2. 校验 warnings；缺失关键字段时向用户确认而非编造
3. 按模板分节撰写，事实性内容只允许引用 JSON 字段
4. 输出 PROJECT_GUIDE.md 至仓库根目录，并在对话中给出 5 行摘要
```

### PROJECT_GUIDE.md 输出模板（v1 定稿）

```markdown
# PROJECT_GUIDE — <项目名>
> 由 repo-onboarding 生成于 <日期> · 基于 <完整|降级> 模式扫描

## 1. 这个项目是什么
<一句话定位 + 三行以内说明 · 来源: README 提取 + LLM 归纳>

## 2. 技术栈速览
<语言占比表 · 框架清单及用途 · 来源: languages/frameworks>

## 3. 五分钟跑起来
<install/dev/test 命令 · 前置依赖声明 · 来源: buildRun + evidence>
⚠️ 无法推断的步骤明确写"未检测到"，绝不编造

## 4. 目录地图
<顶层目录表：路径/职责猜测/关键文件 · 来源: structure+modules>

## 5. 核心流程走读
<从入口点出发的 1-3 条主链路描述 · 来源: entryPoints+dependencyGraph+LLM>

## 6. 改动从哪进
<"改 XX 应该动 YY"对照表 · 来源: modules+dependencyGraph>

## 7. 已知风险与注意点
<warnings 复述 + 大文件/复杂度热点提醒 · 来源: metrics>

## 附录 A. 数据来源说明
<本文件哪些结论来自静态扫描、哪些来自 LLM 推断，置信度分级>
```

附录 A 是差异化细节：**把幻觉管理做成明面上的功能**，用户可自查每个结论的出处。

## 五、MVP 范围界定

### v0.1（首发版）包含

- [x] SKILL.md（中英双语说明）+ `scripts/scan.py`（降级模式内嵌扫描）
- [x] 完整模式：检测到已安装的 repo-intel-core ≥ M2 时自动启用
- [x] PROJECT_GUIDE 模板渲染 + LLM 组织（DeepSeek 默认，OPENAI_BASE_URL 兼容协议可换）
- [x] 对 monorepo 的基本处理（按 workspace 分别生成小节）
- [x] README + 演示 GIF（录自己 25 个仓库里效果最好的 1 个，如 lumen 或 chatez）

### v0.1 明确不包含（防蔓延）

- [ ] 多语言输出切换
- [ ] 增量更新 / watch 模式
- [ ] GUI / 在线服务
- [ ] 对 GitHub URL 直接分析（要求用户本地 clone，URL 支持放 v0.2）

## 六、分阶段路线

### M0 —— 可自用
- [ ] 降级模式扫描脚本完成
- [ ] 模板 + LLM 层打通，对自己的 3 个仓库（lumen / chatez / kb-ui）产出可用文档
- **验收**：自己愿意把生成的 PROJECT_GUIDE 留在仓库里不删

### M1 —— 可发布
- [ ] 完整模式接入 core
- [ ] 幻觉防线：事实字段引用校验 + 来源附录
- [ ] README/GIF/LICENSE(MIT)/CHANGELOG 齐备；PR 进 awesome-dsh-plugin；在 reasonix-skills 互挂链接
- **验收**：Gate 1 启动计时

### M2 —— 可迭代（仅当 Gate 1 通过后）
- [ ] 按 issue 补框架规则、修文档模板
- [ ] v0.2：GitHub URL 直达（内部 clone 到临时目录）
- [ ] 姊妹 Skill 立项评估：Project Memory（`.memory/` 长期记忆）或 Project Architect（复用同一套 core，边际成本极低）

## 七、发布与运营清单

| 渠道 | 动作 | 参照 |
|---|---|---|
| GitHub 仓库本身 | GIF 放 README 第一屏；英文 README；topics: deepseek-harness / dsh / agent-skills / claude-code / opencode | dsh-logtimeline 的 topic 打法 |
| awesome-dsh-plugin | fork 已就绪，发版即 PR | 已 fork 在账号下 |
| DeepSeek/dsh 社区 | 发布帖附 GIF + 一个"30 秒试一试"教程 | logtimeline 先例 |
| V2EX / 掘金 | 《我给 25 个仓库批量生成了新人指南》实测文，带数据不带吹嘘 | — |
| r/LocalLLaMA 等 | 强调 Ollama 本地模型可用、零上传 | local-first 卖点 |
| reasonix-skills | README 互挂，形成个人 Skill 矩阵入口 | — |

运营铁律：**所有宣传素材都从真实产物里来**（贴自己仓库的真实输出），不造假图。

## 八、验收指标与止损线

### 成功指标（对应 Gate 1，发布起算 4 周）

| 指标 | 及格 | 良好 |
|---|---|---|
| Star | ≥ 50 | ≥ 150 |
| 非本人 issue/PR | ≥ 3 | ≥ 8 |
| 外部用户晒产物 | ≥ 1 | ≥ 3 |
| 自用留存 | 自己每周仍在用 | — |

### 止损决策树

```
Gate 1 未过
 ├─ 有 Star 无 issue → 分发还行，产物没戳中痛点 → 看 issue 缺失原因，
 │   换角度重包装一轮（比如主打"AI Agent 项目上下文初始化"）
 ├─ 无 Star → 分发失败或品类无感 → 换备选：Project Architect Skill 再试一轮
 └─ 两轮皆败 → 承认"Skill 先行"假设错误 → 直接做 03 自用版，Skill 战略冻结
```

## 九、风险与对策

| 风险 | 对策 |
|---|---|
| LLM 编造命令导致用户执行出错 | G3 防线：事实字段强制引用扫描结果；无法推断写"未检测到"；危险命令加警示前缀 |
| dsh 生态太小喂不饱曝光 | Skill 形态 harness 无关；README 同时给 dsh / Claude Code / opencode 三种接入示例 |
| 与未来 Claude Code 官方 `/init` 类功能撞车 | 差异化：深度扫描证据链 + 来源附录 + 中文优化 + 可换 provider；且撞车恰好证明方向正确 |
| core 未完成拖慢发布 | 双模式设计保证解耦——降级模式先行发布，core 后到 |

---

## 十、降级模式扫描器逻辑（scan.py 内嵌版，目标 ≤200 行）

```
1. 定位仓库根: 向上找 .git
2. 读 manifest 优先级: package.json > pyproject.toml > go.mod > Cargo.toml > pom.xml
3. 遍历目录(应用默认排除清单), 按扩展名统计语言占比 top5
4. 入口粗判:
   a. package.json 存在 → bin/scripts.dev 直接取
   b. 找 main.* / app.py / __main__.py / cmd/*/main.go
5. buildRun 直取: scripts.{dev,test,start} 或 Makefile 前两个 target 或 go run ./cmd/<name>
6. 目录地图: 顶层目录 + 各自文件数, 标注含 README 的目录
7. 技术栈线索: dependencies 里 grep 已知框架关键词表(~30 条内置)
8. 组装 mini-profile JSON (schema 为完整 RepoProfile 的子集, 字段名一致!)
9. 输出 warnings: 未识别的 manifest / 超大目录跳过记录
10. 把 JSON 原文交给 SKILL.md 流程第 3 步(LLM 组织)
关键约束: 子集字段名必须与完整 Schema 完全一致 —— 保证上层模板零改动兼容两种模式
```

## 十一、LLM Prompt 主模板（v1 冻结稿）

### System Prompt

```text
你是一名严谨的软件文档工程师，正在为一个陌生代码库撰写《新人入门指南》。

铁律：
1. 你会收到一份扫描产生的 JSON（可能不完整）。事实性内容（命令、路径、依赖、版本、文件名）
   只允许来自 JSON；JSON 中没有的信息，写"未检测到"，禁止推测补全。
2. 你的职责是把结构化事实组织成人类可读的叙述，并做少量安全的语义归纳
   （如从模块名推断职责），所有归纳句以"据扫描结果推断"或类似措辞开头。
3. 输出遵循给定的 Markdown 模板章节顺序，不得增删一级标题。
4. 语言：简体中文。语气：克制、具体、零形容词堆砌。
5. 写完后执行末尾的自检清单，不通过则自行修正后再输出。
自检清单：
□ 每条命令都出现在 JSON 的 buildRun/entryPoints 中？
□ 没有"应该/大概/可能是"修饰任何命令行指令？
□ 第 7 节风险全部引用了 warnings 或 metrics 字段？
```

### User Prompt 骨架

```text
[扫描模式: full|lite] [仓库: {name}]
<RepoProfile JSON 原文>
---
请按 PROJECT_GUIDE 模板输出。附录 A 中逐节标注数据来源字段。
```

Prompt 版本随 Skill 发版记录在 CHANGELOG——**改 prompt = 改产品**。

## 十二、README 结构骨架（发布用）

```markdown
<div align=center>
<img GIF 第一屏: 对 lumen 仓库跑一次的全过程录屏, 8~15 秒, 无声>
# repo-onboarding
一句话(中英双份) · 徽章(license/py版本/skills数量)
</div>

## Why — 接手新项目的半小时都花在哪了(3 行)
## Quick Start — 三种宿主各 4 行代码块: dsh / Claude Code / opencode
## 两种模式 — lite 开箱即用; 安装 repo-intel-core 后自动升级 full(质量对比表)
## 输出示例 — 折叠块放真实生成的 PROJECT_GUIDE 全文
## 隐私 — 纯本地扫描; LLM 调用只上传扫描摘要, 不上传源码原文
## Roadmap / FAQ(3条) / 致谢与关联(repo-intel-core, reasonix-skills)
```

## 十三、发布日动作清单

| 序 | 动作 | 时点 |
|---|---|---|
| 1 | repo 转 public，置顶 issue #1「反馈收集」 | 发布日 09:00 |
| 2 | PR 进 awesome-dsh-plugin；reasonix-skills README 加链接 | 09:30 |
| 3 | dsh 社区发帖（GIF+30 秒教程） | 10:00 |
| 4 | V2EX / 掘金实测文发布 | 12:00 |
| 5 | r/LocalLLaMA 英文帖（强调 Ollama 可用） | 21:00（对齐海外时段） |
| 6 | 记录各渠道初始数据进决策日志 | 24:00 后 |
| 7 | 第 72 小时回看：哪个渠道有真实反应 → 集中回复互动 | D+3 |

## 十四、Issue 应对预案

| 反馈类别 | 首响应要点 | 修复 SLA |
|---|---|---|
| 跑不起来 | 要 log + 环境（OS/python/宿主）；先发 workaround | 48h 内 hotfix |
| 文档某节不准 | 感谢 + 请对方贴 JSON（`--debug` 开关输出）→ 归因到规则缺失还是 LLM 层 | 规则类一周内 |
| "支持 X 语言/框架" | 指引提 rules yaml PR（表驱动就是为这个设计的） | 随下个 minor |
| "能不能自动保持更新" | 说明属于姊妹 Project Memory 的路线，邀请订阅 release | — |

## 十五、版本规划

| 版本 | 内容 | 前置 |
|---|---|---|
| v0.1 | 双模式 + 中文模板 + 发布全套 | M1 完成 |
| v0.2 | GitHub URL 直达；英文文档输出开关 | Gate 1 通过 |
| v0.3 | 姊妹 Skill 立项（Project Memory / Architect） | v0.2 稳定 |
| v1.0 | API/prompt 稳定承诺 + 外部用户 ≥3 个真实使用案例 | 数据说话 |

---

> **AI 开发须知**：本项目由 AI 协同开发；prompt 属产品本体走人工审批门、自举评测集等要点见 [06-AI协同开发手册.md](./06-AI协同开发手册.md) §八。
