# AAPForge

AAPForge 是确定性的 AzureArchive `.aap` 工程生成器。

当前仓库包含：

- M0：契约 / 数据冻结。
- M0.1：收紧 `.aap` 线性节点链和台词节点校验。
- M1：源文件前端，负责读取 `.aapforge.json` / `.aapforge.jsonc`、结构校验和规范化。
- M1.1：收紧 `stage_ops` 源语言契约，并把规范中间表示升级为强类型数据模型。
- M2.0：维护者专用 HaloCue 离线索引到 Core Data 候选文件的引导流程。
- AA 官方角色事实提取器：维护者可从本地 AzureArchive 官方表生成角色事实数据。

当前不包含资源解析器、语义校验器、`.aap` 写出器、构建流程、安装器，也不依赖
HaloCue 运行时代码。
