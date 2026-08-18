# AAPForge 技术方案

## 1. 产品边界

### 1.1 目标

AAPForge 是一个独立的 AzureArchive `.aap` 工程生成器。

输入是一份 JSON / JSONC 源文件，描述剧本内容和明确的演出指令，包括：

- 文本；
- 角色声明；
- 表情；
- 动作；
- 立绘位置；
- 立绘移动；
- 入场与退场；
- 背景；
- BGM；
- 音效；
- 背景过渡；
- 地点文本；
- 等待时间。

输出为：

```text
ProjectName.aap
ProjectName/
  manifest.json
  build_report.json
  voices/
    voices.txt
  bgs/
  sounds/
  bgms/
```

AAPForge 的目标是：

1. 定义一套明确、可校验、可版本化的 AAPForge 源语言。
2. 将合法输入按确定规则编译成 AA 可以识别的 `.aap` 工程。
3. 对所有无法唯一解释的输入拒绝编译，而不是猜测。
4. 为 CLI、CI 和 agent workflow 提供稳定诊断。
5. 在不运行 AA、不读取 AA 安装资源的情况下完成正常 `validate` 与 `build`。
6. 允许通过显式的后续 install 操作把已构建工程部署到 AA。

### 1.2 非目标

AAPForge v1 不负责：

- AI 推断；
- 自动分镜；
- 自动演出；
- 自动角色猜测；
- 相似角色名匹配；
- 拼音或翻译匹配；
- 自动发现未知 AA 行为；
- AA 多版本适配；
- AA 协议逆向框架；
- HaloCue UI；
- HaloCue 审查流程；
- HaloCue 草稿系统；
- 自定义角色；
- 自动生成自定义 BGM id；
- 自动修改用户素材库；
- 自动修复不符合预期的 AA 行为。

仓库不得包含：

- AA 可执行文件；
- AA data 目录；
- AA 内部版权资源；
- 用户个人自定义素材；
- 用户作品；
- 用户本地配置。

### 1.3 核心设计原则

AAPForge 是：

> **面向 AA `.aap` 工程生成的源语言 + 编译器。**

不是智能脚本助手。

基本原则：

- 输入必须显式表达意图。
- compiler 不猜。
- normalizer 不改变语义。
- resolver 不推断未知事实。
- validator 不替用户做选择。
- writer 只写已经验证过的 IR。
- 任何阶段出现不符合预期的结果都立即停止。
- 不因“很可能没问题”继续执行后续有副作用阶段。

同一合法输入在：

```text
相同 AAPForge 版本
+ 相同 core data
+ 相同 local library
```

下，应产生语义稳定的结果。

AAPForge 不承诺：

- 跨 AA 版本一致；
- 跨未来 AAPForge 主版本一致；
- 不同外部资源库下输出一致；
- `.aap` 字节级永远不变。

---

## 2. AA 与 HaloCue 假设

### 2.1 AA 定位

当前阶段认为：

> AA 是相对黑盒、相对稳定、不可控的外部系统。

AAPForge v1：

- 不做 AA 多版本体系；
- 不做 AA 版本探测；
- 不做 compatibility profile；
- 不根据 AA 版本切换 writer；
- 不为未知未来变化预设抽象层。

当前暂定 AA 已知 `.aap` 行为不会变化。

如果未来发现变化，通过：

```text
新需求
→ 新 fixture
→ 新 contract
→ 新 AAPForge 版本
```

处理。

### 2.2 HaloCue 定位

HaloCue 已经实际验证和使用的以下事实，在 v1 中视为可信输入：

- `.aap` Newtonsoft JSON contract；
- `$type`；
- 字段名；
- 字段顺序；
- Node 类型；
- 6 槽 characters 结构；
- `speakerSlotNum`；
- `highlightedSlotNums`；
- `selectionGroup=0`；
- 背景 hash；
- transition 枚举；
- bgEffect 枚举；
- emoticon 枚举；
- action 枚举；
- appear 枚举；
- shapeOverride 枚举；
- AA character identifier；
- faceId 能力；
- 已验证背景名；
- 已验证 sound 名；
- 已验证 BGM id；
- GUID 生成规则。

AAPForge 当前不重新证明这些规则是不是 AA 唯一正确实现。

目标仅是：

> 按这些已知规则稳定生成符合预期的工程。

### 2.3 HaloCue 仅作为 bootstrap 来源

AAPForge 第一次建立自身数据时，可以离线引用 HaloCue。

完成 bootstrap 后：

```text
HaloCue
   ↓ 一次性/维护者显式导入
AAPForge core data
   ↓
AAPForge runtime
```

正常：

```text
validate
build
inspect
```

均不得运行时依赖 HaloCue。

HaloCue 后续更新不得隐式改变 AAPForge 输出。

### 2.4 署名

AAPForge README、文档和发行说明应保留：

```text
Powered by HaloCue
```

---

## 3. 全局判定规则

### 3.1 规范词

“必须”：

> 不满足时操作失败并产生稳定诊断。

“默认”：

> 输入缺省时 normalizer 写入的唯一规范值。

“允许”：

> schema / semantic validator 接受。

“禁止”：

> 出现即失败，除非本文明确规定兼容行为。

“推荐”：

> 不影响 correctness，但影响可维护性。

### 3.2 Fail-fast

每一个阶段只有在当前阶段满足预期后才能进入下一阶段。

如果：

```text
预期：HaloCue 已验证规则下该结构应成功
实际：AA 拒绝 / 行为异常
```

AAPForge 不擅自判断：

