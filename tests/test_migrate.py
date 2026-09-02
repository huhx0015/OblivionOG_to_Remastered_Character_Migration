from __future__ import annotations

import struct
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from oblivion_migrate.ess_parser import (
    ESS_MAGIC,
    CharacterDump,
    EssError,
    FactionRank,
    InventoryItem,
    QuestStage,
    _fill_derived_pools,
    parse_ess,
)
from oblivion_migrate.formid_map import build_prefix_map, hex_formid, load_plugins_txt, remap_form_id
from oblivion_migrate.console_export import emit_console_script
from oblivion_migrate.sav_inspect import inspect_sav


def _u8(n: int) -> bytes:
    return bytes([n & 0xFF])


def _u16(n: int) -> bytes:
    return struct.pack("<H", n)


def _u32(n: int) -> bytes:
    return struct.pack("<I", n)


def _f32(n: float) -> bytes:
    return struct.pack("<f", n)


def _bstr(s: str) -> bytes:
    raw = s.encode("latin-1")
    return _u8(len(raw)) + raw


def build_minimal_ess(*, name: str = "Test", level: int = 4, location: str = "Sewer") -> bytes:
    """Tiny valid TES4SAVEGAME with no change records."""
    body = bytearray()
    body += ESS_MAGIC
    body += _u8(0) + _u8(125)
    body += b"\x00" * 16  # exeTime
    # headerVersion + placeholder header_size
    hdr_start = len(body)
    body += _u32(125)
    size_pos = len(body)
    body += _u32(0)
    after_size = len(body)
    body += _u32(1)  # saveNum
    body += _bstr(name)
    body += _u16(level)
    body += _bstr(location)
    body += _f32(1.0)
    body += _u32(1000)
    body += b"\x00" * 16  # gameTime
    # 1x1 screenshot: size field = 8 + 3
    body += _u32(11)
    body += _u32(1) + _u32(1)
    body += b"\x00\x00\x00"
    header_payload = len(body) - after_size
    struct.pack_into("<I", body, size_pos, header_payload)

    body += _u8(1)
    body += _bstr("Oblivion.esm")

    fid_off_pos = len(body)
    body += _u32(0)  # formIdsOffset placeholder
    body += _u32(0)  # recordsNum
    body += _u32(0xFF000001)
    body += _u32(0) * 3  # world
    body += _u32(0x000001A0)  # cell
    body += _f32(0) + _f32(0) + _f32(0)
    body += _u16(0)  # globals
    body += _u16(8)  # class size
    body += _u32(0)  # death counts
    body += _f32(0.0)
    body += _u16(0) + _u16(0) + _u16(0)
    body += _u32(0)  # combat
    body += _u32(0)  # created
    body += _u16(0) + _u16(0) + _u16(0)
    body += _u16(2)  # region size
    body += _u16(0)  # region num
    body += _u32(0)  # temp effects
    fid_off = len(body)
    struct.pack_into("<I", body, fid_off_pos, fid_off)
    body += _u32(1)
    body += _u32(0)  # iref 0 empty
    body += _u32(0)  # worldspaces
    return bytes(body)


class FormIdMapTests(unittest.TestCase):
    def test_default_plugins_order(self) -> None:
        plugins = load_plugins_txt()
        self.assertEqual(plugins[0], "Oblivion.esm")
        self.assertEqual(plugins[6], "DLCShiveringIsles.esp")
        self.assertTrue(plugins[-1].startswith("Altar"))

    def test_knights_prefix_shift(self) -> None:
        og = ["Oblivion.esm", "Knights.esp"]
        rem = load_plugins_txt()
        mapping = build_prefix_map(og, rem)
        self.assertEqual(mapping[0], 0)
        self.assertEqual(mapping[1], rem.index("Knights.esp"))
        fid = remap_form_id(0x01000E0A, mapping)
        self.assertEqual(hex_formid(fid), f"{rem.index('Knights.esp'):02X}000E0A")

    def test_created_items_dropped(self) -> None:
        self.assertIsNone(remap_form_id(0xFF000123, {0: 0}))

    def test_mod_prefix_is_skipped(self) -> None:
        og = ["Oblivion.esm", "Unofficial Oblivion Patch.esp", "Knights.esp"]
        rem = load_plugins_txt()
        mapping = build_prefix_map(og, rem)
        self.assertEqual(mapping[0], 0)
        self.assertNotIn(1, mapping)
        self.assertIsNone(remap_form_id(0x01000ABC, mapping))
        knights = rem.index("Knights.esp")
        self.assertEqual(mapping[2], knights)


