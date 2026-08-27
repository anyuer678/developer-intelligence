# 安全策略

## 报告漏洞

请使用 GitHub 的 **Private vulnerability reporting**（仓库 Security 页 → Report a vulnerability）私密报告，**不要**在公开 issue 中披露细节。

- 确认响应：≤ 72 小时
- 修复目标：高危 ≤ 7 天，其余 ≤ 30 天

## 范围说明

本项目当前（P0 阶段）不含任何网络代码与密钥处理；未来接入 GitHub Token 时将强制经 keyvault 存取、日志脱敏，并在本文件更新威胁模型。