- 是 AAPForge bug；
- 是 HaloCue 数据错误；
- 是 AA 更新；
- 是环境问题。

统一处理为：

> **observed AA behavior differs from current expected contract**

停止流程，保留诊断和产物证据。

---

# 4. 数据资产

## 4.1 数据生命周期分离

AAPForge v1 把数据严格分成三类：

```text
1. core data
2. local library
3. project assets
```

三者不得混用。

---

## 4.2 Core Data

目录：

```text
resources/
  core/
    index.json
    tables.json
```

Core Data：

- 随 AAPForge repo/version 发布；
- 进入 Git；
- 由 AAPForge 维护者管理；
- 不包含用户素材文件；
- 不包含本机路径；
- 不包含 local library；
- 不因用户 AA 安装不同而自动变化。

### 4.2.1 `index.json`

只表示：

> **AAPForge 当前认可的 AA 资源事实。**

例如：

```jsonc
{
  "schema_version": "1.0",

  "backgrounds": [
    { "name": "BG_Black" },
    { "name": "BG_GameDevRoom" }
  ],

  "sounds": [
    { "name": "SE_Button_01" }
  ],

  "bgms": [
    {
      "id": 123,
      "name": "AA_Test_BGM",
      "verified": true
    }
  ],

  "characters": [
    {
      "id": "모모이",
      "canonical_name": "桃井",
      "name": "桃井",
      "aliases": ["才羽桃井", "Momoi"],
      "portrait_verified": true,
      "spine_available": true,
      "faces": [
        { "id": "00", "evidence": "observed" },
        { "id": "03", "evidence": "observed" },
        { "id": "99", "evidence": "observed" }
      ]
    }
  ]
}
```

`index.json` 不得保存：

- external custom background；
- external custom sound；
- external custom BGM；
- 用户素材 path；
- AA resources_dir；
- 用户角色；
- local library path。

### 4.2.2 Character name resolution

角色匹配集合由：

```text
id
canonical_name
name
aliases[]
```

共同生成。

匹配规则：

1. trim；
2. Unicode normalization；
3. case-insensitive exact match；
4. 不做模糊匹配；
5. 不做拼音；
6. 不做翻译；
7. 不做 AI。

如果同一个名字可以解析到多个角色：

```text
E_CAST_AMBIGUOUS
```

写入 `.aap` 的永远是：

```text
character.id
```

而不是 alias。

### 4.2.3 Face

Face 能力只由 core index 表示。

例如：

```json
"faces": [
  {"id": "00", "evidence": "observed"},
  {"id": "03", "evidence": "observed"}
]
```

剧本的 `cast` 不重复声明“角色拥有哪些 face”。

引用：

```json
"face": "03"
```

直接校验：

```text
03 ∈ core.characters[actor].faces
```

否则：

```text
E_FACE_UNVERIFIED
```

### 4.2.4 `tables.json`

用于无法由资源存在性推出的静态 `.aap` 语义。

包含：

```jsonc
{
  "schema_version": "1.0",

  "transitions": {
    "fade:500": 2,
    "fade:1000": 4,
    "crossfade:1000": 31
  },

  "bg_effects": {
    "none": 0
  },

  "emoticons": {
    "surprise": 3
  },

  "actions": {
    "none": 0,
    "jump": 6
  },

  "appears": {
    "enter:right": 1,
    "enter:left": 2,
    "enter:center": 3,
    "exit:left": 4,
    "exit:right": 5,
    "exit:center": 6
  },

  "shapes": {
    "none": 0,
    "closeup": 4
  },

  "hashes": {
    "background": "xxHash32:utf8:seed0"
  }
}
```

---

## 4.3 Local Library

Local Library 表示：

> 用户机器上已经验证、可在多个 AAPForge 工程间复用的外部素材。

它不属于 AAPForge core data。

推荐：

```text
~/.aapforge/
  library.json
  library/
    bgs/
    sounds/
    bgms/
```

Windows 实际实现可以使用用户 local app data。

示例：

```jsonc
{
  "schema_version": "1.0",

  "backgrounds": [
    {
      "id": "club_room_night",
      "name": "Custom_ClubRoom_Night",
      "path": "library/bgs/club_room_night.png",
      "verified": true
    }
  ],

  "sounds": [
    {
      "id": "doorbell",
      "name": "Custom_Doorbell",
      "path": "library/sounds/doorbell.wav",
      "verified": true
    }
  ],

  "bgms": [
    {
      "id": "night_theme",
      "name": "Custom_NightTheme",
      "path": "library/bgms/night_theme.ogg",
      "volume": 0.8,
      "bgmId": 1071265322,
      "verified": true
    }
  ]
}
```

### Local library 生命周期

```text
AAPForge repo
    × 不拥有

Git
    × 默认不追踪

用户机器
    ✓ 拥有

AAPForge build
    ✓ 只读
```

v1 build 不自动：

- 添加 library entry；
- 修改 verified；
- 生成 bgmId；
- 修复 path；
- 删除素材。

### BGM volume

v1 中 `volume` 只属于 library BGM definition。

BgmRef 不允许覆盖 volume。

例如：

```json
{
  "kind": "library",
  "type": "bgm",
  "id": "night_theme"
}
```

最终 Volume 来自：

```text
library.bgms[night_theme].volume
```

缺省：

```text
1.0
```

---

## 4.4 Project Assets

源文件中的：

```json
"assets": {}
```

表示只属于当前工程的私有素材。

v1 支持：

```text
background
sound
```

不支持：

```text
BGM
custom character
```

例：

