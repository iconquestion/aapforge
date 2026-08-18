from __future__ import annotations

import argparse
import base64
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aapforge.data.aa_official import build_official_character_data


class CharacterBundleNotFoundError(FileNotFoundError):
    pass


class CharacterBundleAmbiguousError(RuntimeError):
    pass


# HaloCue 已验证的 ScenarioCharacterNameExcel 文本解密 key。
CHARACTER_NAME_KEY = bytes.fromhex("268bd50b5cce8633")
CHARACTER_NAME_UINT_KEY = int.from_bytes(
    CHARACTER_NAME_KEY[:4], "little"
)


# ============================================================
# 基础二进制读取
# ============================================================

def u16(blob: bytes, offset: int) -> int:
    return struct.unpack_from("<H", blob, offset)[0]


def u32(blob: bytes, offset: int) -> int:
    return struct.unpack_from("<I", blob, offset)[0]


def i32(blob: bytes, offset: int) -> int:
    return struct.unpack_from("<i", blob, offset)[0]


def table_fields(blob: bytes, table_offset: int) -> list[int]:
    vtable = table_offset - i32(blob, table_offset)
    count = (u16(blob, vtable) - 4) // 2

    return [
        u16(blob, vtable + 4 + index * 2)
        for index in range(count)
    ]


# ============================================================
# AA FlatData 字符串解密
# ============================================================

def decrypt_ba_text(token: str) -> str:
    encrypted = base64.b64decode(token)

    plain = bytes(
        value ^ CHARACTER_NAME_KEY[index % len(CHARACTER_NAME_KEY)]
        for index, value in enumerate(encrypted)
    )

    return plain.decode("utf-16-le")


def encrypted_string(blob: bytes, offset: int) -> str:
    string_offset = offset + u32(blob, offset)
    size = u32(blob, string_offset)

    token = blob[
        string_offset + 4:
        string_offset + 4 + size
    ].decode("ascii")

    return decrypt_ba_text(token)


# ============================================================
# catalog.json 解析
# ============================================================

def catalog_entries_raw(raw: bytes) -> dict[int, tuple[int, ...]]:
    if len(raw) < 4 or (len(raw) - 4) % 28 != 0:
        raise ValueError("非法 Addressables m_EntryDataString")

    count = (len(raw) - 4) // 28

    rows = (
        struct.unpack_from("<7i", raw, 4 + index * 28)
        for index in range(count)
    )

    return {row[0]: row for row in rows}


def bundle_options_raw(raw: bytes, offset: int) -> dict[str, Any]:
    json_start = raw.index(b"{\x00", offset)

    size = u32(raw, json_start - 4)

    data = raw[
        json_start:
        json_start + size
    ].decode("utf-16-le")

    return json.loads(data)


