# Oblivion Remastered save format (Phase 0)

Inspected Steam PC saves from:

`Documents\My Games\Oblivion Remastered\Saved\SaveGames`

Re-checked against a live autosave (~778 KB) and `saves_meta.sav` (~505 KB).

## Findings

- Manual, auto, and quick saves all start with Unreal **GVAS** (`47 56 41 53`) at offset 0.
- `saves_meta.sav` is also GVAS (`/Script/Altar.VAltarSaveMetaData`). It contains Unreal properties such as `bIsESS`, `BoolProperty`, `PlayerName`, `PlayerLevel`, and JPEG thumbnails.
- ASCII search of gameplay `.sav` files found **no** `TES4SAVEGAME` magic. Sampled zlib-like streams (`78 01` / `78 9c` / `78 da`) also do not decompress to a TES4 ESS. The original Oblivion ESS blob is **not** stored as uncompressed (or trivially zlib-wrapped) TES4 data inside the `.sav`.
- Class / path strings near the gameplay-save header include `/Script/Altar.VAltarSaveContainer`, `AltarSaveData`, `ArrayProperty`, and `ByteProperty`. Gameplay state is wrapped in Unreal properties, not a raw TES4 file.
- File sizes (~300 KB–800 KB) are consistent with Unreal serialization of Gamebryo-side state plus UE metadata, not a renamed `.ess`.
- Stock Remastered `plugins.txt` is: Oblivion.esm, official DLC ESPs, Knights.esp, then `AltarESPMain.esp`, `AltarDeluxe.esp`, `AltarESPLocal.esp`.

## Implication

A byte-for-byte ESS transplant into Remastered is not viable without a full reverse-engineering of the GVAS object graph. Character migration therefore goes:

**OG `.ess` → parsed character dump → Remastered console `exec` script.**

If a later patch embeds a zlib/Oodle-compressed ESS, `python migrate.py inspect-sav <file.sav>` will report `TES4SAVEGAME` or a nested TES4 blob.
