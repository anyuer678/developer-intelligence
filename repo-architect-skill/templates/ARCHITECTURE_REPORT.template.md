# 架构报告 — {项目名}

> 由 repo-architect 生成于 {日期} · 扫描引擎 repo-intel-core

## 1. 项目概览

{一句话定位 + 规模速览：文件数/行数/主语言}

<!-- 来源: metrics / languages -->

## 2. 技术栈与框架

{languages 表格 + frameworks 清单（含版本与证据来源）}

<!-- 来源: languages / frameworks -->

## 3. 模块分析

| 模块 | 文件数 | 内聚度 | 职责（据扫描结果推断） |
|---|---|---|---|
{modules 表格行}

<!-- 来源: modules（cohesionScore 为三态：null=无内部导入关系） -->

## 4. 内部依赖与数据流

```mermaid
{architectureMermaid 字段原样嵌入}
```

关键边解读：{weight 靠前的边逐条说明谁依赖谁、意味着什么}
外部依赖面：{runtime/dev 分组要点}

<!-- 来源: dependencyGraph.internal / external -->

## 5. 入口与构建体系

{entryPoints 清单 + buildRun 命令与置信度}

<!-- 来源: entryPoints / buildRun -->

## 6. 架构风险

{逐条引用 metrics.complexityHotspots / todos / testEvidence / warnings；
无证据的风险判断放附录 A}

<!-- 来源: metrics / warnings -->

## 7. 优化建议

1. {建议} 【{高|中|低}置信】——依据：{字段引用}
2. ...

<!-- 来源: 综合以上各节；纯推测集中到附录 A -->

## 附录 A · 数据来源说明

- 扫描模式：full（硬依赖引擎）
- 事实类结论逐节对照 `<!-- 来源 -->`
- 纯推测区：{列出所有未经证据支撑的直觉判断；没有则写"无"}
