"""Emit a Remastered console batch (`exec migrate.txt`)."""

from __future__ import annotations

from .ess_parser import CharacterDump
from .formid_map import (
    build_prefix_map,
    hex_formid,
    load_plugins_txt,
    remap_form_id,
    shiverings_isles_merged,
    unmapped_masters,
)

ATTRIBUTE_AV = {
    "strength": "strength",
    "intelligence": "intelligence",
    "willpower": "willpower",
    "agility": "agility",
    "speed": "speed",
    "endurance": "endurance",
    "personality": "personality",
    "luck": "luck",
}

SKILL_AV = {
    "armorer": "armorer",
    "athletics": "athletics",
    "blade": "blade",
    "block": "block",
    "blunt": "blunt",
    "handtohand": "handtohand",
    "heavyarmor": "heavyarmor",
    "alchemy": "alchemy",
    "alteration": "alteration",
    "conjuration": "conjuration",
    "destruction": "destruction",
    "illusion": "illusion",
    "mysticism": "mysticism",
    "restoration": "restoration",
    "acrobatics": "acrobatics",
    "lightarmor": "lightarmor",
    "marksman": "marksman",
    "mercantile": "mercantile",
    "security": "security",
    "sneak": "sneak",
    "speechcraft": "speechcraft",
}


def _append_unlock(lines: list[str]) -> None:
    """Finish the tutorial lock and restore movement after setstage cinematics."""
    lines.extend(
        [
            "SetInChargen 0",
            "setstage MQ01 90",
            "setstage MQ01 100",
            "EnableFastTravel 1",
            "enableplayercontrols",
        ]
    )


def emit_console_script(
    dump: CharacterDump,
    remaster_plugins: list[str] | None = None,
    *,
    include_quests: bool = True,
) -> str:
    plugins = remaster_plugins if remaster_plugins is not None else load_plugins_txt()
    prefix_map = build_prefix_map(dump.masters, plugins)
    skipped_plugins = unmapped_masters(dump.masters, plugins)
    lines: list[str] = [
        "; Oblivion OG to Remastered Character Migration",
        f"; Source character: {dump.name}  level {dump.level}  ({dump.location})",
        "; Using this file disables achievements unless you use an unblocker.",
        "",
        "Altar.Cheat.AllowSetStage true",
        "",
    ]

    if skipped_plugins:
        lines.append("; Skipped plugins (not in Remastered load order):")
        for name in skipped_plugins:
            lines.append(f";   {name}")
        lines.append("")

    if shiverings_isles_merged(dump.masters):
        lines.append(
            "; WARNING: save has no DLCShiveringIsles.esp — SI may be merged into "
            "Oblivion.esm. SI FormIDs may not remap correctly."
        )
        lines.append("")

    lines.append(f"player.setlevel {max(1, min(dump.level, 255))}")
    if dump.base_health:
        lines.append(f"player.setav health {dump.base_health}")
    if dump.base_magicka:
        lines.append(f"player.setav magicka {dump.base_magicka}")
    if dump.base_fatigue:
        lines.append(f"player.setav fatigue {dump.base_fatigue}")

    for key, av in ATTRIBUTE_AV.items():
        if key in dump.attributes:
            lines.append(f"player.setav {av} {dump.attributes[key]}")
    for key, av in SKILL_AV.items():
        if key in dump.skills:
            lines.append(f"player.setav {av} {dump.skills[key]}")

    lines.append("")
    skipped_ids = 0
    for item in dump.inventory:
        new_id = remap_form_id(item.form_id, prefix_map)
        if new_id is None:
            skipped_ids += 1
            continue
        lines.append(f"player.additem {hex_formid(new_id)} {item.count}")
        if item.equipped:
            lines.append(f"player.equipitem {hex_formid(new_id)}")

    lines.append("")
    for spell in dump.spells:
        new_id = remap_form_id(spell, prefix_map)
        if new_id is None:
            skipped_ids += 1
            continue
        lines.append(f"player.addspell {hex_formid(new_id)}")

    lines.append("")
    for fac in dump.factions:
        new_id = remap_form_id(fac.form_id, prefix_map)
        if new_id is None:
            continue
        lines.append(f"player.setfactionrank {hex_formid(new_id)} {fac.rank}")

    lines.append("")
    for marker in dump.map_markers:
        new_id = remap_form_id(marker, prefix_map)
        if new_id is None:
            skipped_ids += 1
            continue
        lines.append(f"ShowMap {hex_formid(new_id)} 1")

    if include_quests:
        lines.append("")
        for q in dump.quests:
            if q.stage < 0:
                continue
            new_id = remap_form_id(q.form_id, prefix_map)
            if new_id is None:
                continue
            lines.append(f"setstage {hex_formid(new_id)} {q.stage}")

    lines.append("")
    _append_unlock(lines)
    lines.append("")
    if skipped_ids:
        lines.append(
            f"; skipped {skipped_ids} FormIDs from mods/created items not in Remastered"
        )
    for warn in dump.warnings:
        lines.append(f"; {warn}")
    lines.append("")
    return "\n".join(lines)
