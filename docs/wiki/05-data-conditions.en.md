# 05 Data and conditions

[한국어](05-data-conditions.md) | [English](05-data-conditions.en.md) · [Index](README.en.md)

Paths are relative to the RE0 project root. Citations name files and functions, not line numbers. Evidence level of everything here is static (code and script reading, native functions run in an emulator) unless it is stated to have been seen live.

## General (any RE map mod)

### Placements

- Item and enemy placements live in the game's own placement tables (room, kind, item, amount, world position, a condition byte). Read them with a parser that raises unless the layout consumes the whole file, so a wrong layout cannot pass quietly.
- Convert world position to map canvas with the game's own map transform. Run the game's anchor and per-room correction functions in an x86 emulator for every room and floor instead of re-deriving them. The scale constant must be proved with a test that a wrong value fails (page 07): "the point falls inside its room" passed even with a wrong scale; matching trigger-volume wall edges to the room box discriminated.
- Choose the floor whose piece contains the point; if none does, use the nearest and flag it. Never hide a row because it is off its piece.
- Locks: place on the door whose GUI flag equals the lock's done flag, at the painted centre of the door sprite.
- Puzzles: bind an item-use script group to its trigger volume (a wildcard volume inherits a unique caller group). Place at the volume's centre if it lies on the map.
- Items given only by a script have no table row. List them by hand with the script, group and flag, check each against the same group by tool, and place at the trigger volume when one is tied to the group, else at room level.

### Conditions

- A row's condition byte maps to a flag in the game's bit array; a row spawns only if the byte is 0 or the flag is set. Use the game's own test, so the mod and the game agree.
- Flags unreadable means unknown: treat all as zero so conditional rows stay off rather than appear falsely, and say so in the log.
- Rows whose reward wording says "only appears after rank X" must carry the same condition byte so room counts and marks follow the live flag.

### Done state of a mark

- Table items: taken is read from the placement manager (the row's kind zeroed on pickup; the slot's link freed by a script). Guard each read against the expected room, kind and item and count mismatches.
- Identify which table is loaded from its row count: save restore brings back rows and the count but not the mode field, so a rule that needs the mode fails after loading a save.
- Enemies: the kill reaches the table only when the room unloads or at a save. Before that, read the live actor lists, skipping actors in transitional states; item and player actors also have HP 0 so the row's kind must be an enemy.
- Puzzles and locks: done when their flag is set. A flag that any reachable script clears again is not a proof.
- Events: see below.
- Difficulty: read from which table is loaded, with the user's INI value only as a fallback.

### Events (audit method)

An event is a script group that starts a cutscene or turns an enemy on with no cutscene.

1. Disassemble every room script with the game's own command table; the decoder raises if a command leaves its group.
2. Walk each group from its real entry with the evaluator, forcing one flag at a time, so conditions are what the script tests and no neighbour is blamed.
3. `done` flag: setting it stops the event and a script sets it. `need` flag: clearing it stops the event; only the first `need` is applied to the mark, the rest are listed. A mark stays hidden until its `need` flag is set, and stays hidden when flags are unknown.
4. Status: **excluded** (room setup, item use that already has a puzzle mark, cutscenes already covered by a placed group), **unresolved** (no flag decides that it happened, or that flag is cleared again by a script so the mark would return), **script_read** (drawn).
5. Position: trigger volume if the group's tag points to one, the table row of an item for the item tag, otherwise **room level**, labelled so. Room-level is not where the event happens.
6. Say plainly: `script_read` means only that a done flag exists. Nobody has seen the cutscene. Tags were classified by observation over all scripts because the native code that selects a group by tag was not found.

### Dropped items

- Items the player drops occupy slots past the table's rows in the same manager. Read them every frame, so pickup removes the icon next frame.
- A freed slot keeps stale bytes; validity is the slot's link not being the free marker, not the row's kind.
- Project the world position with the same transform as table rows. A point slightly off the piece snaps to its edge; further than a small distance counts as another floor's base.
- Draw the icon on the game's own dot. If the same room exists on several floors, filter by the floors the map is drawing.
- Count every drop path (valid, drawn, unmapped, rejected, capped) in a log line.

### Category rules

