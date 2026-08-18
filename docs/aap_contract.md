# AAP Contract Freeze

This document records the M0 facts AAPForge freezes for v1. These are
AAPForge-owned copies of verified rules; normal runtime must not import
HaloCue.

| Contract | Source | Status |
| --- | --- | --- |
| Newtonsoft `$type` strings for ProjectData, NodeData lists, ScriptData lists, CharacterRecordData lists, Guid lists, Int32 lists | `D:\文档\GitHub\HaloCue\script2aap.py`, constants `T_PROJ`, `T_NODES`, `T_ENTRY`, `T_SNODE`, `T_EXIT`, `T_SLIST`, `T_SCRIPT`, `T_CLIST`, `T_CHAR`, `T_GLIST`, `T_ILIST` | verified |
| Project wrapper shape and Entry -> ScriptNode -> Exit graph | `D:\文档\GitHub\HaloCue\script2aap.py`, `wrap_project` | verified |
| Entry GUID is all zeroes | `D:\文档\GitHub\HaloCue\script2aap.py`, `wrap_project` | verified |
| Scene GUID rule | `D:\文档\GitHub\HaloCue\script2aap.py`, `uuid.uuid5(NS, f"{project}/scene/{i}")` | AAPForge v1 chosen verified rule |
| Voice GUID rule | `D:\文档\GitHub\HaloCue\script2aap.py`, `voice_guid(project, n)` | AAPForge v1 chosen verified rule |
| Exit and exit voice GUID rules | `D:\文档\GitHub\HaloCue\script2aap.py`, `wrap_project` | AAPForge v1 chosen verified rule |
| ScriptData field order | `D:\文档\GitHub\HaloCue\verify.py`, `SCRIPT_KEYS`; `script2aap.py`, script dict construction | verified |
| CharacterRecordData field order | `D:\文档\GitHub\HaloCue\verify.py`, `CHAR_KEYS`; `script2aap.py`, `blank_char` | verified |
| Character slots = 6 | `D:\文档\GitHub\HaloCue\script2aap.py`, `SLOTS = 6`; `verify.py`, slot validator | verified |
| Narrator/no-portrait speaker slot = 0 | `D:\文档\GitHub\HaloCue\stage.py` position model comments; `script2aap.py`, narrator branch and speaker fallback | verified |
| `selectionGroup = 0` | `D:\文档\GitHub\HaloCue\script2aap.py`, ScriptData construction; `verify.py`, fixture checks | verified |
| Default background `BG_Black` | `D:\文档\GitHub\HaloCue\script2aap.py`, `cfg.get("default_bg", "BG_Black")` | verified as default input to writer |
| Default BGM `999` | `D:\文档\GitHub\HaloCue\script2aap.py`, `cfg.get("default_bgm", 999)` | verified as default/silent writer value |
| Background hash | `D:\文档\GitHub\HaloCue\tables.py`, `xxh32` and `bg_id`; module provenance says `xxHash32(utf8, seed=0)` | verified |
| Transition mapping | `D:\文档\GitHub\HaloCue\tables.py`, `TRANSITION` | verified, single-source extraction noted by HaloCue |
| Background effect mapping | `D:\文档\GitHub\HaloCue\tables.py`, `BGEFFECT` | verified |
| Emoticon mapping | `D:\文档\GitHub\HaloCue\build_index.py`, `EMOTICON` | verified by HaloCue `.aap`/`.aas` pairing note |
| Action mapping | `D:\文档\GitHub\HaloCue\build_index.py`, `ACTION`; `script2aap.py`, `ACTION_IDS` | verified |
| Appear mapping | `D:\文档\GitHub\HaloCue\build_index.py`, `APPEAR`; `D:\文档\GitHub\HaloCue\stage.py`, `APPEAR`/`DISAPPEAR` | verified |
| Shape override mapping | `D:\文档\GitHub\HaloCue\build_index.py`, `SHAPE`; `script2aap.py`, `SHAPE` and `SHAPE_IDS` | verified |

## Unresolved In M0

- Full AA background, sound, BGM, and character resource catalogs are not
  frozen. This workspace has no authoritative AA resource directory or reviewed
  HaloCue export to import.
- `resources/core/index.json` therefore contains only `BG_Black`, because it is
  directly evidenced as HaloCue's default writer background. It contains no
  character, sound, or AA BGM catalog entries.
- BGM value `999` is frozen as the default/silent writer value in the golden
  contract, not as a `resources/core/index.json` BGM resource.
