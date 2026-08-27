---
name: repo-onboarding
description: Generate a PROJECT_GUIDE.md for any repository so a new developer or AI agent can onboard in minutes. Use when entering an unfamiliar codebase, writing project docs, or initializing agent context for a repo.
---

# repo-onboarding 工作流

目标：为当前仓库产出 `PROJECT_GUIDE.md`。**所有事实必须来自扫描 JSON，缺失写"未检测到"，禁止编造。**

## 步骤

1. **扫描**
   ```bash
   python <skill_dir>/skill/scripts/scan.py scan <仓库路径> --pretty
   ```
   auto 模式自动选择 lite（零依赖）/ full（需 `pip install "repo-intel-core>=0.1"`）。
   记下 warnings 里 `SCAN_MODE` 的值，附录 A 必须注明。

2. **校验 JSON**：确认 `languages` 非空；若含 `EMPTY_REPO` 或大量 `READ_ERRORS`，先向用户确认路径是否正确。

3. **撰写文档**：严格按 `templates/PROJECT_GUIDE.template.md` 的七节顺序输出；
   系统提示词见 `prompts/system.md`（反幻觉铁律与自检清单在那里，必须遵守）。

4. **来源附录**：每节末尾用 `<!-- 来源: languages / entryPoints -->` 标注数据来源字段。

5. **交付**：文件写入仓库根目录 `PROJECT_GUIDE.md`，对话中给出 ≤5 行摘要 + 扫描模式。

## 禁止事项

- 编造任何命令、路径、依赖版本
- 增删模板的一级标题
- 在文档里推测"作者意图"类语义判断（那是上层 LLM 的活，且要标注"据扫描结果推断"）