```jsonc
{
  "assets": {
    "backgrounds": [
      {
        "id": "night_room",
        "name": "Custom_NightRoom",
        "path": "assets/bgs/night_room.png"
      }
    ],

    "sounds": [
      {
        "id": "click",
        "name": "Custom_Click",
        "path": "assets/sounds/click.wav"
      }
    ]
  }
}
```

路径相对于源文件所在目录。

绝对路径默认禁止。

---

# 5. 配置

## 5.1 配置目标

配置文件只描述：

- AAPForge 本地运行环境；
- local library；
- build 输出；
- 可选 install 信息。

推荐：

```jsonc
{
  "aapforge": {
    "core_index": "resources/core/index.json",
    "tables": "resources/core/tables.json"
  },

  "library": {
    "index": "C:\\Users\\User\\AppData\\Local\\AAPForge\\library.json"
  },

  "build": {
    "output_dir": "out",
    "allow_absolute_asset_paths": false
  },

  "aa": {
    "executable": "C:\\Program Files\\AzureArchive\\AzureArchive.exe",
    "data_dir": "C:\\Users\\User\\AppData\\LocalLow\\foxxlight\\AzureArchive\\data"
  }
}
```

注意：

> v1 不需要 `aa.resources_dir`。

正常 compiler 不读取 AA resources。

## 5.2 能力依赖

`validate`：

```text
需要 core index
需要 tables
仅源文件实际使用 kind=library 时需要 local library
不需要 AA
```

`build`：

```text
同 validate
+ project assets
不需要 AA
```

`inspect`：

```text
不需要 AA
```

`install`：

```text
需要 aa.data_dir
```

`--force-close-aa`：

```text
需要 aa.executable
```

### 配置错误

缺少当前操作需要的配置：

```text
E_CONFIG_MISSING
```

配置存在但非法：

```text
E_CONFIG_INVALID
```

不允许：

> 因没有配置 AA 路径，而导致一个完全不 install 的 build 失败。

---

# 6. 输入语言

## 6.1 文件格式

支持：

```text
.aapforge.json
.aapforge.jsonc
```

`.json`：

RFC 8259。

`.jsonc`：

允许：

- `// comment`
- `/* comment */`
- trailing comma

JSONC parser 必须正确处理：

```json
"https://example.com"
```

不能把字符串内部 `//` 识别为注释。

解析错误必须保留行列信息。

---

## 6.2 Schema version

使用：

> `major.minor`

不是 SemVer。

v1：

```json
{
  "aapforge": {
    "schema_version": "1.0"
  }
}
```

规则：

```text
1.0 → 1.1
```

允许兼容性新增字段或 branch。

不得修改已有字段含义。

破坏性变化进入：

```text
2.0
```

---

## 6.3 顶层结构

必须：

```jsonc
{
  "aapforge": {
    "schema_version": "1.0"
  },

  "project": {},

  "cast": {},

  "scenes": []
}
```

可选：

```text
assets
extensions
x_*
```

未知字段默认：

```text
E_SCHEMA
```

---

# 7. 资源引用模型

资源来源必须显式。

## 7.1 Background

```json
{
  "kind": "aa",
  "name": "BG_GameDevRoom"
}
```

或：

```json
{
  "kind": "library",
  "type": "background",
  "id": "club_room_night"
}
```

或：

```json
{
  "kind": "asset",
  "type": "background",
  "id": "night_room"
}
```

## 7.2 Sound

```json
{
  "kind": "aa",
  "name": "SE_Button_01"
}
```

```json
{
  "kind": "library",
  "type": "sound",
  "id": "doorbell"
}
```

```json
{
  "kind": "asset",
  "type": "sound",
  "id": "click"
}
```

## 7.3 BGM

静音：

```json
{
  "kind": "silent"
}
```

AA：

```json
{
  "kind": "aa",
  "id": 123
}
```

library：

```json
{
  "kind": "library",
  "type": "bgm",
  "id": "night_theme"
}
```

### v1 不支持

```text
BgmRef.kind=asset
BgmRef.kind=file
```

返回：

```text
E_UNSUPPORTED_BGM_SOURCE
```

AAPForge 不自动：

- hash BGM；
- 分配 BGM id；
- 猜测 BGM id；
- 将未知 BGM 降级为 silent。

---

## 7.4 兼容简写

允许：

```jsonc
"bg": "BG_GameDevRoom"
"se": "SE_Button_01"
"bgm": 999
```

Normalizer 单向展开为规范对象。

Skill、examples、fixture 默认使用完整对象语法。

---

# 8. Project 与 Cast

## 8.1 Project

```jsonc
{
  "project": {
    "name": "AAPForge_Example",
    "default_bg": {
      "kind": "aa",
      "name": "BG_Black"
    },
    "default_bgm": {
      "kind": "silent"
    }
  }
}
```

`name`：

- trim 后 1-80；
- 禁止 Windows 路径非法字符；
- 禁止 `.`;
- 禁止 `..`;
- 禁止 Windows 保留设备名。

---

## 8.2 Cast

Narrator：

```json
"旁白": {
  "narrator": true
}
```

普通角色：

```json
"桃井": {
  "portrait": true
}
```

可以显式 id：

```json
"桃井": {
  "id": "모모이",
  "portrait": true
}
```

具名无立绘 voice：

```json
"系统音": {
  "id": "SystemVoice",
  "name": "系统音",
  "portrait": false
}
```

### Cast 字段

`narrator`

```text
boolean
default=false
```

`id`

可选。

缺省时通过 cast key / name / alias 解析。

`name`

可选，人类显示名称。

`portrait`

```text
boolean
default=false
```

### 不再存在

v1 `cast` 不包含：

