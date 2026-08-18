"""Background hash contract frozen from HaloCue's verified implementation."""

from __future__ import annotations

_P1, _P2, _P3, _P4, _P5 = 2654435761, 2246822519, 3266489917, 668265263, 374761393
_MASK = 0xFFFFFFFF


def _rotl(value: int, shift: int) -> int:
    return ((value << shift) | (value >> (32 - shift))) & _MASK


def xxh32(data: str | bytes, seed: int = 0) -> int:
    if isinstance(data, str):
        data = data.encode("utf-8")
    size = len(data)
    offset = 0
    if size >= 16:
        state = [
            (seed + _P1 + _P2) & _MASK,
            (seed + _P2) & _MASK,
            seed & _MASK,
            (seed - _P1) & _MASK,
        ]
        while offset <= size - 16:
            for index in range(4):
                chunk = int.from_bytes(data[offset : offset + 4], "little")
                offset += 4
                mixed = (state[index] + chunk * _P2) & _MASK
                state[index] = (_rotl(mixed, 13) * _P1) & _MASK
        result = (
            _rotl(state[0], 1)
            + _rotl(state[1], 7)
            + _rotl(state[2], 12)
            + _rotl(state[3], 18)
        ) & _MASK
    else:
        result = (seed + _P5) & _MASK
    result = (result + size) & _MASK
    while offset <= size - 4:
        result = (result + int.from_bytes(data[offset : offset + 4], "little") * _P3) & _MASK
        result = (_rotl(result, 17) * _P4) & _MASK
        offset += 4
    while offset < size:
        result = (result + data[offset] * _P5) & _MASK
        result = (_rotl(result, 11) * _P1) & _MASK
        offset += 1
    result ^= result >> 15
    result = (result * _P2) & _MASK
    result ^= result >> 13
    result = (result * _P3) & _MASK
    result ^= result >> 16
    return result


def background_hash(friendly_name: str) -> int:
    return xxh32(friendly_name, seed=0)
