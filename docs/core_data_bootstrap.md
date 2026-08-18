# Core Data Bootstrap

本页记录 M2.0 的维护者专用引导流程。它只把 HaloCue 已生成的离线
`aa_resources.json` 转成 AAPForge Core Data 候选文件，不实现运行时解析、
语义校验、写出、构建或安装。

## 输入

输入文件来自 HaloCue 的 `build_index.py`，结构上包含：

- `bg`：背景名到已观察哈希值的映射。
- `bg_conflict`：HaloCue 已发现的同名背景冲突。
- `characters`：角色条目。AAPForge 只接收 `source` 为
  `official_flatdata` 的官方条目。
- `faces_used`：从历史工程观察到的角色表情编号。
- `face_capabilities`：表情能力候选与观察证据；只有观察证据可以进入候选。
- `enums`：HaloCue 侧枚举快照，仅用于和 `resources/core/tables.json` 交叉检查。

输入中的 `_source`、`spine` 等路径线索不得写入输出。`spine` 只用于派生
`spine_available = bool(spine)`，不能因为角色来自官方表就默认有立绘。AAPForge
运行时也不得导入 HaloCue 代码、扫描 AA 安装目录或读取用户素材。

## 白名单

转换必须通过 `tools/bootstrap_allowlist.json` 明确列出本轮允许进入候选的数据：

- `backgrounds`：背景名。
- `characters`：角色中文名。
- `faces`：按角色中文名列出允许进入候选的表情编号。

M2.0 的最小切片只包含桃井、表情 `00` 和 `03`，以及 `BG_Black`、
`BG_GameDevRoom`。如果输入缺证据，工具必须失败，不能臆造。

## 输出

运行示例：

```powershell
py -3 tools/bootstrap_from_halocue.py path\to\aa_resources.json
```

默认输出到 `build/core_candidates/halocue_core_candidate.json`。工具会拒绝直接覆盖
`resources/core/index.json`，候选文件必须人工审查后再决定是否冻结。

输出证据使用三个明确来源种类：

- `official`：AA 官方表证据。
- `observed`：历史工程或 HaloCue 索引中的观察证据。
- `derived`：AAPForge 根据冻结算法派生出的值，例如背景哈希。

## 失败条件

以下情况必须失败并给出错误码：

- 白名单项在 HaloCue 输入中不存在。
- 角色不是可确认的官方条目，或同名角色不唯一。
- HaloCue 报告 `bg_conflict`。
- 背景哈希与 `xxHash32:utf8:seed0` 契约不一致。
- 表情只有候选证据，没有历史工程观察证据。
- HaloCue 枚举快照与 `resources/core/tables.json` 冲突。

多立绘变体不会让角色身份构建失败。身份解析只回答“这个显示名称是否能唯一
对应角色标识符”；如果后续步骤需要选择具体立绘或表情变体，应在那个步骤再做
唯一性检查，当前引导流程不能自动选择第一个变体。

## 校验

候选文件可以通过核心数据校验脚本检查：

```powershell
py -3 tools/verify_core_data.py build\core_candidates\halocue_core_candidate.json
```