```text
faces
resource_kind
```

自定义角色本身不属于 v1。

所有 portrait 角色必须解析到 core index 中：

```text
portrait_verified=true
```

---

# 9. Scene 与 Line

## 9.1 Scene

```jsonc
{
  "id": "s1",
  "title": "开场",
  "bg": {
    "kind": "aa",
    "name": "BG_GameDevRoom"
  },
  "bgm": {
    "kind": "silent"
  },
  "transition": {
    "type": "fade",
    "duration": 500
  },
  "place": "千年科技学园",
  "lines": []
}
```

每一个 scene：

> 编译成一个 `ScriptNodeData`。

`scene.id`：

- 输入内唯一；
- 主要用于人类和 NodeName；
- v1 GUID 仍使用 ordinal 派生。

---

## 9.2 Line

每一个 line：

> **严格生成一条 AA `ScriptData`。**

主要字段：

```text
speaker
text
bg
bgm
transition
se
wait
place
face
slot
move
appear
action
emoticon
shape
highlight
stage_ops
```

`text=""` 合法。

空文本仍然：

- 生成 `ScriptData`；
- 生成 voice GUID。

---

# 10. 舞台操作

## 10.1 Slot

```text
0 = narrator / voice-only
1..5 = portrait
```

## 10.2 Speaker 快捷语法

```jsonc
{
  "speaker": "桃井",
  "text": "登场。",
  "face": "00",
  "slot": 3,
  "appear": {
    "type": "enter",
    "from": "right"
  }
}
```

Normalizer 可以转换成统一舞台 IR。

## 10.3 stage_ops

### enter

```json
{
  "op": "enter",
  "actor": "桃井",
  "slot": 3,
  "from": "right",
  "face": "00"
}
```

### exit

```json
{
  "op": "exit",
  "actor": "桃井",
  "slot": 3,
  "to": "left"
}
```

### move

```json
{
  "op": "move",
  "actor": "桃井",
  "from": 3,
  "to": 1
}
```

### set_face

```json
{
  "op": "set_face",
  "actor": "桃井",
  "slot": 1,
  "face": "03"
}
```

---

# 11. 舞台状态机

每个 scene 开始：

```text
stage = empty
face state = empty
highlight state = empty
```

BG/BGM 可以从 project defaults 初始化。

Portrait state 不跨 scene。

模型：

```text
before_state
    +
line directives
    ↓
row.characters[0..5]
    ↓
after_state
```

关键规则：

- `characters` 始终恰好 6 项。
- index 0 用于 narrator / voice-only。
- index 1-5 用于 portrait。
- 未发生操作的在场角色仍必须写入当前行。
- `enter` 本行出现，行末保留。
- `exit` 本行仍出现，行末删除。
- `move` 当前记录保留在 `from` 下标，`endingPos=to`。
- 下一行角色位于 `to`。
- `set_face` 当前行立即生效，并进入 after state。
- 已在台上的角色不得再次 enter。
- 不在台上的角色不得 move / exit / set_face。
- 两个角色不得同一行占同一个目标槽。
- 两角色不得直接 swap。
- swap 必须拆行或经过空 slot。

---

# 12. 背景语义

优先级：

```text
project.default_bg
        ↓
scene.bg
        ↓
line.bg
```

背景状态持续到下一次覆盖。

输出：

```text
bgFriendlyName = resolved background name
bgName = xxHash32(UTF-8 name, seed=0)
```

`scene.transition`：

只作用于 scene 第一条 line。

必须：

```text
scene.transition
→ scene.bg 显式存在
```

`line.transition`：

只作用当前 line。

必须：

```text
line.transition
→ line.bg 显式存在
```

否则：

```text
E_TRANSITION_WITHOUT_BG
```

---

# 13. BGM 语义

优先级：

```text
project.default_bgm
      ↓
scene.bgm
      ↓
line.bgm
```

持续到下一次覆盖。

### silent

```text
bgmId=999
```

### aa

必须存在：

```text
core.index.bgms
```

并：

```text
verified=true
```

输出该 integer id。

### library

必须存在：

```text
local_library.bgms
```

并且：

```text
verified=true
bgmId exists
file exists
```

build：

```text
复制文件
→ bgms/
→ manifest.BgmOverrides
→ build_report
```

---

# 14. Face / Action / Emoticon / Shape

`face`：

必须属于 core character faces。

`action`：

必须存在 `tables.actions`。

`emoticon`：

必须存在 `tables.emoticons`。

缺省无 emoticon：

```text
-1
```

`shape`：

必须存在 `tables.shapes`。

未知枚举：

```text
E_ENUM_UNKNOWN
```

未知 transition：

```text
E_TRANSITION_UNKNOWN
```

---

# 15. Highlight

值：

```text
0..5
```

重复值：

> 去重，并保留第一次出现顺序。

引用：

```text
1..5
```

时，该槽当前行必须存在 portrait。

缺省：

portrait speaker：

```text
[speaker slot]
```

narrator / voice-only：

```text
[]
```

非法：

```text
E_HIGHLIGHT_INVALID
```

---

# 16. 编译流程

这是全文唯一 compiler pipeline：

```text
读取源文件
    ↓
解析
    ↓
结构校验
    ↓
规范化
    ↓
加载 core data
    ↓
按需加载 local library
    ↓
引用解析
    ↓
语义校验
    ↓
生成 canonical IR
    ↓
生成 AAP IR
    ↓
AAP contract 校验
    ↓
生成临时工程
    ↓
最终产物校验
    ↓
安全发布
```

注意：

> `install` 不属于 compiler pipeline。