class ConsoleExportTests(unittest.TestCase):
    def test_emits_setav_and_unlock(self) -> None:
        dump = CharacterDump(
            name="Hero",
            level=12,
            location="Cheydinhal",
            masters=["Oblivion.esm"],
            attributes={"strength": 60},
            skills={"blade": 55},
            inventory=[InventoryItem(0x00000F, 50)],
            quests=[QuestStage(0x0001B800, 30)],
            factions=[FactionRank(0x0001B8, 1)],
            spells=[0x0005E15F],
            map_markers=[0x0001A2B3],
        )
        text = emit_console_script(dump)
        self.assertIn("Altar.Cheat.AllowSetStage true", text)
        self.assertIn("player.setlevel 12", text)
        self.assertIn("player.setav strength 60", text)
        self.assertIn("player.setav blade 55", text)
        self.assertIn("player.additem 0000000F 50", text)
        self.assertIn("ShowMap 0001A2B3 1", text)
        self.assertIn("setstage 0001B800 30", text)
        self.assertNotIn("coc ", text)
        self.assertIn("setstage MQ01 90", text)
        self.assertIn("setstage MQ01 100", text)
        self.assertIn("EnableFastTravel 1", text)
        self.assertIn("enableplayercontrols", text)
        self.assertLess(text.index("ShowMap 0001A2B3 1"), text.index("setstage 0001B800 30"))
        self.assertLess(text.index("setstage 0001B800 30"), text.index("EnableFastTravel 1"))
        self.assertLess(text.index("setstage 0001B800 30"), text.rindex("enableplayercontrols"))

    def test_unlock_without_transferred_quests(self) -> None:
        dump = CharacterDump(
            name="Hero",
            level=2,
            location="Sewer",
            masters=["Oblivion.esm"],
            quests=[QuestStage(0x0001B800, 30)],
        )
        text = emit_console_script(dump, include_quests=False)
        self.assertNotIn("setstage 0001B800", text)
        self.assertIn("setstage MQ01 100", text)
        self.assertIn("EnableFastTravel 1", text)
        self.assertIn("enableplayercontrols", text)

    def test_skips_unmapped_map_markers(self) -> None:
        dump = CharacterDump(
            name="Hero",
            level=2,
            location="Sewer",
            masters=["Oblivion.esm"],
            map_markers=[0x01000ABC, 0x0001A2B3],
        )
        text = emit_console_script(dump)
        self.assertIn("ShowMap 0001A2B3 1", text)
        self.assertNotIn("ShowMap 01000ABC", text)

    def test_derived_pools_emitted(self) -> None:
        dump = CharacterDump(
            name="Hero",
            level=10,
            location="Sewer",
            masters=["Oblivion.esm"],
            attributes={
                "strength": 100,
                "intelligence": 71,
                "willpower": 66,
                "agility": 100,
                "endurance": 69,
            },
            base_magicka=0,
            base_fatigue=0,
        )
        _fill_derived_pools(dump)
        text = emit_console_script(dump)
        self.assertIn("player.setav magicka 142", text)
        self.assertIn("player.setav fatigue 335", text)

    def test_dedupe_keeps_highest_stage(self) -> None:
        dump = CharacterDump(
            name="Hero",
            level=2,
            location="Sewer",
            masters=["Oblivion.esm"],
            quests=[
                QuestStage(0x0001B800, 10),
                QuestStage(0x0001B800, 90),
                QuestStage(0x0001B800, 30),
            ],
        )
        from oblivion_migrate.ess_parser import _dedupe_quests

        dump.quests = _dedupe_quests(dump.quests)
        text = emit_console_script(dump)
        self.assertEqual(text.count("setstage 0001B800"), 1)
        self.assertIn("setstage 0001B800 90", text)


class MinimalEssTests(unittest.TestCase):
    def test_parse_header(self) -> None:
        raw = build_minimal_ess(name="Hero", level=7, location="Market")
        dump = parse_ess(_write_tmp(raw))
        self.assertEqual(dump.name, "Hero")
        self.assertEqual(dump.level, 7)
        self.assertEqual(dump.location, "Market")
        self.assertEqual(dump.masters, ["Oblivion.esm"])

    def test_xbox_container_rejected(self) -> None:
        path = _write_tmp(b"CON " + b"\x00" * 32)
        with self.assertRaises(EssError):
            parse_ess(path)


class SavInspectTests(unittest.TestCase):
    def test_gvas_magic(self) -> None:
        path = _write_tmp(b"GVAS" + b"\x00" * 16)
        path = path.with_suffix(".sav")
        path.write_bytes(b"GVAS" + b"\x00" * 16)
        text = inspect_sav(path)
        self.assertIn("GVAS", text)
        self.assertIn("Unreal Engine GVAS", text)
        self.assertIn("TES4SAVEGAME: not found", text)


def _write_tmp(data: bytes) -> Path:
    import tempfile

    handle = tempfile.NamedTemporaryFile(suffix=".ess", delete=False)
    handle.write(data)
    handle.close()
    return Path(handle.name)


if __name__ == "__main__":
    unittest.main()
