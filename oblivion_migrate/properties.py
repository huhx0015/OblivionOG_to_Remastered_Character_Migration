"""Oblivion ESS extra-data property flags (inventory + ACHR/REFR).

Sizes follow UESP Save File Format/Properties and OSE (grahame-student/OSE).
"""

from __future__ import annotations

from .binary import BinaryReader

# Fixed payload sizes (bytes after the 1-byte flag). None = variable.
FIXED_PROPERTY_SIZES: dict[int, int] = {
    0x11: 4,   # worldspace iref
    0x1B: 0,   # equipped (weapons/armor/clothes)
    0x1C: 0,   # equipped (rings/amulets)
    0x1E: 20,  # marker heading
    0x1F: 14,  # AI package
    0x20: 63,  # trespass
    0x22: 4,   # iref
    0x27: 4,   # owner
    0x28: 4,   # global
    0x29: 4,   # faction rank
    0x2A: 2,   # affected item count
    0x2B: 4,   # item health (float)
    0x2D: 4,   # time
    0x2E: 4,   # enchantment points
    0x2F: 1,   # soul
    0x31: 6,   # lock
    0x32: 28,  # teleport
    0x33: 1,   # map marker
    0x35: 0,   # leveled creature
    0x36: 5,
    0x37: 4,   # scale
    0x39: 12,
    0x3D: 4,   # crime gold
    0x3E: 16,  # oblivion entry
    0x41: 4,
    0x48: 4,   # poison
    0x4F: 4,
    0x52: 4,   # investment gold
    0x53: 4,
    0x55: 1,   # shortcut key
    0x5A: 1,   # essential
    0x5C: 4,
}

EQUIPPED_FLAGS = {0x1B, 0x1C}


class PropertyParseError(ValueError):
    pass


def skip_script_property(r: BinaryReader) -> None:
    r.u32()  # script iref
    var_num = r.u16()
    if var_num > 4096:
        raise PropertyParseError(f"script varNum {var_num} looks corrupt")
    for _ in range(var_num):
        r.u16()  # index
        var_type = r.u16()
        if var_type == 0xF000:
            r.u32()
        else:
            r.f64()
    r.u8()  # trailing unknown


def skip_one_property(r: BinaryReader) -> int:
    """Read one property flag+payload. Returns the flag."""
    flag = r.u8()
    if flag == 0x12:
        skip_script_property(r)
        return flag
    if flag == 0x21:
        count = r.u16()
        r.skip(count * 5)
        return flag
    if flag == 0x23:
        count = r.u16()
        r.skip(count * 4)
        return flag
    if flag == 0x3A:
        r.u32()
        count = r.u16()
        r.skip(count)  # OSE Block(60) is a fixed 61-byte blob in some files; treat count as bytes
        return flag
    if flag == 0x4A:
        n = r.u8()
        r.skip(n)
        return flag
    if flag == 0x4B:
        # Movement extra: length-prefixed blob (ushort).
        n = r.u16()
        r.skip(n)
        return flag
    if flag == 0x4E:
        count = r.u16()
        r.skip(10 if count == 0 else count)
        return flag
    if flag == 0x59:
        n = r.u8()
        r.skip(n)
        conv = r.u16()
        r.skip(conv * 13)
        return flag
    if flag in FIXED_PROPERTY_SIZES:
        r.skip(FIXED_PROPERTY_SIZES[flag])
        return flag
    raise PropertyParseError(f"unknown property flag 0x{flag:02X} at {r.pos - 1}")


def skip_property_list(r: BinaryReader, count: int) -> list[int]:
    flags: list[int] = []
    if count < 0 or count > 4096:
        raise PropertyParseError(f"property count {count} looks corrupt")
    for _ in range(count):
        flags.append(skip_one_property(r))
    return flags
