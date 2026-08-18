"""Maintainer-only notes for HaloCue bootstrap.

M0 data was manually frozen from explicit HaloCue modules and reviewed into
AAPForge-owned JSON. This placeholder intentionally does not import HaloCue at
runtime and does not scan local AA installs or user resource directories.
"""

from __future__ import annotations


def main() -> int:
    print("No automatic bootstrap is defined for M0; review docs/aap_contract.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
