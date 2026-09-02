"""Inspect an Oblivion Remastered .sav (Unreal GVAS) for TES4 leftovers."""

from __future__ import annotations

import zlib
from pathlib import Path

NEEDLES = (
    b"TES4SAVEGAME",
    b"GVAS",
    b"bIsESS",
    b"BoolProperty",
    b"Altar",
    b"SaveGame",
)

ZLIB_HEADERS = (b"\x78\x01", b"\x78\x9c", b"\x78\xda")


def inspect_sav(path: str | Path) -> str:
    data = Path(path).read_bytes()
    magic = data[:4]
    lines = [
        f"file: {path}",
        f"size: {len(data)} bytes",
        f"magic: {magic!r} ({magic.decode('latin-1', errors='replace')})",
    ]
    if magic == b"GVAS":
        lines.append("format: Unreal Engine GVAS (Oblivion Remastered wrapper)")
    elif magic == b"TES4":
        lines.append("format: looks like a TES4 ESS, not a Remastered .sav")
    else:
        lines.append("format: unknown")

    for needle in NEEDLES:
        idx = data.find(needle)
        if idx < 0:
            lines.append(f"  {needle.decode('latin-1')}: not found")
        else:
            lines.append(f"  {needle.decode('latin-1')}: FOUND at offset {idx}")

    lines.extend(_scan_compression(data))

    # Printable strings in the first 8 KB (class names).
    strings: list[str] = []
    cur = bytearray()
    for b in data[:8192]:
        if 32 <= b < 127:
            cur.append(b)
        else:
            if len(cur) >= 6:
                strings.append(cur.decode("ascii"))
            cur.clear()
    if strings:
        lines.append("header strings:")
        for s in strings[:40]:
            lines.append(f"  {s}")
    lines.append("")
    return "\n".join(lines)


def _scan_compression(data: bytes) -> list[str]:
    """Look for zlib streams that might hide a nested TES4SAVEGAME blob."""
    lines: list[str] = []
    tes4_nested = False
    for hdr in ZLIB_HEADERS:
        hits = 0
        start = 0
        while hits < 8:
            idx = data.find(hdr, start)
            if idx < 0:
                break
            hits += 1
            start = idx + 1
            chunk = data[idx : idx + 1_048_576]
            try:
                out = zlib.decompress(chunk)
            except zlib.error:
                continue
            if b"TES4SAVEGAME" in out:
                tes4_nested = True
                lines.append(f"  nested TES4SAVEGAME inside zlib stream at offset {idx}")
        if hits:
            lines.append(f"  zlib-like {hdr.hex()} candidates: {hits}")
    gzip_at = data.find(b"\x1f\x8b")
    if gzip_at >= 0:
        lines.append(f"  gzip header: FOUND at offset {gzip_at}")
    if tes4_nested:
        lines.append("  uncompressed TES4 blob is nested inside compressed data")
    else:
        lines.append("  no TES4SAVEGAME inside sampled zlib streams")
    return lines