def locate_character_bundle(
    catalog_path: Path,
    cache_root: Path,
) -> tuple[Path, str, str, str]:
    """
    从 Addressables catalog 中找到
    scenariocharacternameexceltable.bytes
    所属 bundle。
    """

    catalog = json.loads(
        catalog_path.read_text(encoding="utf-8-sig")
    )

    internal_ids = catalog["m_InternalIds"]

    entries = catalog_entries_raw(
        base64.b64decode(catalog["m_EntryDataString"])
    )

    extra_data = base64.b64decode(
        catalog["m_ExtraDataString"]
    )

    matches: list[tuple[Path, str, str, str]] = []

    for internal_index, internal_id in enumerate(internal_ids):

        if not str(internal_id).casefold().endswith(
            "scenariocharacternameexceltable.bytes"
        ):
            continue

        if internal_index not in entries:
            continue

        entry = entries[internal_index]

        bundle_index = entry[2]

        if bundle_index >= 0:
            if bundle_index not in entries:
                continue
            bundle_entry = entries[bundle_index]

        elif str(internal_id).casefold().endswith(".bundle"):
            bundle_entry = entry

        else:
            continue

        options = bundle_options_raw(
            extra_data,
            bundle_entry[4],
        )

        bundle_name = str(options["m_BundleName"])
        catalog_hash = str(options["m_Hash"])

        bundle_root = cache_root / bundle_name

        exact = (
            bundle_root
            / catalog_hash
            / "__data"
        )

        if exact.is_file():
            matches.append(
                (exact, bundle_name, catalog_hash, catalog_hash)
            )
            continue

        # 某些缓存目录 hash 与 catalog 当前 hash 不完全同步。
        # 只有唯一候选时才接受，绝不猜多个候选中的一个。
        candidates = sorted(
            bundle_root.glob("*/__data")
        ) if bundle_root.is_dir() else []

        candidates = [
            path
            for path in candidates
            if path.is_file()
        ]

        if len(candidates) > 1:
            paths = "\n".join(f"  {path}" for path in candidates)
            raise CharacterBundleAmbiguousError(
                "ScenarioCharacterNameExcel bundle 存在多个缓存 hash 候选，"
                "拒绝自动选择：\n"
                + paths
            )

        if len(candidates) == 1:
            matches.append(
                (
                    candidates[0],
                    bundle_name,
                    catalog_hash,
                    candidates[0].parent.name,
                )
            )

    if not matches:
        raise CharacterBundleNotFoundError(
            "无法找到 ScenarioCharacterNameExcel bundle。\n"
            f"catalog: {catalog_path}\n"
            f"cache:   {cache_root}"
        )

    # 同一个表不能存在多个不同候选。
    unique = {
        str(path.resolve()).casefold(): (path, name, catalog_hash, cache_hash)
        for path, name, catalog_hash, cache_hash in matches
    }

    if len(unique) != 1:
        paths = "\n".join(
            f"  {item[0]}"
            for item in unique.values()
        )
        raise CharacterBundleAmbiguousError(
            "发现多个 ScenarioCharacterNameExcel bundle，"
            "拒绝自动选择：\n"
            + paths
        )

    return next(iter(unique.values()))


# ============================================================
# Unity bundle 读取
# ============================================================

def read_text_asset(
    bundle_path: Path,
    asset_name: str,
) -> bytes:
    try:
        import UnityPy
    except ImportError:
        raise SystemExit(
            "缺少 UnityPy。\n"
            "请运行：\n"
            "  python -m pip install UnityPy"
        )

    env = UnityPy.load(str(bundle_path))

    wanted = asset_name.casefold()

    for obj in env.objects:

        if obj.type.name != "TextAsset":
            continue

        asset = obj.read()

        name = str(
            getattr(asset, "m_Name", "")
        ).casefold()

        if name != wanted:
            continue

        script = getattr(asset, "m_Script", None)

        if isinstance(script, bytes):
            return script

        if isinstance(script, str):
            return script.encode(
                "utf-8",
                errors="surrogateescape",
            )

        raise TypeError(
            f"TextAsset {asset_name} 的 m_Script 类型未知："
            f"{type(script)!r}"
        )

    raise LookupError(
        f"bundle 中找不到 TextAsset: {asset_name}"
    )


# ============================================================
# ScenarioCharacterNameExcel 解码
# ============================================================

def decode_character_table(blob: bytes) -> list[dict[str, Any]]:
    root = u32(blob, 0)

    root_fields = table_fields(blob, root)

    if not root_fields or root_fields[0] == 0:
        raise ValueError(
            "ScenarioCharacterNameExcel root 无有效 vector"
        )

    vector_field = root + root_fields[0]
    vector = vector_field + u32(blob, vector_field)

    count = u32(blob, vector)

    rows: list[dict[str, Any]] = []

    for index in range(count):

        element = vector + 4 + index * 4
        table = element + u32(blob, element)

        fields = table_fields(blob, table)

        if len(fields) < 15:
            raise ValueError(
                f"ScenarioCharacterNameExcel 第 {index} 行字段数不足"
            )

        if not all(fields[slot] for slot in range(15)):
            raise ValueError(
                f"ScenarioCharacterNameExcel 第 {index} 行缺少已验证字段"
            )

        def text(slot: int) -> str:
            return encrypted_string(
                blob,
                table + fields[slot],
            ).strip()

        try:
            # HaloCue 已验证：
            #
            # 2  = NameKR，AAP native identifier
            # 8  = NameTW，AA UI 中显示名称
            # 9  = Club
            # 13 = Spine path
            # 14 = Avatar path
            identifier = text(2)
            name = text(8)

            if not identifier or not name:
                continue

            club = text(9)
            spine = text(13)
            avatar = text(14)

            native_key = (
                u32(blob, table + fields[0])
                ^ CHARACTER_NAME_UINT_KEY
            )

            shape = (
                u32(blob, table + fields[1])
                ^ CHARACTER_NAME_UINT_KEY
            )

        except (
            UnicodeDecodeError,
            ValueError,
            IndexError,
            struct.error,
        ) as exc:
            raise ValueError(
                f"解析角色表第 {index} 行失败"
            ) from exc

        rows.append(
            {
                "id": identifier,
                "name": name,
                "club": club,
                "spine": spine,
                "avatar": avatar,
                "native_key": native_key,
                "shape": shape,

                # 不扫描历史 AAP，因此不能声称知道 face。
                "faces": [],
            }
        )

    return rows


