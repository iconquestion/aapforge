# AAP 契约冻结

本文记录 AAPForge 在 M0 阶段为 v1 固化的事实。这些内容是 AAPForge
自己维护的已验证规则副本；正常运行不得导入 HaloCue 运行时代码。

| 契约 | 来源 | 状态 |
| --- | --- | --- |
| Newtonsoft `$type` 字符串，包括工程数据、节点列表、台词数据列表、角色记录列表、Guid 列表和整数列表 | `D:\文档\GitHub\HaloCue\script2aap.py`，常量 `T_PROJ`、`T_NODES`、`T_ENTRY`、`T_SNODE`、`T_EXIT`、`T_SLIST`、`T_SCRIPT`、`T_CLIST`、`T_CHAR`、`T_GLIST`、`T_ILIST` | 已验证 |
| 工程包裹结构，以及入口节点 -> 台词节点 -> 出口节点的图结构 | `D:\文档\GitHub\HaloCue\script2aap.py`，`wrap_project` | 已验证 |
| 入口节点 Guid 全为 0 | `D:\文档\GitHub\HaloCue\script2aap.py`，`wrap_project` | 已验证 |
| 场景 Guid 规则 | `D:\文档\GitHub\HaloCue\script2aap.py`，`uuid.uuid5(NS, f"{project}/scene/{i}")` | AAPForge v1 采用的已验证规则 |
| 配音 Guid 规则 | `D:\文档\GitHub\HaloCue\script2aap.py`，`voice_guid(project, n)` | AAPForge v1 采用的已验证规则 |
| 出口节点和出口内嵌配音 Guid 规则 | `D:\文档\GitHub\HaloCue\script2aap.py`，`wrap_project` | AAPForge v1 采用的已验证规则 |
| 台词数据字段顺序 | `D:\文档\GitHub\HaloCue\verify.py`，`SCRIPT_KEYS`；`script2aap.py` 的台词字典构造 | 已验证 |
| 角色记录字段顺序 | `D:\文档\GitHub\HaloCue\verify.py`，`CHAR_KEYS`；`script2aap.py`，`blank_char` | 已验证 |
| 角色槽位数 = 6 | `D:\文档\GitHub\HaloCue\script2aap.py`，`SLOTS = 6`；`verify.py` 的槽位校验 | 已验证 |
| 旁白 / 无立绘说话者使用 0 号槽 | `D:\文档\GitHub\HaloCue\stage.py` 的位置模型注释；`script2aap.py` 的旁白分支和说话者回退逻辑 | 已验证 |
| `selectionGroup = 0` | `D:\文档\GitHub\HaloCue\script2aap.py` 的台词数据构造；`verify.py` 的样例校验 | 已验证 |
| 默认背景 `BG_Black` | `D:\文档\GitHub\HaloCue\script2aap.py`，`cfg.get("default_bg", "BG_Black")` | 已验证为写出器默认输入 |
| 默认背景音乐 `999` | `D:\文档\GitHub\HaloCue\script2aap.py`，`cfg.get("default_bgm", 999)` | 已验证为默认 / 静音写出值 |
| 背景哈希 | `D:\文档\GitHub\HaloCue\tables.py`，`xxh32` 和 `bg_id`；模块来源说明写明 `xxHash32(utf8, seed=0)` | 已验证 |
| 过渡映射 | `D:\文档\GitHub\HaloCue\tables.py`，`TRANSITION` | 已验证；HaloCue 中注明这是单来源提取 |
| 背景效果映射 | `D:\文档\GitHub\HaloCue\tables.py`，`BGEFFECT` | 已验证 |
| 表情气泡映射 | `D:\文档\GitHub\HaloCue\build_index.py`，`EMOTICON` | 已验证；HaloCue 注明来自 `.aap` / `.aas` 配对反推 |
| 动作映射 | `D:\文档\GitHub\HaloCue\build_index.py`，`ACTION`；`script2aap.py`，`ACTION_IDS` | 已验证 |
| 进退场映射 | `D:\文档\GitHub\HaloCue\build_index.py`，`APPEAR`；`D:\文档\GitHub\HaloCue\stage.py`，`APPEAR` / `DISAPPEAR` | 已验证 |
| 立绘效果映射 | `D:\文档\GitHub\HaloCue\build_index.py`，`SHAPE`；`script2aap.py`，`SHAPE` 和 `SHAPE_IDS` | 已验证 |

## M0 未解决事项

- 完整 AA 背景、音效、背景音乐和角色资源目录尚未冻结。本工作区没有权威 AA
  资源目录，也没有经过审查的 HaloCue 导出数据可导入。
- 因此 `resources/core/index.json` 只包含 `BG_Black`。它的来源是 HaloCue
  写出器默认背景。该索引目前不包含角色、音效或 AA 背景音乐目录项。
- 背景音乐值 `999` 只作为默认 / 静音写出值固化在黄金样例中，不作为
  `resources/core/index.json` 里的背景音乐资源。