它是一个对**已成功 build 的产物**执行的独立后续操作。

因此逻辑关系是：

```text
build
  ↓ success
published artifact

可选：
install published artifact
```

而不是：

```text
compiler 内部顺便改 AA
```

---

# 17. Normalizer

Normalizer 只允许：

- 补文档规定默认值；
- `bg` string → BgRef；
- `se` string → SoundRef；
- `bgm=999` → `{kind:"silent"}`；
- face integer → canonical string；
- speaker shortcut → canonical stage operation IR；
- transition shorthand → canonical object。

Normalizer 禁止：

- 猜角色；
- 猜资源；
- 猜 kind；
- 猜 face；
- 自动替换不存在资源；
- 自动把 library 变 asset；
- 自动生成 BGM id；
- 自动更改用户 stage semantics。

---

# 18. Resolver

Resolver 只解析显式引用。

负责：

```text
cast key → core character
alias → core character
BgRef → background
SoundRef → sound
BgmRef → bgm
transition → integer
action → integer
emoticon → integer
shape → integer
appear → integer
```

不做：

```text
similarity
AI
pinyin
translation
heuristics
```

---

# 19. Semantic Validator

必须验证：

- speaker 已声明；
- cast 可唯一解析；
- portrait actor 被 core 验证；
- face 合法；
- slot 合法；
- move.from 与当前状态一致；
- move target 合法；
- enter target 为空；
- exit actor 当前存在；
- set_face actor 当前存在；
- 无直接 swap；
- 无 slot collision；
- transition 与 bg 绑定；
- highlight 合法；
- BGM 来源合法；
- library entry verified；
- asset 存在；
- stage state 可唯一执行。

无法唯一解释：

> 必须报错。

---

# 20. AAP IR

AAP writer 前的内部模型至少包含：

```text
ProjectData
EntryNodeData
ScriptNodeData
ExitNodeData
ScriptData
CharacterRecordData
```

AAP IR 只能由：

> 已通过 semantic validation 的 canonical IR

生成。

Writer 不负责业务级修复。

---

# 21. `.aap` Wire Contract

Writer 输出必须遵守当前 HaloCue 已验证 contract。

要求：

- Newtonsoft `$type` 固定；
- 字段顺序固定；
- UTF-8 no BOM；
- characters 固定 6 项；
- `selectionGroup=0`；
- GUID 规则固定；
- Node graph 合法；
- speaker slot 合法；
- highlighted slots 合法。

最小节点图：

```text
EntryNodeData
    ↓
ScriptNodeData
    ↓
ExitNodeData
```

多个 scene：

```text
Entry
 ↓
Scene 0
 ↓
Scene 1
 ↓
...
 ↓
Exit
```

Writer 输出禁止说明性别名，例如：

```text
GuidList
IntList
```

必须输出完整 Newtonsoft generic type。

原方案已经将字段顺序、完整 `$type`、6 个 `CharacterRecordData` 和节点图作为 wire contract；此约束继续保留。

---

# 22. GUID

AAPForge v1 使用当前 HaloCue 已验证规则。

Namespace：

```text
6ba7b812-9dad-11d1-80b4-00c04fd430c8
```

Entry：

```text
00000000-0000-0000-0000-000000000000
```

Scene：

```text
uuid5(namespace, "{project}/scene/{ordinal}")
```

Voice：

```text
uuid5(namespace, "{project}/voice/{global_line_ordinal}")
```

Exit：

```text
uuid5(namespace, "{project}/exit")
```

Exit embedded voice：

```text
uuid5(namespace, "{project}/exitvoice")
```

不使用随机 UUID。

AAPForge 不声明该算法属于 AA 协议硬要求。

这里只声明：

> 它是 AAPForge v1 当前采用的已验证输出契约。

---

# 23. Voices

每一条 line 生成 voice GUID。

生成：

```text
voices/voices.txt
```

v1：

- 不默认生成空 `.ogg`；
- 无真实 audio 时 `VoiceOverrides=[]`；
- voice audio injection 不是 compiler 主链要求。

---

# 24. Manifest

必须存在：

```json
{
  "CharacterOverrides": [],
  "VoiceOverrides": [],
  "PopupOverrides": [],
  "SoundOverrides": [],
  "BgOverrides": [],
  "BgmOverrides": []
}
```

v1：

```text
CharacterOverrides = []
PopupOverrides = []
```

`BgOverrides`：

只包含成功复制到工程目录的：

```text
library backgrounds
project asset backgrounds
```

`SoundOverrides`：

只包含：

```text
library sounds
project asset sounds
```

`BgmOverrides`：

只包含：

```text
verified library BGM
```

路径：

