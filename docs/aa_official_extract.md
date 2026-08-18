# AA 官方角色事实提取

`tools/extract_aa_official.py` 是维护者使用的数据构建工具。它从本地
AzureArchive 官方资源中读取 `ScenarioCharacterNameExcel`，生成 AAPForge 可审查的
官方角色事实数据。它不是 `.aap` 生成运行时的一部分，运行 AAPForge 不会扫描 AA
安装目录，也不需要 UnityPy。

## 命令

```powershell
py -3 tools/extract_aa_official.py "D:\Games\AzureArchive" --output resources\generated\aa_official_characters.json
```

也可以传入 `AzureArchive.exe` 路径。若自动缓存探测失败，显式传入：

```powershell
py -3 tools/extract_aa_official.py "D:\Games\AzureArchive" --cache "D:\AA资源缓存"
```

Unity 资源读取依赖 UnityPy。只在需要重新提取官方角色事实时安装：

```powershell
py -3 -m pip install ".[extract]"
```

## 输出

默认输出到 `resources/generated/aa_official_characters.json`。这是“AA 官方角色事实”
文件，不是完整 Core，不能覆盖 `resources/core/index.json`。

结构示例：

```json
{
  "schema_version": "1.0",
  "source": {
    "kind": "aa_official_flatdata",
    "table": "ScenarioCharacterNameExcel",
    "catalog_sha256": "...",
    "bundle_name": "...",
    "bundle_catalog_hash": "...",
    "bundle_cache_hash": "...",
    "bundle_sha256": "..."
  },
  "characters": [
    {
      "id": "호시노",
      "canonical_name": "星野",
      "name": "星野",
      "aliases": [],
      "spine_available": true,
      "portrait_verified": false,
      "faces": [],
      "records": [
        {
          "native_key": 123,
          "shape": 3,
          "club": "對策委員會",
          "spine": "UIs/03_Scenario/02_Character/CharacterSpine_hoshino",
          "avatar": "UIs/01_Common/01_Character/NPC_Portrait_hoshino"
        }
      ],
      "evidence": [
        {
          "kind": "official",
          "source": "aa:ScenarioCharacterNameExcel"
        }
      ]
    }
  ],
  "name_index": {
    "星野": ["호시노"]
  },
  "ambiguous_names": {},
  "stats": {
    "characters": 1,
    "records": 1,
    "names": 1,
    "ambiguous_names": 0
  }
}
```

## 事实边界

`NameKR` 在 `ScenarioCharacterNameExcel` 中是剧情角色的标识字段，而不是绝对唯一、
稳定的真实人物 identity。对普通记录，它可用于聚合同一逻辑角色；但真实官方数据
中存在 `"???"` 这样的 placeholder identifier，表示匿名/隐藏身份占位，不应被视为
稳定唯一角色 identity。

`ScenarioCharacterNameExcel` 能证明角色标识符、官方显示名称、官方多行记录、
社团、Spine 路径是否至少存在、头像路径、`native_key` 和 `shape`。它不能证明
faceId，因此 `faces` 必须保持为空，`portrait_verified` 必须保持 `false`。

同一个正常角色标识符出现多条官方行时，全部保存到 `records`。这里不叫 `variants`，
因为当前只能证明“官方表有多条记录”，还不能证明每条都等价于 AAPForge 可选择的
立绘变体。

已知的 placeholder identifier（当前仅处理 `"???"`）不进入正常 `characters` 聚合，
也不进入 `name_index`。这些记录仍是有效官方事实，因此保存在单独的
`unresolved_records` 中，完整保留每条 FlatData 原始字段：`id`、`name`、
`native_key`、`shape`、`club`、`spine`、`avatar`。不根据 `spine` / `avatar` 猜测真实
角色身份，也不把 `"???"` 和 `"？？？"` 做 Unicode 等价合并。

`records` 统计只统计正常角色 `characters[*].records` 的总数；`unresolved_records`
是单独统计字段，避免把 placeholder 的有效官方事实混入正常角色计数。

`club` 保存在每条 `records` 中，不提升到角色顶层。当前没有充分证据证明同一个
角色标识符的全部官方记录一定拥有相同社团。

`spine_available` 使用确定性规则：

```text
any(bool(record["spine"]) for record in records)
```

头像字段按官方原值保存。即使出现 `NPC_Portrait_Null`，也不会派生
`avatar_available` 之类的能力字段。

## 名称歧义

正常 identifier 仍采用严格一致性规则：同一 `id` 允许相同 `name` 的多条记录聚合，
但不同 `name` 仍然抛错。placeholder `"???"` 不走这个规则，直接进入
`unresolved_records`。`name_index` 仅覆盖正常角色，不能包含 placeholder。

`name_index` 是一对多索引：

```text
官方显示名称 -> 1..N 个角色标识符
```

同名不同标识符是真实歧义，会保存在 `ambiguous_names`，不会自动消歧。相反，同一
标识符对应多个不同官方显示名称表示身份模型无法解释，提取器会严格失败。

## 严格失败

提取器保持失败优先：找不到安装结构、缺少 `catalog.json`、Addressables 条目异常、
资源包候选不唯一、UnityPy 解析失败、找不到 `ScenarioCharacterNameExcel`、解析结果
为空或同一标识符名称冲突，都会停止。不会猜缓存、猜最新文件、跳过坏行继续。
