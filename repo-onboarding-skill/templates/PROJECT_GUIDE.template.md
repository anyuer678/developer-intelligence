# PROJECT_GUIDE — {项目名}

> 由 repo-onboarding 生成于 {日期} · 基于 {完整|降级} 模式扫描

## 1. 这个项目是什么

{一句话定位 + ≤三行说明}

<!-- 来源: README 提取 + structure.configFiles -->

## 2. 技术栈速览

| 语言 | 占比 | 文件数 | 行数 |
|---|---|---|---|
{languages 表格行}
框架：{frameworks 清单及用途，lite 模式无此数据时写"未检测到（建议安装 repo-intel-core 获得完整模式）"}

<!-- 来源: languages / frameworks -->

## 3. 五分钟跑起来

```bash
# 安装
{installCmd}
# 开发运行
{devCmd}
# 测试
{testCmd}
```

⚠️ 无法推断的步骤明确写"未检测到"，绝不编造。

<!-- 来源: buildRun.installCmd/devCmd/testCmd + entryPoints -->

## 4. 目录地图

| 目录 | 职责猜测 | 关键文件 |
|---|---|---|
{structure.topLevelDirs 行}

<!-- 来源: structure.topLevelDirs / modules -->

## 5. 核心流程走读

{从 entryPoints 出发的 1~3 条主链路描述；dependencyGraph 存在时可引用模块边}

<!-- 来源: entryPoints / dependencyGraph + 据扫描结果推断 -->

## 6. 改动从哪进

| 想改什么 | 动哪里 |
|---|---|
{modules × dependencyGraph 推导的对照表；lite 模式可省略本节并注明}

<!-- 来源: modules / dependencyGraph.internal -->

## 7. 已知风险与注意点

{warnings 复述 + metrics.complexityHotspots / largestFiles 提醒}

<!-- 来源: warnings / metrics -->

## 附录 A · 数据来源说明

- 扫描模式：{lite|full}（{模式说明一句}）
- 本文件哪些结论来自静态扫描、哪些来自 LLM 推断，逐节对照上方 `<!-- 来源 -->` 注释
