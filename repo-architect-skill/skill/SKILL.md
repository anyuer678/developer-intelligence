---
name: repo-architect
description: Generate an ARCHITECTURE_REPORT.md for any repository — module responsibilities, coupling, data flow, mermaid dependency graph, risks and prioritized suggestions. Use when reviewing architecture, planning refactors, or documenting a codebase design.
---

# repo-architect 工作流

前置：`pip install "repo-intel-core>=0.1"`（本 Skill 硬依赖，无降级模式）。

## 步骤

1. **扫描**
   ```bash
   python <skill_dir>/skill/scripts/scan.py scan <仓库路径> --pretty
   ```
   产物含 `modules / dependencyGraph / frameworks / buildRun / metrics` 与现成的
   `architectureMermaid` 字段。

2. **校验**：`modules` 为空或全 null 时停止——该仓库可能过小或语言未覆盖，
   如实告知用户而非硬写报告。

3. **撰写报告**：严格按 `templates/ARCHITECTURE_REPORT.template.md` 八节结构；
   架构师角色铁律见 `prompts/system.md`。

4. **架构图**：第 4 节直接嵌入 JSON 的 `architectureMermaid` 字段内容（```mermaid 代码块）。

5. **建议分级**：第 7 节每条建议标注 `【高/中/低置信】` + 引用证据字段；
   无证据支撑的直觉判断必须整体移到附录 A 的"纯推测"小节。

## 禁止事项

- 编造模块职责（responsibility 字段为 null 时由你归纳，但必须以"据扫描结果推断"开头）
- 给出任何"直接重构代码"的指令——本报告只做体检与规划
- 增删一级标题