- Windows-style `\`；
- 工程内相对路径；
- 禁止 drive；
- 禁止 root；
- 禁止 `..`。

顺序：

> 按第一次引用顺序稳定输出。

BGM Volume：

> 取 local library BGM definition 的 volume。

---

# 25. 素材处理

## 25.1 Background

允许：

```text
.png
.jpg
.jpeg
```

必须验证基本文件头。

## 25.2 Sound

v1：

```text
.wav
```

必须验证：

```text
RIFF/WAVE
```

## 25.3 Library BGM

允许：

```text
.ogg
.wav
.mp3
```

基本 header 验证：

```text
OggS
RIFF/WAVE
ID3
MPEG frame
```

但：

> 文件格式合法 ≠ 已验证 AA 可以使用。

正式 build 仍要求：

```text
library entry verified=true
```

## 25.4 输出命名

统一：

```text
<domain>_<id>.<ext>
```

例如：

```text
library_night_theme.ogg
asset_click.wav
asset_night_room.png
```

相同 source 多次使用只复制一次。

相同 target 对应不同 content：

```text
E_ASSET_CONFLICT
```

---

# 26. Build Report

必须生成：

```text
build_report.json
```

建议结构：

```jsonc
{
  "aapforge_version": "0.1.0",
  "schema_version": "1.0",

  "core": {
    "index_schema_version": "1.0",
    "tables_schema_version": "1.0"
  },

  "copied_assets": [
    {
      "source_kind": "asset",
      "type": "background",
      "id": "night_room",
      "source": "assets/bgs/night_room.png",
      "target": "bgs\\asset_night_room.png"
    },

    {
      "source_kind": "library",
      "type": "bgm",
      "id": "night_theme",
      "source": "library/bgms/night_theme.ogg",
      "target": "bgms\\library_night_theme.ogg"
    }
  ],

  "library_bgms": {
    "night_theme": {
      "bgmId": 1071265322,
      "volume": 0.8,
      "path": "bgms\\library_night_theme.ogg"
    }
  }
}
```

`source_kind` 必须明确区分：

```text
library
asset
```

避免之前 example 中 library source 写成 `assets/...` 的歧义。

---

# 27. Build 输出安全

Build 永远先写临时目录。

例如：

```text
out/.aapforge-build-<id>/
```

流程：

```text
write temp
   ↓
AAP contract validate
   ↓
manifest validate
   ↓
asset validate
   ↓
build_report validate
   ↓
pair completeness validate
   ↓
publish
```

只有全部成功：

```text
ProjectName.aap
ProjectName/
```

才替换正式结果。

旧工程不得被失败 build 覆盖。

---

# 28. Install

Install 从 compiler 主链独立。

命令：

```bash
aapforge install out/ProjectName.aap
```

或者 convenience：

```bash
aapforge build story.aapforge.jsonc --install
```

但语义始终等价：

```text
build
 ↓ success
install published artifact
```

## 28.1 Install Preflight

任何写 AA data 之前先校验：

- `.aap` 存在；
- 同名工程目录存在；
- manifest 存在；
- build report 存在；
- output pair 完整；
- AA data 可写；
- 目标路径可确定；
- backup 能建立。

失败：

> 不执行任何 AA data 修改。

## 28.2 AA Running

默认：

```text
不杀进程
不自动重试
不交互
```

AA 未运行：

```text
允许继续
```

AA 正在运行：

默认：

```text
skip install
non-zero exit
```

显式：

```text
--allow-install-skip
```

可将此视为成功。

显式：

```text
--force-close-aa
```

才尝试关闭 AA。

## 28.3 Install Commit Model

AAPForge 不宣称拥有真正的 filesystem ACID transaction。

采用：

> staged replace + mandatory recovery attempt

流程：

```text
preflight
↓
backup old pair
↓
prepare new pair
↓
replace .aap
↓
replace project dir
↓
verify final pair
```

任一 replacement 后失败：

```text
必须尝试 rollback
```

rollback 成功：

```text
E_INSTALL_FAILED
```

rollback 本身失败：

```text
E_INSTALL_RECOVERY_FAILED
```

此时必须保留：

```text
recovery_report.json
```

并停止，不继续做任何自动“修复”。

---

# 29. CLI

v1 稳定公共 CLI：

```bash
aapforge validate story.aapforge.jsonc

aapforge build story.aapforge.jsonc

aapforge inspect out/ProjectName.aap

aapforge install out/ProjectName.aap
```

Convenience：

```bash
aapforge build story.aapforge.jsonc --install
```

### 通用参数

```text
--config <path>
--output-dir <path>
--core-index <path>
--tables <path>
--library <path>
--log-format text|jsonl
--quiet
```

Build：

```text
--allow-absolute-asset-paths
--install
```

Install：

```text
--aa-data
--force-close-aa
--allow-install-skip
--backup
--no-backup
```

### 不属于公共 CLI

删除：

```text
aapforge index export
```

Core data bootstrap / maintenance 属于 maintainer tooling。

例如：

```text
tools/bootstrap_from_halocue.py
tools/update_core_snapshot.py
tools/verify_core_data.py
```

它们不是 v1 用户稳定接口。

---

# 30. Config 优先级

```text
CLI explicit
>
selected config
>
built-in default
```

配置选择：

```text
--config
>
AAPFORGE_CONFIG
>
config/aapforge.local.json
>
defaults
```

---

# 31. 日志

默认 text。

例如：

```text
INFO  aapforge: loading input file=story.aapforge.jsonc
INFO  aapforge: schema ok
INFO  aapforge: core loaded
INFO  aapforge: semantic ok scenes=2 lines=42 cast=4
INFO  aapforge: aap contract ok
INFO  aapforge: published file=out/Example.aap
INFO  aapforge: done status=success
```

JSONL：

```jsonl
{"level":"INFO","event":"load_input","file":"story.aapforge.jsonc"}
{"level":"INFO","event":"schema_ok"}
{"level":"INFO","event":"semantic_ok","scenes":2,"lines":42}
{"level":"INFO","event":"publish_ok","project":"Example"}
{"level":"INFO","event":"done","status":"success"}
```

事件顺序必须稳定。

---

# 32. Diagnostics

统一格式：

```jsonc
{
  "code": "E_FACE_UNVERIFIED",
  "message": "face 07 is not verified for 桃井",
  "file": "story.aapforge.jsonc",
  "json_path": "$.scenes[0].lines[2].face",
  "line": 42,
  "column": 15,
  "blocking": true,
  "suggestion": "Use a face id present in the AAPForge core character index."
}
```

允许：

```text
code
message
file
json_path
line
column
blocking
suggestion
related
```

Suggestion：

- 可以告诉用户如何修；
- 不得猜测资源事实。

---

# 33. 稳定错误码

解析：

```text
E_JSON_PARSE
```

Schema：

```text
E_SCHEMA
E_SCHEMA_VERSION
```

Config：

```text
E_CONFIG_MISSING
E_CONFIG_INVALID
```

Cast：

```text
E_CAST_UNKNOWN
E_CAST_UNVERIFIED
E_CAST_AMBIGUOUS
E_CAST_DUPLICATE_ACTIVE
```

Resource：

```text
E_RESOURCE_MISSING
E_LIBRARY_MISSING
E_LIBRARY_UNVERIFIED
E_FACE_UNVERIFIED
E_BGM_UNVERIFIED
E_UNSUPPORTED_BGM_SOURCE
E_UNSUPPORTED_RESOURCE_SOURCE
E_ASSET_INVALID
E_ASSET_CONFLICT
```

Stage：

```text
E_STAGE_SLOT_OCCUPIED
E_STAGE_MOVE_MISMATCH
E_STAGE_ILLEGAL_SWAP
```

Semantics：

```text
E_TRANSITION_WITHOUT_BG
E_TRANSITION_UNKNOWN
E_ENUM_UNKNOWN
E_HIGHLIGHT_INVALID
```

Output：

```text
E_AAP_CONTRACT
E_OUTPUT_WRITE
```

Install：

```text
E_INSTALL_FAILED
E_INSTALL_RECOVERY_FAILED
E_AA_CLOSE_FAILED
```

Warning：

```text
W_INSTALL_SKIPPED_AA_RUNNING
```

原方案已经要求诊断具有稳定 code、JSONPath、行列和 blocking 信息；这一约束继续保留。

---

# 34. 退出码

建议：

```text
0 = requested operation success

