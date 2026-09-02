"""Map OG save FormID prefixes onto Remastered plugins.txt load order."""

from __future__ import annotations

from pathlib import Path

PKG_DATA = Path(__file__).resolve().parent.parent / "data" / "remastered_plugins.txt"

SKIP_PREFIXES = ("altar",)


def load_plugins_txt(path: str | Path | None = None) -> list[str]:
    src = Path(path) if path else PKG_DATA
    names: list[str] = []
    for raw in src.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        if line.startswith("*"):
            line = line[1:]
        names.append(line)
    if not names:
        raise ValueError(f"no plugins listed in {src}")
    return names


def _norm(name: str) -> str:
    return name.strip().lower()


def build_prefix_map(save_masters: list[str], remaster_plugins: list[str]) -> dict[int, int]:
    """Old load-order index (high byte) -> Remastered load-order index.

    Masters that do not exist in Remastered (UOP, third-party mods) are omitted
    so their FormIDs are skipped rather than colliding with DLC slots.
    """
    rem = {_norm(n): i for i, n in enumerate(remaster_plugins)}
    mapping: dict[int, int] = {}
    for old_idx, master in enumerate(save_masters):
        key = _norm(master)
        if key.startswith(SKIP_PREFIXES):
            continue
        if key in rem:
            mapping[old_idx] = rem[key]
    return mapping


def unmapped_masters(save_masters: list[str], remaster_plugins: list[str]) -> list[str]:
    rem = {_norm(n) for n in remaster_plugins}
    skipped = []
    for master in save_masters:
        key = _norm(master)
        if key.startswith(SKIP_PREFIXES):
            continue
        if key not in rem:
            skipped.append(master)
    return skipped


def remap_form_id(form_id: int, prefix_map: dict[int, int]) -> int | None:
    """Return remapped FormID, or None if created (0xFF) or from an unknown plugin."""
    if form_id >= 0xFF000000:
        return None
    old_prefix = (form_id >> 24) & 0xFF
    if old_prefix not in prefix_map:
        return None
    object_index = form_id & 0x00FFFFFF
    new_prefix = prefix_map[old_prefix]
    return (new_prefix << 24) | object_index


def hex_formid(form_id: int) -> str:
    return f"{form_id:08X}"


def shiverings_isles_merged(save_masters: list[str]) -> bool:
    return not any(_norm(m) == "dlcshiveringisles.esp" for m in save_masters)
