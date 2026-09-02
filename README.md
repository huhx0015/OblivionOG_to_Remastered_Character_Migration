# Oblivion OG to Remastered Character Migration

**PC only.** This tool is intended for **Oblivion OG on PC** and **Oblivion Remastered on PC**. Xbox, PlayStation, Nintendo, and other consoles are **not** supported. Xbox 360 `CON ` container saves are rejected.

Unofficial tool that reads an original 2006 Oblivion PC `.ess` save and writes a Remastered **console batch** (`migrate.txt`). You create a new Remastered character on PC, then run `exec migrate.txt` in the in-game console.

This is **not** a save-file converter. It does **not** write or patch a Remastered `.sav`. Original saves are TES4 (`TES4SAVEGAME`); Remastered saves are Unreal Engine **GVAS**. A byte-for-byte transplant is not possible. Bethesda does not support official save transfer.

Cyrodiil itself stays a mostly fresh Remastered world. The script restores **character data** (stats, gear deltas, spells, factions, discovered map markers, journal stages) onto whatever cell you are standing in.

**Not affiliated with Bethesda, ZeniMax, or Microsoft.** Use at your own risk. Back up your Remastered saves first.

## Requirements

- Windows PC with original Oblivion (2006) **and** Oblivion Remastered **on PC**
- [Python 3.10+](https://www.python.org/downloads/) — stdlib only, no pip packages
- An original Oblivion PC `.ess` from `Documents\My Games\Oblivion\Saves`
- Oblivion Remastered on PC (Steam build documented), with the in-game console enabled

**Not supported:** Xbox (original or Remastered), PlayStation, other consoles, Xbox 360 `CON ` saves, or transferring a console save through this script. Game Pass / WinGDK layouts are untested (`exec` paths differ from Steam).

A clone of this repo does **not** include a bundled Python interpreter. Install Python and tick **Add python.exe to PATH**.

## How it works

```text
OG .ess  →  parse character dump  →  migrate.txt  →  copy to Binaries\  →  in-game: exec migrate.txt
```

FormID high bytes are remapped from the original save’s plugin list onto Remastered `plugins.txt` (bundled default: GOTY DLC + Knights + Altar ESPs). Plugins that do not exist in Remastered (Unofficial Patches, overhauls, weather mods, and so on) are listed as comments; their FormIDs are skipped instead of colliding with DLC slots.

Created objects (`0xFF......` — custom spells, custom enchantments) are dropped.

## Warning before you start

- Using the console **disables achievements** on that Remastered save unless you already use an achievement unblocker.
- `additem` **duplicates inventory** if you `exec migrate.txt` more than once on the same character.
- `setstage` can fire quest scripts. Those scripts can start a cinematic, freeze movement and menus, and **abort the rest of the batch** (including the control/fast-travel unlock at the end). See [Known issues](#known-issues).
- Keep a Remastered save from **before** `exec` so you can retry with `--no-quests` if the character locks up.

## Generate migrate.txt

From this folder:

```text
python migrate.py migrate "C:\Users\You\Documents\My Games\Oblivion\Saves\Save 12.ess" --output migrate.txt
```

Useful extras:

```text
python migrate.py migrate "path\to\Save 12.ess" --output migrate.txt --json character.json
python migrate.py migrate "path\to\Save 12.ess" --output migrate.txt --no-quests
python migrate.py dump "path\to\Save 12.ess"
python migrate.py inspect-sav "path\to\Remastered.sav"
```

| Flag | Meaning |
| --- | --- |
| `--output` / `-o` | Write `migrate.txt` here (default: stdout). Prefer `--output` in PowerShell. |
| `--json` | Also write the parsed character dump as JSON |
| `--plugins` | Remastered `plugins.txt` if your load order is not the bundled [data/remastered_plugins.txt](data/remastered_plugins.txt) |
| `--no-quests` | Do not emit transferred `setstage` lines. Tutorial unlock (`MQ01`) is still emitted. Safer if quest scripts freeze the character. |

`python -m oblivion_migrate ...` works if this folder is on `PYTHONPATH`.

If you wrap the CLI in PowerShell (`.\run.ps1`), do **not** use `-o`; PowerShell treats it as `-OutVariable` / `-OutBuffer`. Use `--output`.

Stock Remastered `plugins.txt` (also under `OblivionRemastered\Content\Dev\ObvData\Data\Plugins.txt`):

```text
Oblivion.esm
DLCBattlehornCastle.esp
DLCFrostcrag.esp
DLCHorseArmor.esp
DLCMehrunesRazor.esp
DLCOrrery.esp
DLCShiveringIsles.esp
DLCSpellTomes.esp
DLCThievesDen.esp
DLCVileLair.esp
Knights.esp
AltarESPMain.esp
AltarDeluxe.esp
AltarESPLocal.esp
```

## In-game steps

1. Copy `migrate.txt` into **this** folder (not next to the `.exe`):

   ```text
   <Steam>\steamapps\common\Oblivion Remastered\OblivionRemastered\Binaries\
   ```

   Typical Steam path:

   ```text
   C:\Program Files (x86)\Steam\steamapps\common\Oblivion Remastered\OblivionRemastered\Binaries\migrate.txt
   ```

   Remastered `exec` **does not take a path**. It only looks in `OblivionRemastered\Binaries\`. Putting the file in `Binaries\Win64\` (beside `OblivionRemastered-Win64-Shipping.exe`) does nothing.

2. Start a **new** Remastered character and finish character generation so race and face exist. A save just after leaving the sewers is a good base. Appearance, race, class, and birthsign come from **this** character, not the OG save.

3. Open the console (`~` / `` ` ``, the key left of `1`).

4. Type exactly:

   ```text
   exec migrate.txt
   ```

   Hundreds of commands can take a while. The game does **not** pause while the console is open.

5. Close the console. Confirm you can **walk** and **open the menu**. Then save from the pause menu.

   Remastered saves live in `Documents\My Games\Oblivion Remastered\Saved\SaveGames`.

You stay in the cell where you ran `exec`. There is no teleport.

## What transfers

Commands are emitted in this order: stats → inventory → spells → factions → map markers → quest stages → control / fast-travel unlock.

| Data | Behavior |
| --- | --- |
| Level, attributes, skills | `player.setlevel` / `player.setav` from the player `NPC_` change record |
| Health | `player.setav health` from NPC_ ACBS when present |
| Magicka / fatigue | From ACBS when non-zero. If ACBS stored `0` (auto-calc), magicka is `2 × intelligence` and fatigue is `strength + willpower + agility + endurance`. Racial and birthsign magicka bonuses are **not** included. |
| Inventory | `player.additem` / `player.equipitem` for **save deltas** only. Items that never differed from ESM defaults may be missing. Equipped state is preserved when parsed. Gold is included when present as a delta. |
| Spells | `player.addspell` for vanilla + official DLC FormIDs |
| Factions | `player.setfactionrank` |
| Map markers | `ShowMap <formid> 1` for REFR change records with the map-marker flag (locations discovered in the OG save). Markers from skipped mods are dropped. |
| Quest journal | `setstage <formid> <stage>` for the highest decoded stage per quest. NPCs, world scripts, and gates will not match. |
| Tutorial / fast travel | Always ends with `setstage MQ01 90`, `setstage MQ01 100`, and `EnableFastTravel 1` so the sewer tutorial lock is cleared even if you never walked out of the sewers. |
| Controls | Always ends with `SetInChargen 0` and `enableplayercontrols`. |

The generated file also starts with `Altar.Cheat.AllowSetStage true` (required for `setstage` in Remastered) and comments listing skipped plugins.

## What does not transfer

| Data | Why |
| --- | --- |
| Remastered `.sav` / world state | Different file format (GVAS). No ESS blob inside the `.sav`. |
| Position / cell | `coc` to Imperial City Market District does **not** work in Remastered. The script does not teleport. |
| FaceGen, race, sex, class, birthsign, name | Taken from the new Remastered character |
| Player-created spells, custom enchantments | FormIDs `0xFF......` are skipped |
| Third-party mods | Anything not in Remastered `plugins.txt` is skipped (UOP, OCO, weather, harvest, etc.) |
| Horses, houses, ownership, storage | Not parsed |
| NPC deaths, disposition, AI, crime (beyond faction ranks) | Not parsed |
| Oblivion Gates, Kvatch/IC siege geometry, placed objects | World stays vanilla Remastered |
| Local-map fog of war | Only world-map marker FormIDs are emitted |
| Time, date, fame/infamy globals | Not emitted as console commands |

If the OG save has **no** `DLCShiveringIsles.esp` (SI merged into `Oblivion.esm`), SI FormIDs may keep prefix `00` and will not match Remastered prefix `06`. The script prints a comment warning when that happens.

## Known issues

These were observed on Steam PC Remastered while running generated batches.

### `exec migrate.txt` does nothing

The file is in the wrong folder. It must be in `OblivionRemastered\Binaries\`, **not** `Binaries\Win64\`. `exec` cannot take a path. The filename must include `.txt`.

A missing file produces no useful error.

### Cannot move; cannot open the menu; camera and console still work

A `setstage` line started a quest cinematic (`DisablePlayerControls`). In Remastered the console does not pause the game, so the cinematic can freeze you **and** stop the rest of `exec` (including `enableplayercontrols` at the end).

In the console:

```text
enableplayercontrols
EnableFastTravel 1
```

If that is not enough:

```text
SetInChargen 0
setstage MQ01 100
```

Then close the console and press Esc or the radial-menu key once. **Save.**

To avoid this on a retry, reload the pre-`exec` save and regenerate with `--no-quests`. Do not `exec` the full batch again on the frozen character if items already applied.

### Fast travel is locked

Common causes, in order:

1. Still in an **interior** (sewers, shop, dungeon). Walk outside. Oblivion cannot fast travel from interiors.
2. The sewer tutorial was never completed. The batch tries to finish `MQ01` and run `EnableFastTravel 1`, but those lines never run if `setstage` aborted the file. Type them manually (see above).
3. **Overencumbered.** Dumped inventory (armor, weapons, 100k+ gold is weightless, but gear is not) can exceed carry weight. Drop items, or `player.modav carryweight 10000`.
4. In combat, or a quest that blocks travel.
5. Vampire in sunlight (vanilla restriction).

### Map markers from OG are missing

`ShowMap` is the documented Construction Set function; Remastered may ignore it in the console.

Workaround (unlocks **every** marker, including places you never visited):

```text
tmm 1
```

`tmm 1,0,1` (Skyrim-style) does not work in Remastered. Use `tmm 1` only.

### No teleport to the Imperial City

By design. `coc ICMarketDistrict` does not work here. Walk or fast travel once it is unlocked. `coc` to a specific **interior** editor ID (for example a shop cell) may still work; worldspace `coc` is unreliable.

### Magicka feels too low

ACBS often stores magicka/fatigue as `0` (auto-calc). The script then uses `2 × intelligence` and does **not** add racial or birthsign bonuses. Adjust with `player.setav magicka <n>` if needed.

### Inventory gaps

Only items that appear as **change records** in the `.ess` are added. Default starting gear or untouched ESM stacks can be missing. Custom / mod items are skipped. Check the `; skipped N FormIDs` comment at the bottom of `migrate.txt`.

### Quest log does not match the world

Journal stages are force-set. Martin may not be where the quest says, Kvatch may still be intact, guild buildings may not recognize you, and some stages can break scripts. `--no-quests` plus playing the guild/MQ content in Remastered is often more stable.

### Achievements disabled

Any console use flags the save. This tool cannot avoid that.

## Troubleshooting cheatsheet

| Symptom | Try |
| --- | --- |
| `exec` silent | File in `...\OblivionRemastered\Binaries\migrate.txt` |
| Frozen, no menu | `enableplayercontrols` then save; retry later with `--no-quests` |
| No fast travel | Outdoors + `EnableFastTravel 1` + `setstage MQ01 100`; check encumbrance |
| Empty world map | `tmm 1` |
| Duplicate items | You ran `exec migrate.txt` twice; reload an older save |
| PowerShell error on `-o` | Use `--output` |
| `Not an Oblivion PC save` | Xbox `CON ` file; need a PC `.ess` |

## Tests

```text
python -m unittest discover -s tests -v
```

## Remastered save format

Inspected Steam `.sav` files are Unreal GVAS (`GVAS` magic), not `TES4SAVEGAME`. Details: [docs/REMASTERED_SAVE_FORMAT.md](docs/REMASTERED_SAVE_FORMAT.md).

`python migrate.py inspect-sav path\to\file.sav` reports whether a nested TES4 blob is present (none found on current patches).

## License / disclaimer

Unofficial fan tool. Oblivion and Oblivion Remastered are trademarks of their owners. You are responsible for your saves. There is no warranty that a given `.ess` will parse cleanly or that Remastered will accept every emitted command after a game patch.