- Map tables to six categories by item class, with the game's item-name table: weapons are **key items** (the player cannot buy or find them freely); recovery items, ammo, grenades and the like are common items; documents and maps go to files; characters are story presence and are not marked; objects the game already marks (typewriter) are skipped.
- Kinds that are the player classes are never enemies.
- Keep the weapon list explicit in one place and import it everywhere; Molotov is a weapon.

## RE0 HD Remaster specific

### Data files and counts

| File | Content | Count at HEAD |
| --- | --- | --- |
| `data/native-map.json` | Regions, floors, map pieces, door instances, location records | 6 regions, 23 floors, 138 pieces, 115 door instances, 175 location records |
| `data/room-matches.json`, `data/external-locations.json` | Reviewed correspondence of native rooms to the external catalogue | 122 claims covering 124 external places |
| `data/room-contents.json` | Per-room contents by difficulty from Evil Resource (checked 2026-11-03; facts and URLs only) | 124 places, 1187 content rows |
| `data/item-uses.json` | Curated lock and puzzle item uses | built by `tools/extract/item_uses.py` |
| `data/placements.json` | All located rows | 758 rows: 345 enemy, 213 item, 67 key, 33 file, 20 lock, 80 puzzle (23 item-use + 57 event) |
| generated `markers[]` | One def per row and distinct label (per difficulty) | `MARKER_COUNT 781` (`labels_generated.h`) |
| generated catalogue | Places, content rows, links | 122, 472, 275 (`verification/label-build.json`) |
| `data/room-state.json` | Visited/revealed flags per piece, doors per piece | 138 pieces |
| `data/room-projection.json` | Drop projection: room, piece, base (bx, by) | 171 rows over 109 rooms |
| `data/item-names.json` | All item ids, English/Korean name, class | 181 ids |
| `verification/state-flags.json` | Done state of each row | |
| `verification/event-audit.json` | Event audit | 305 groups |

Regions in order (`tools/extract/placements.py`): `tr` (room 0), `sh` (36), `dm` (86), `ch` (99), `bt` (132), `pl` (141); rooms end at 175.

### Flags and tables (native addresses)

- Flag array: `[[0xdcc014] + 0x20]`, bit test `0x59b8d0`. A row's condition byte `c` tests flag `0x312 + c` (`src/core/annotation.h`, `annotation.c`; spawn gate `0x410c46-0x410c75`). The map (`0x5b6903-0x5b6947`) and item list (`0x57da2f-0x57da73`) use the same test. Array holds 71 words; 33 words are copied (`RE0_FLAG_WORDS`).
- Leech Hunter reward rows: condition bytes 160, 161, 162 = flags `0x3b2`, `0x3b3`, `0x3b4`, ranks B, E, A; one writer `0x59d2a0` from reward bits `0x20`, `0x100`, `0x10` of `[0xdcbe9c] + 0x40`; thresholds table `0xcdb59c` (100, 90, 60, 30, any) (`tools/extract/conditions.py`).
- Placement manager `[0xdcc010]`: 0x4e8 slots of 0x5c bytes from `+0x30`; link at `+0x2c`; count at `+0x24fac`; mode at `+0x24ff0`. Row fields: `+0` room, `+4` kind, `+8` item, `+0x39` taken byte, `+0x3c` amount or HP (`verification/state-flags.md`, `annotation.c`).
- Tables per mode: `loctbl0000/0100/0200` with 647/589/568 rows (`annotation.c`); the easy/normal/hard naming rests on row counts matching the catalogue and was not checked against a difficulty menu. Mode 3 picks a random `loctbl030x`; then the INI difficulty applies.
- Done rule (`annotation.c`): flag set, or row kind 0, or taken byte set, or link `0xffffffff`, or the killed bit (enemies). Row guard: room, kind (or 0), and item (not for enemies, as `0x412c30` rewrites row+8 from the actor).
- Kinds: `0x71` placed items, `0x78` script-given keys (never spawn; 18 rows), enemies `0x10..0x6f` except `0x3b` (`annotation.c`, walk `0x61d544`); kinds 2 and 5 are the player characters (150/250 HP) and are removed; `0x6a`, `0x6b` are zombie-family enemies (14 rows added).
- Enemy kill: save virtual (`vtable+0x94`) returns 1 at HP 0, setting row `+0x39` (`0x412d7a`), written when the room unloads (`0x61dde0`) or at a save (`0x613854`); before that read the actor lists (`re0_map.c`: owner `[0xe2d434]`, layers 9, 0xc, 0xd, head `+0x2c`, next `+0x14`, state `+0xc & 7` not 3 or 4, slot `+0xff0`, HP `+0x1030`). Exceptions: the Queen Leech second form (`uEnemy47`) never writes HP, so it goes only while its actor is on the list at HP 0 and returns after the room unloads; an actor deleted before unload leaves the row live.
- Visited/revealed: piece state = visited + 2 x revealed, colour table `0xd9de40`, read at `0x5b4cfc`; state 0 means the game draws nothing. Revealed is flag `0x2c8 + region` set by the map item (`0x5d74a1`), with the exception that room `0x19` of region 5 also counts under the map of the region on screen. Visited is `0x5bac90`, mostly flag `0x200 + room` (written at `0x60ed84`, `0x60ee53`, `0x61e7df`), some rooms with a second flag per floor, room `0xa6` one flag per floor. Each rule was proved to be an AND of the flags it asks for by running the native function over every combination (`tools/extract/room_state.py`).
- All-rooms scope patches the call at `0x5b4afa` (one flag test) so unreached rooms get state 2 and draw grey outlines; read-only, 5 bytes, checked against context bytes first (`re0_map.c`). The floor tabs and region list stay native.