1 = source/schema/semantic error

2 = resource/library/asset error

3 = AAP/output contract failure

4 = install failure, rollback successful

5 = AA close failure

6 = install skipped because AA running

7 = install recovery failure
```

`--allow-install-skip`：

允许：

```text
W_INSTALL_SKIPPED_AA_RUNNING
```

最终返回 0。

---

# 35. Inspect

```bash
aapforge inspect ProjectName.aap
```

只负责静态检查。

至少返回：

- project name；
- node 数；
- scene 数；
- ScriptData 数；
- GUID uniqueness；
- characters 数量；
- known `$type` contract；
- ConnectionsTo graph；
- manifest pairing；
- build report pairing。

Inspect 不运行 AA。

---

# 36. 工程结构

推荐：

```text
aapforge/
  pyproject.toml
  README.md

  config/
    aapforge.example.json

  resources/
    core/
      index.json
      tables.json

  src/aapforge/
    __init__.py
    cli.py
    config.py

    input/
      json_loader.py
      schema_validator.py
      normalizer.py
      diagnostics.py

    data/
      core.py
      library.py
      tables.py

    semantic/
      resolver.py
      validator.py
      stage_state.py

    ir/
      source.py
      canonical.py

    aap/
      models.py
      writer.py
      contract.py
      ids.py
      manifest.py
      voices.py

    project/
      builder.py
      layout.py
      assets.py
      report.py
      publisher.py

    install/
      aa_process.py
      backup.py
      installer.py
      recovery.py

  tools/
    bootstrap_from_halocue.py
    update_core_snapshot.py
    verify_core_data.py

  schema/
    aapforge.schema.json
    core-index.schema.json
    library.schema.json

  skill/
    aapforge/

  docs/
    aapforge_skill_spec.md

  examples/

  tests/
    fixtures/
    golden/
```

此结构是初始推荐，不属于外部稳定 API。

---

# 37. 模块职责

`json_loader`

> JSON / JSONC parse + source location。

`schema_validator`

> 单字段和结构约束。

`normalizer`

> 等价语法标准化。

`core.py`

> 加载 AAPForge 自带 AA facts。

`library.py`

> 加载 local external library。

`resolver`

> 显式引用解析。

`validator`

> 跨字段语义。

`stage_state`

> portrait 状态机。

`canonical IR`

> 已解析、无歧义的 AAPForge 语义。

`aap.models`

> AA wire-oriented model。

`aap.contract`

> AA contract validation。

`writer`

> 序列化。

`assets`

> 素材验证和复制。

`publisher`

> 临时输出 → 正式输出。

`installer`

> 已 build artifact → AA data。

---

# 38. Skill

AAPForge 提供：

```text
aapforge skill
```

它不是 compiler runtime。

职责：

- 解释 AAPForge spec；
- 帮用户生成 `.aapforge.jsonc`；
- 根据 diagnostic 修正 source；
- 对缺失的真实意图提问；
- 优先输出规范对象语法。

它不负责：

- 自动写剧情；
- 自动决定演出；
- 猜资源；
- 猜角色；
- 绕过 validator；
- 直接手工拼 `.aap`；
- 修改 core data；
- 修改 local library verification。

Skill 的原则：

> Agent 可以帮助用户表达意图，但 compiler 只接受确定语义。

---

# 39. Extension Policy

v1 不提前实现未来能力。

未来可能包括：

```text
custom characters
asset BGM
inline file resource
popup
bg_effect
camera
screen_text
node graph
branch
voice override
cross-scene stage inheritance
```

只有明确需求出现后再设计。

所有扩展必须满足：

1. 缺省时旧行为不变；
2. 有 schema；
3. 有 normalizer 规则；
4. 有 semantic validator；
5. 有 fixture；
6. 有 golden test；
7. 不支持时显式报错；
8. 不静默忽略。

---

# 40. 测试原则

测试分层。

## M0 — Contract/Data

验证：

```text
core index
tables
HaloCue-derived fixture
minimal golden .aap
```

目标：

> 锁定我们认为当前正确的 AA contract。

## M1 — Source Frontend

```text
JSON
JSONC
schema
normalizer
diagnostic location
```

验收：

```text
source → canonical input IR
```

稳定。

## M2 — Semantic Compiler

```text
resolver
cast
resource ref
stage state
face
highlight
transition
BGM
```

验收：

```text
canonical input → deterministic semantic IR
```

## M3 — AAP Backend

```text
AAP IR
GUID
writer
contract
golden
```

验收：

```text
AAP IR → valid .aap
```

此阶段必须人工让 AA 打开关键 golden 工程。

## M4 — Project Assets

增加：

```text
local library
project asset
manifest
copy
build report
```

## M5 — UX

增加：

```text
CLI
JSONL
diagnostics
skill
```

## M6 — Install

最后增加：

```text
backup
AA process detection
staged replace
rollback
recovery report
```

---

# 41. 实现顺序约束

在 M0-M3 完成前：

> 禁止为了 install、AA process、复杂素材管理打断 compiler 主链实现。

最先证明的只有：

```text
AAPForge Source
      ↓
