"""Parse original Oblivion PC .ess saves into a character dump."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .binary import BinaryReader
from .properties import EQUIPPED_FLAGS, PropertyParseError, skip_property_list

ESS_MAGIC = b"TES4SAVEGAME"
PLAYER_NPC_FID = 0x00000007
PLAYER_ACHR_FID = 0x00000014
CREATED_FID_MIN = 0xFF000000
TEMP_AV_COUNT = 73

REC_NPC = 35
REC_REFR = 49
REC_ACHR = 50
REC_QUST = 59
FLAG_MAP_MARKER = 0x00000400

ATTRIBUTES = (
    "strength",
    "intelligence",
    "willpower",
    "agility",
    "speed",
    "endurance",
    "personality",
    "luck",
)

SKILLS = (
    "armorer",
    "athletics",
    "blade",
    "block",
    "blunt",
    "handtohand",
    "heavyarmor",
    "alchemy",
    "alteration",
    "conjuration",
    "destruction",
    "illusion",
    "mysticism",
    "restoration",
    "acrobatics",
    "lightarmor",
    "marksman",
    "mercantile",
    "security",
    "sneak",
    "speechcraft",
)


@dataclass
class InventoryItem:
    form_id: int
    count: int
    equipped: bool = False
    created: bool = False


@dataclass
class FactionRank:
    form_id: int
    rank: int


@dataclass
class QuestStage:
    form_id: int
    stage: int
    log_entry: int = 0


@dataclass
class CharacterDump:
    name: str
    level: int
    location: str
    masters: list[str]
    attributes: dict[str, int] = field(default_factory=dict)
    skills: dict[str, int] = field(default_factory=dict)
    base_health: int | None = None
    base_magicka: int | None = None
    base_fatigue: int | None = None
    spells: list[int] = field(default_factory=list)
    factions: list[FactionRank] = field(default_factory=list)
    inventory: list[InventoryItem] = field(default_factory=list)
    quests: list[QuestStage] = field(default_factory=list)
    map_markers: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChangeRecord:
    form_id: int
    rec_type: int
    flags: int
    version: int
    data: bytes


def _flag(flags: int, bit: int) -> bool:
    return bool(flags & (1 << bit))


class EssError(ValueError):
    pass


def resolve_iref(iref: int, form_ids: list[int]) -> int:
    if iref >= CREATED_FID_MIN:
        return iref
    if iref == 0:
        return 0
    if iref < 0 or iref >= len(form_ids):
        return iref
    return form_ids[iref]


def parse_ess(path: str | Path) -> CharacterDump:
    data = Path(path).read_bytes()
    if data[:4] == b"CON ":
        raise EssError("Xbox 360 container saves are not supported. Use a PC .ess file.")
    if not data.startswith(ESS_MAGIC):
        raise EssError(f"Not an Oblivion PC save (magic={data[:12]!r})")

    r = BinaryReader(data)
    r.skip(12)
    major = r.u8()
    minor = r.u8()
    if minor >= 82:
        r.skip(16)  # SYSTEMTIME exeTime
    header_version = r.u32()
    _header_size = r.u32()
    _save_num = r.u32()
    name = r.bstring()
    level = r.u16()
    location = r.bstring()
    r.f32()  # gameDays
    r.u32()  # gameTicks
    r.skip(16)  # gameTime
    shot_size = r.u32()
    width = r.u32()
    height = r.u32()
    pix = 3 * width * height
    # UESP/OSE: size includes the 8 bytes of width/height.
    if shot_size >= pix + 8:
        r.skip(pix)
    else:
        r.skip(max(0, shot_size - 8))

    n_plugins = r.u8()
    masters = [r.bstring() for _ in range(n_plugins)]

    form_ids_offset = r.u32()
    records_num = r.u32()
    r.u32()  # nextObjectId
    r.u32()  # worldId
    r.u32()  # worldX
    r.u32()  # worldY
    r.u32()  # pc cell
    r.f32()
    r.f32()
    r.f32()

    globals_num = r.u16()
    r.skip(globals_num * 8)
    _class_size = r.u16()  # informational; payload follows (OSE)
    num_deaths = r.u32()
    r.skip(num_deaths * 6)
    r.f32()  # gameModeSeconds

    processes_size = r.u16()
    r.skip(processes_size)
    spec_size = r.u16()
    r.skip(spec_size)
    weather_size = r.u16()
    r.skip(weather_size)
    r.u32()  # playerCombatCount

    created_num = r.u32()
    for _ in range(created_num):
        r.read(4)  # type
        size = r.u32()
        r.u32()  # flags
        r.u32()  # formId
        r.u32()  # vci
        r.skip(size)

    quick_size = r.u16()
    r.skip(quick_size)
    ret_size = r.u16()
    r.skip(ret_size)
    iface_size = r.u16()
    r.skip(iface_size)
    _region_size = r.u16()
    region_num = r.u16()
    r.skip(region_num * 8)

    records: list[ChangeRecord] = []
    npc_player: ChangeRecord | None = None
    achr_player: ChangeRecord | None = None
    quest_records: list[ChangeRecord] = []
    map_marker_fids: list[int] = []
    for _ in range(records_num):
        rec = ChangeRecord(r.u32(), r.u8(), r.u32(), r.u8(), r.read(r.u16()))
        records.append(rec)
        if rec.form_id == PLAYER_NPC_FID and rec.rec_type == REC_NPC:
            npc_player = rec
        elif rec.form_id == PLAYER_ACHR_FID and rec.rec_type == REC_ACHR:
            achr_player = rec
        elif rec.rec_type == REC_QUST:
            quest_records.append(rec)
        elif (
            rec.rec_type == REC_REFR
            and rec.flags & FLAG_MAP_MARKER
            and rec.form_id
            and rec.form_id < CREATED_FID_MIN
        ):
            map_marker_fids.append(rec.form_id)

    temp_size = r.u32()
    r.skip(temp_size)

    # FormID array is at formIdsOffset; seek there rather than trusting sequential pos.
    r.seek(form_ids_offset)
    n_fids = r.u32()
    form_ids = [r.u32() for _ in range(n_fids)]

    dump = CharacterDump(
        name=name,
        level=level,
        location=location,
        masters=masters,
    )
    dump.warnings.append(f"ESS version {major}.{minor} headerVersion={header_version}")

    if npc_player is None:
        dump.warnings.append("Player NPC_ (0x7) change record not found; stats may be defaults.")
    else:
        _parse_npc(npc_player, form_ids, dump)

    if achr_player is None:
        dump.warnings.append("Player ACHR (0x14) change record not found; inventory/quests limited.")
    else:
        _parse_achr(achr_player, form_ids, dump, quest_records)

    dump.quests = _dedupe_quests(dump.quests)
    if not dump.quests:
        _quests_from_quest_records(quest_records, dump)
        dump.quests = [q for q in dump.quests if q.stage >= 0] or dump.quests

    dump.map_markers = list(dict.fromkeys(map_marker_fids))
    _fill_derived_pools(dump)
    return dump


def _parse_npc(rec: ChangeRecord, form_ids: list[int], dump: CharacterDump) -> None:
    r = BinaryReader(rec.data)
    flags = rec.flags
    try:
        if _flag(flags, 0):
            r.u32()
        if _flag(flags, 3):
            vals = [r.u8() for _ in range(8)]
            dump.attributes = dict(zip(ATTRIBUTES, vals, strict=True))
        if _flag(flags, 4):
            r.u32()  # npc flags
            dump.base_magicka = r.u16()
            dump.base_fatigue = r.u16()
            r.u16()  # barter gold
            r.i16()  # level offset
            r.u16()
            r.u16()
        if _flag(flags, 6):
            n = r.u16()
            for _ in range(n):
                iref = r.u32()
                rank = r.i8()
                fid = resolve_iref(iref, form_ids)
                if rank >= 0 and rank != 0xFF and fid:
                    dump.factions.append(FactionRank(fid, rank))
        if _flag(flags, 5):
            n = r.u16()
            for _ in range(n):
                fid = resolve_iref(r.u32(), form_ids)
                if fid and fid < CREATED_FID_MIN:
                    dump.spells.append(fid)
                elif fid >= CREATED_FID_MIN:
                    dump.warnings.append(f"skipped created spell {fid:08X}")
        if _flag(flags, 8):
            r.skip(4)
        if _flag(flags, 2):
            dump.base_health = r.u16()
            r.skip(2)
        if _flag(flags, 28):
            n = r.u16()
            r.skip(n * 5)
        if _flag(flags, 7):
            full = r.bstring()
            if full:
                dump.name = full
        if _flag(flags, 9):
            vals = [r.u8() for _ in range(21)]
            dump.skills = dict(zip(SKILLS, vals, strict=True))
        if _flag(flags, 10):
            r.u32()
    except (EOFError, ValueError) as exc:
        dump.warnings.append(f"NPC_ parse stopped early: {exc}")


def _parse_achr(
    rec: ChangeRecord,
    form_ids: list[int],
    dump: CharacterDump,
    quest_records: list[ChangeRecord],
) -> None:
    r = BinaryReader(rec.data)
    flags = rec.flags
    try:
        if _flag(flags, 31):
            r.skip(16)
        if _flag(flags, 1):
            r.skip(36)
        elif _flag(flags, 2):
            r.skip(28)
        elif _flag(flags, 3):
            r.skip(28)
        if _flag(flags, 23) and not (_flag(flags, 1) or _flag(flags, 2) or _flag(flags, 3)):
            r.skip(4)
        _apply_temp_actor_values(r)
        r.u8()  # actor flag
        if _flag(flags, 0):
            r.skip(4)
        if _flag(flags, 27):
            _parse_inventory(r, form_ids, dump)
        rest = rec.data[r.pos :]
        _extract_quests(rest, form_ids, quest_records, dump)
    except (EOFError, PropertyParseError, ValueError) as exc:
        dump.warnings.append(f"ACHR parse stopped early: {exc}")
        # Still try quest scan on full record.
        _extract_quests(rec.data, form_ids, quest_records, dump)


def _apply_temp_actor_values(r: BinaryReader) -> None:
    """Skip the player-only 876-byte temporary AV block (3 x 73 floats).

    These floats are *modifiers* (fortify/damage), not base stats. ACBS magicka
    and fatigue are often 0 (auto-calc); derived bases are filled later.
    """
    r.skip(TEMP_AV_COUNT * 3 * 4)


def _fill_derived_pools(dump: CharacterDump) -> None:
    """When ACBS stores 0, Oblivion auto-calcs magicka/fatigue from attributes."""
    attrs = dump.attributes
    if not attrs:
        return
    if dump.base_magicka in (None, 0):
        intel = int(attrs.get("intelligence", 0))
        if intel:
            dump.base_magicka = 2 * intel
            dump.warnings.append(
                "ACBS magicka was 0 (auto-calc); used 2 * intelligence "
                "(racial/birthsign bonuses not included)"
            )
    if dump.base_fatigue in (None, 0):
        fatigue = (
            int(attrs.get("strength", 0))
            + int(attrs.get("willpower", 0))
            + int(attrs.get("agility", 0))
            + int(attrs.get("endurance", 0))
        )
        if fatigue:
            dump.base_fatigue = fatigue
            dump.warnings.append(
                "ACBS fatigue was 0 (auto-calc); used strength+willpower+agility+endurance"
            )


def _dedupe_quests(quests: list[QuestStage]) -> list[QuestStage]:
    best: dict[int, QuestStage] = {}
    for q in quests:
        prev = best.get(q.form_id)
        if prev is None or q.stage > prev.stage:
            best[q.form_id] = q
    return list(best.values())


def _parse_inventory(r: BinaryReader, form_ids: list[int], dump: CharacterDump) -> None:
    item_num = r.u16()
    if item_num > 8000:
        raise PropertyParseError(f"inventory itemNum {item_num} looks corrupt")
    for _ in range(item_num):
        iref = r.u32()
        stacked = r.i32()
        changed_n = r.u32()
        equipped = False
        try:
            for _c in range(changed_n):
                pnum = r.i16()
                flags = skip_property_list(r, pnum)
                if any(f in EQUIPPED_FLAGS for f in flags):
                    equipped = True
        except (PropertyParseError, EOFError) as exc:
            dump.warnings.append(f"inventory extra parse failed for iref {iref}: {exc}")
            break
        fid = resolve_iref(iref, form_ids)
        created = fid >= CREATED_FID_MIN
        if created:
            dump.warnings.append(f"skipped created/custom item {fid:08X}")
            continue
        if stacked > 0 or equipped:
            dump.inventory.append(
                InventoryItem(form_id=fid, count=max(stacked, 1), equipped=equipped)
            )


def _extract_quests(
    blob: bytes,
    form_ids: list[int],
    quest_records: list[ChangeRecord],
    dump: CharacterDump,
) -> None:
    quest_fids = {q.form_id for q in quest_records}
    if not quest_fids or len(blob) < 8:
        return
    found: list[QuestStage] = []
    # Prefer packed list: ushort count + N * (iref u32, stage u8, log u8)
    for off in range(0, len(blob) - 2):
        n = int.from_bytes(blob[off : off + 2], "little")
        if n < 1 or n > 400:
            continue
        need = 2 + n * 6
        if off + need > len(blob):
            continue
        entries: list[QuestStage] = []
        ok = True
        p = off + 2
        for _ in range(n):
            iref = int.from_bytes(blob[p : p + 4], "little")
            stage = blob[p + 4]
            log = blob[p + 5]
            fid = resolve_iref(iref, form_ids)
            if fid not in quest_fids:
                ok = False
                break
            entries.append(QuestStage(fid, stage, log))
            p += 6
        if ok and entries:
            found = entries
            break
    if found:
        dump.quests = found
        return
    # Fallback: scan irefs that resolve to QUST formids.
    seen: set[int] = set()
    for off in range(0, len(blob) - 6):
        iref = int.from_bytes(blob[off : off + 4], "little")
        fid = resolve_iref(iref, form_ids)
        if fid in quest_fids and fid not in seen:
            seen.add(fid)
            dump.quests.append(QuestStage(fid, blob[off + 4], blob[off + 5]))


def _quests_from_quest_records(quest_records: list[ChangeRecord], dump: CharacterDump) -> None:
    """Last-resort: mark QUST records as stage 0 if we could not find journal data."""
    if dump.quests:
        return
    dump.warnings.append(
        "Could not decode journal stages; quest FormIDs listed without stage. "
        "setstage commands will be omitted unless you pass --force-quest-ids."
    )
    for rec in quest_records:
        dump.quests.append(QuestStage(rec.form_id, -1, 0))