### Placement conversion

`tools/extract/placements.py`: `canvas = ((base + world * 0.07) * 1.5 + 163, (base + world * 0.07) * 1.5 - 357)` (x uses world x, y uses world z); `base` from native `0x5bb8c0` (anchor), the floor table `0xd9d7b8` (offset at `+0x10/+0x14`, `+240` on y), and `0x5bd390` (per-room correction). Runtime uses the same constants for drops (`frame.c`).

Scale check on record (`data/placements.json`): "inside its room" passes 646/648 at the true 0.07, 648/648 at a wrong 0.05 and 477/648 at 0.09; the wall-fit test over 89 single-piece rooms gives median edge error 1.45 px (p90 3.93) at 0.07 against 3.5 (17.0) at 0.05, 3.1 (10.82) at 0.06, 3.3 (13.71) at 0.08, 3.58 (22.86) at 0.09 (`tools/extract/placements.py`).

### Events at HEAD

305 groups: 145 excluded, 103 unresolved, 57 drawn (`verification/event-audit.json`). The 57 marks: 24 at a trigger volume, 1 at a table row, 32 at room level (named `Event (room)` / `이벤트(방)`). Tags as observed (`verification/event-audit.md`): 2 and 14 volumes (384/394 and 11/11 groups), 17 an item of the room's table (2/2), 25 and 39 an enemy kind (14/14, 1/1, not used for position), 8 and 30 item use (30 is the door form), 18 room setup; the loader is `0x57d100` (up to 32 headers, stride 0x10) and the native dispatcher by tag was not found (`0x583260` is unrelated). Two reported cases: the Large Hall 3F key (`sh1d` g15, tag 17, done flag 178) and the Stinger's appearance (`tr0b` g6, tag 14, volume 4, need 120, done 78; that this group is the Stinger is an inference, movie 11 was not viewed). 23 puzzle (item-use) rows all have a trigger position (`puzzles_without_position` is empty); tag 30 is the door form (Hookshot in `ch01`, `ch03`, `ch0d`).

Script-given items (`placements.py`): 16 hand-listed rows (`SCRIPT_GRANTS`). The script classification gives 11 at a trigger volume and 5 at room level; `verification/state-flags.md` says 15 matched, 11 exact and 4 room level. They differ by one row; not reconciled.

### Dropped items

`src/core/frame.c`, test `tests/test_drops.py`.