# ============================================================
# AA 路径处理
# ============================================================

def normalize_aa_root(value: str) -> Path:
    path = Path(value).expanduser().resolve()

    if path.is_file():
        if path.name.casefold() != "azurearchive.exe":
            raise ValueError(
                f"给定文件不是 AzureArchive.exe：{path}"
            )
        path = path.parent

    exe = path / "AzureArchive.exe"

    if not exe.is_file():
        raise FileNotFoundError(
            f"找不到 AzureArchive.exe：{exe}"
        )

    return path


def locate_catalog(aa_root: Path) -> Path:
    catalog = (
        aa_root
        / "AzureArchive_Data"
        / "StreamingAssets"
        / "aa"
        / "catalog.json"
    )

    if not catalog.is_file():
        raise FileNotFoundError(
            f"找不到 catalog.json：{catalog}"
        )

    return catalog


def discover_cache_candidates(aa_root: Path) -> list[Path]:
    """
    尽量只用路径信息定位 AA 官方资源缓存。

    注意：
    这里不会扫描 projects / overrides / .aap。
    """

    candidates: list[Path] = []

    # 常见：安装目录附近。
    candidates.extend(
        [
            aa_root / "资源文件",
            aa_root.parent / "资源文件",
        ]
    )

    # AA 默认设置目录。
    local_low = (
        Path.home()
        / "AppData"
        / "LocalLow"
        / "foxxlight"
        / "AzureArchive"
    )

    # Unity Addressables 标准缓存目录。
    unity_cache = (
        Path.home()
        / "AppData"
        / "LocalLow"
        / "Unity"
        / "foxxlight_AzureArchive"
    )

    if unity_cache.is_dir():
        candidates.append(unity_cache)

    settings_path = (
        local_low
        / "data"
        / "settings"
        / "user_settings.json"
    )

    if settings_path.is_file():
        try:
            settings = json.loads(
                settings_path.read_text(
                    encoding="utf-8-sig"
                )
            )

            cache_path = str(
                settings.get("cachePath") or ""
            ).strip()

            if cache_path:
                candidates.insert(
                    0,
                    Path(cache_path).expanduser(),
                )

            workspace = str(
                settings.get("workspacePath") or ""
            ).strip()

            if workspace:
                workspace_path = (
                    Path(workspace)
                    .expanduser()
                    .resolve()
                )

                candidates.append(
                    workspace_path.parent
                    / "资源文件"
                )

        except Exception:
            # cache 自动发现失败不影响显式 --cache。
            pass

    seen: set[str] = set()

    discovered: list[Path] = []
    for candidate in candidates:
        try:
            candidate = candidate.resolve()
        except OSError:
            continue

        key = str(candidate).casefold()

        if key in seen:
            continue

        seen.add(key)

        if not candidate.is_dir():
            continue

        # 简单验证 AA Addressables cache：
        # <bundle>/<hash>/__data
        found_data = False
        for outer in candidate.iterdir():
            if not outer.is_dir():
                continue

            try:
                for inner in outer.iterdir():
                    data = inner / "__data"

                    if data.is_file():
                        found_data = True
                        break

            except OSError:
                continue
            if found_data:
                discovered.append(candidate)
                break

    return sorted(discovered, key=lambda path: str(path).casefold())