Canonical IR
      ↓
Semantic IR
      ↓
AAP IR
      ↓
Writer
      ↓
AA accepts output
```

这是整个项目成立的核心。

---

# 42. Golden / Fixture 要求

至少需要以下成功样例：

```text
minimal narrator
single portrait enter
portrait face change
portrait move
portrait exit
multi actor
background transition
AA BGM
silent BGM
AA sound
multiple scenes
```

M4 再加入：

```text
library background
library sound
library BGM
project background
project sound
```

失败 fixture：

```text
invalid JSONC
unknown field
unknown character
ambiguous alias
unverified portrait
unknown face
occupied slot
bad move.from
illegal swap
transition without bg
unknown transition
unknown BGM
unverified library BGM
missing asset
invalid media
```

每个 fixture 应锁定：

```text
error code
json_path
exit code
```

---

# 43. AA 人工验收

自动测试全部通过以后，才允许进行 AA 人工验证。

人工验收单位应该尽可能小：

```text
背景
角色
face
enter
move
exit
BGM
sound
transition
multi-scene
```

如果某一步：

> 按已知 contract 应成功，但 AA 实际不接受，

立即：

```text
STOP
```

记录：

```text
source
canonical IR
AAP IR
.aap
manifest
build report
AA observed behavior
AAPForge version
core data version
```

不得继续把更多能力叠在未知基础上。

---

# 44. v1 最终能力边界

AAPForge v1 完成后应满足：

```text
JSON / JSONC source
        ↓
strict schema
        ↓
normalizer
        ↓
core/local resource resolver
        ↓
semantic validation
        ↓
stage state machine
        ↓
AAP IR
        ↓
contract validator
        ↓
.aap + project dir
```

并支持：

```text
AA background
library background
project background

AA sound
library sound
project sound

silent BGM
AA BGM
verified library BGM

AA character
face
enter
exit
move
highlight
action
emoticon
shape
transition
place
wait
```

v1 明确不支持：

```text
custom character
project-private BGM
inline file BGM
AI generation
automatic BGM id
automatic resource guessing
cross-scene portrait persistence
branches
node graph authoring
camera
popup
advanced effects
AA version compatibility
runtime HaloCue dependency
runtime AA resource scanning
```

---

# 45. 最终架构边界

整个系统最终保持以下关系：

```text
                 HaloCue
                    │
             maintainer bootstrap
                    │
                    ▼
             AAPForge Core Data
                    │
                    │
User Source ────────┼──────── Local Library
                    │
                    ▼
              AAPForge Compiler
                    │
                    ▼
            Published Artifact
              .aap + project/
                    │
                    │ optional
                    ▼
             AAPForge Installer
                    │
                    ▼
                   AA
```

关键边界：

```text
HaloCue ≠ runtime dependency

AA installation ≠ compiler dependency

Core Data ≠ Local Library

Local Library ≠ Project Assets

Build ≠ Install

Skill ≠ Compiler

Compiler ≠ AI Agent
```

这六条边界属于 v1 架构核心，不应在实现阶段被模糊化。

---

# 46. 完成定义

AAPForge v1 只有同时满足以下条件才算完成：

1. 同一合法 source 在相同数据下产生稳定 semantic output。
2. 所有非法或歧义输入 fail-fast。
3. `validate` / `build` 不依赖 HaloCue。
4. `validate` / `build` 不依赖真实 AA installation。
5. Core Data 与 Local Library 完全分离。
6. AAP writer 通过 contract tests。
7. Golden `.aap` 可以被目标 AA 正常加载。
8. 舞台状态 fixture 全部通过。
9. 所有素材输出与 manifest 一致。
10. build 不会用失败结果覆盖已存在工程。
11. install 失败后执行明确 recovery protocol。
12. recovery 无法完成时明确报错并停止。
13. agent skill 不拥有 compiler correctness decision。
14. 当前没有被验证的行为不得作为“最佳猜测”静默进入正式 build。

AAPForge v1 的核心目标不是覆盖 AA 的所有能力，而是建立一条：

> **边界清晰、语义确定、可以验证、失败时立即停止的 AA 工程编译链。**

在这条链被充分验证之前，不继续增加未来能力。