| Item | Value |
| --- | --- |
| Slots | from the table count to `0x3e8` (saved slots end there); step `0x5c`; first row `+0x30`; link `+0x2c` |
| Valid | link not `0xffffffff` and `< DROP_ROOMS (175)`; kind `0x71` at row `+4`; position floats at row `+0x20` finite and below 100000 in magnitude (x, z) |
| Fields | item `+8`, amount `+0x3c` (Ink Ribbon x2 confirmed), position `+0x20..+0x2b` |
| Room | the slot's link (`+0x2c`) is the room id. Row `+0` is 0 for dropped rows and must not be used |
| Cap | 64 drawn (`MAX_DROPS`) |
| Projection | `drop_project` at `frame.c`: per room x piece base (`bx`, `by`) from `data/room-projection.json`, same formula as table rows; a point off the piece snaps to its edge; farther than 20 canvas px (`d^2 > 400`) counts as another floor's base; only pieces the current floor draws (`room_on`) |
| Item table | 181 ids: 147 with real names and art, 34 placeholders (Invalid Message, Nothing, `*-NULL`) that draw a plain grey square without a name |
| Class | weapons (including `Sub-Machinegun`, `Custom Handgun`, `Rocket Launcher` that have no placed row) = key; recovery = item; the class sets the name colour and the `[3]`/`[6]` toggles |
| Alpha | 65% (`0xa6`) times icon opacity |
| Names | on with `H`; drawn after all dropped icons (see the unexplained-order note in page 08) |

Observed live: slot 589 = Ink Ribbon, item 55, link 36, amount 2, position (1096.29, -1, 955.42), projected to canvas (672.6, 455.8) inside room 36's box (554, 350, 730, 516). Projection against the game's dots was within 0.4 px at 2560x1440. Slots 980-1091 are kind `0x70`, not items.

**Multi-floor limit.** Thirteen rooms span more than one floor (ids 14, 17, 36, 43, 45, 50, 65, 103, 111, 132, 134, 142, 166; recomputed from `data/room-projection.json` and `data/native-map.json`). Nothing found in the row says which floor a dropped item is on. Rooms 36 and 45 use an inferred height split (`DROP_FLOOR_Y` at `tools/build_labels.py`: room 36 below world y 300 is `1f` else `2f`, room 45 below 500 is `1f` else `3f`, "inferred, not native"); the other eleven draw on every floor where the point falls on that floor's piece.

**Partner and scenario.** Rows with the partner character, or a scenario change, were not traced. The only rows seen (rows-04) are 5 rows all in room 36 with `+0x1c` = 2 or 1; no partner or floor field was identified. F8 writes `-rows-NN.json` for further capture.

### Category rules

Two implementations share one weapon list. `tools/build_labels.py` (per-room catalogue rows) and `tools/extract/placements.py` (placed rows and the dropped-item table).

- `WEAPONS = (Knife, Handgun, Shotgun, Hunting Gun, Magnum, Magnum Revolver, Grenade Launcher, Submachine Gun, Molotov Cocktail)` are **key items** (project decision). Molotov Cocktail is a weapon, so a key item. The dropped-item table adds `Sub-Machinegun`, `Custom Handgun`, `Rocket Launcher` (weapons in the item table with no placed row, `build_labels.py`).
- Catalogue rows (`build_labels.category`): kind `weaponry` is key if the name is in `WEAPONS`, else common item; kind `items` is common if the name contains Herb, First-Aid, Ink Ribbon, Gas Tank or Empty Bottle, else key; `files` and `miscellaneous-objects` are files, except `Typewriter`, which is skipped because the game's map marks it already; `enemies` are enemies; characters get no mark.
- Placed rows and drops (`placements.category`): kinds below `0x10` (player classes) are none; `0x10..0x6f` enemy; only `0x71` and `0x78` are items; a name matching Map, Diary, Report, Notes, Notice, Manual, Orders, Regulations, Records, Photograph, Verse, List, About, Image is a file; `WEAPONS` is checked next and returns key; then a name containing Herb, First-Aid, Ink Ribbon, Gas Tank, Empty Bottle, Ammo, Grenade, Knife, Handgun, Shotgun, Hunting, Magnum, Molotov, Sub-Machinegun, Rocket or Machinegun is a common item (so ammo and grenades are common, and a weapon name never reaches this test); everything else is key.
- A weapon row's amount is rounds loaded, so weapons never show a count.

### Seen-items feature (deferred)

The "show only items already seen" mode (RE2 Remake style) is deferred. Findings: no native per-item seen state exists (an item-glint class `cItemLight` is tied to spawned actors, not a record); room visited flags exist and visited scope already gives room-level seeing; an item-level mode would need the mod to keep its own record in the INI and purge it on a game-clock regression (as the RE1 HD enemy-kill record does), which needs the game clock address and a save identity that were not traced.

### Unclassified

- Whether the placement-table layout (loc2 header, 32-byte records) has a counterpart in other RE titles: not checked.