def resolve_character_bundle_from_discovered_caches(
    catalog_path: Path,
    candidates: list[Path],
    *,
    locator=locate_character_bundle,
) -> tuple[Path, Path, str, str, str]:
    """用目标角色表验证自动发现的缓存候选。"""

    valid: list[tuple[Path, Path, str, str, str]] = []
    for cache_root in candidates:
        try:
            bundle_path, bundle_name, catalog_hash, cache_hash = locator(
                catalog_path,
                cache_root,
            )
        except CharacterBundleNotFoundError:
            continue
        valid.append((cache_root, bundle_path, bundle_name, catalog_hash, cache_hash))

    if not candidates:
        raise CharacterBundleNotFoundError("无法发现 AA Addressables 缓存")
    if not valid:
        raise CharacterBundleNotFoundError(
            "发现了一些缓存候选，但没有任何一个能提供 ScenarioCharacterNameExcel"
        )
    if len(valid) > 1:
        paths = "\n".join(f"  {item[0]}" for item in valid)
        raise CharacterBundleAmbiguousError(
            "多个缓存都能提供 ScenarioCharacterNameExcel，"
            "请显式指定 --cache：\n"
            + paths
        )
    return valid[0]


def resolve_character_bundle_for_cli(
    *,
    catalog_path: Path,
    aa_root: Path,
    explicit_cache: Path | None,
    locator=locate_character_bundle,
    discoverer=discover_cache_candidates,
) -> tuple[Path, Path, str, str, str]:
    if explicit_cache is not None:
        bundle_path, bundle_name, catalog_hash, cache_hash = locator(
            catalog_path,
            explicit_cache,
        )
        return explicit_cache, bundle_path, bundle_name, catalog_hash, cache_hash
    return resolve_character_bundle_from_discovered_caches(
        catalog_path,
        discoverer(aa_root),
        locator=locator,
    )


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


# ============================================================
# CLI
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "只读提取 AzureArchive 官方角色 FlatData，"
            "不扫描用户项目、override 或历史 .aap。"
        )
    )

    parser.add_argument(
        "aa",
        help=(
            "AzureArchive 安装目录，"
            "或 AzureArchive.exe 路径"
        ),
    )

    parser.add_argument(
        "--cache",
        help=(
            "AA 官方 Addressables 资源缓存目录。"
            "不给时尝试自动探测。"
        ),
    )

    parser.add_argument(
        "--output",
        "--out",
        dest="output",
        default=ROOT / "resources/generated/aa_official_characters.json",
        help=(
            "输出 JSON 路径 "
            "(默认 resources/generated/aa_official_characters.json)"
        ),
    )

    args = parser.parse_args()

    aa_root = normalize_aa_root(args.aa)

    catalog_path = locate_catalog(aa_root)

    if args.cache:
        cache_root = (
            Path(args.cache)
            .expanduser()
            .resolve()
        )

        if not cache_root.is_dir():
            raise SystemExit(
                f"--cache 目录不存在：{cache_root}"
            )
        explicit_cache = cache_root

    else:
        explicit_cache = None

    cache_root, bundle_path, bundle_name, catalog_hash, cache_hash = (
        resolve_character_bundle_for_cli(
            catalog_path=catalog_path,
            aa_root=aa_root,
            explicit_cache=explicit_cache,
        )
    )

    print(f"AA 安装目录：{aa_root}")
    print(f"catalog：     {catalog_path}")
    print(f"资源缓存：    {cache_root}")

    print(f"角色表 bundle：{bundle_path}")

    blob = read_text_asset(
        bundle_path,
        "scenariocharacternameexceltable",
    )

    rows = decode_character_table(blob)

    for row in rows:
        if row["id"] == "???":
            print(row)

    if not rows:
        raise SystemExit(
            "ScenarioCharacterNameExcel "
            "解析结果为空，停止。"
        )

    output = build_official_character_data(
        rows=rows,
        source={
            "catalog_sha256": sha256_file(catalog_path),
            "bundle_name": bundle_name,
            "bundle_catalog_hash": catalog_hash,
            "bundle_cache_hash": cache_hash,
            "bundle_sha256": sha256_file(bundle_path),
        },
    )

    out_path = (
        Path(args.output)
        .expanduser()
        .resolve()
    )

    out_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    out_path.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    stats = output["stats"]

    print()
    print("提取完成")
    print(
        f"官方角色：    {stats['characters']}"
    )
    print(
        f"官方记录：    {stats['records']}"
    )
    print(
        f"显示名称：    {stats['names']}"
    )
    print(
        "同名歧义：    "
        f"{stats['ambiguous_names']}"
    )
    print(f"输出：        {out_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130)
