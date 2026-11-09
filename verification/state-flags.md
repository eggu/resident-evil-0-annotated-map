# Done state of displayed rows

Static analysis of `re0hd.exe` (analysis image) and the event scripts, plus Unicorn runs of native functions. No run of the game. Reproduce with `tools/crosscheck/state_flags.py --game <path>`. Per-row data: `state-flags.json`.

## Table items, key items, files (kind 0x71)
Store is the arrange manager `[0xdcc010]`, not the flag array. It holds 0x4e8 slots of 0x5c bytes: slot+0x28 next link, slot+0x2c room link, slot+0x30 row (the loaded record).

- Row fields: +0 room, +4 kind, +8 item, +0xc byte 2, +0x10 byte 3, +0x14 byte 4, +0x18 amount, +0x1c byte 5, +0x20 position, +0x2c rotation, +0x39 taken byte, +0x3c current amount or HP, +0x41 has actor state.
- Pickup: `0x4de730` frees the actor. Slot below the table count (`[mgr+0x24fac]`): row kind is set to 0 at `0x4de816`. Slot at or above it (dropped item): `0x412060` frees it.
- Respawn: `0x410bf1`-`0x410bf7` returns no actor when kind is 0, `0x410c02` when +0x39 is set, `0x410c0b` for kind 0x78. The room loader loop `0x411b9d`-`0x411bb1` has the same tests.
- Persistence: `0x4115d0` copies the first 0x3e8 slots into the save at `0x6138c0`; `0x4103e0` restores them at `0x612849`.
- Slot of a loc2 row: rooms ascending (`0x412110` loops 0..0xae), file order inside a room, free list from 0 (`0x4101f0`, `0x40fb10`). So slot = rows of earlier rooms + index in room, per table. `0x61ff70` maps room aliases, and no table key is an alias.
- Table per mode: `[mgr+0x24ff0]` 0, 1, 2 select `loctbl0000/0100/0200` (`0x4111ff`). Mode 3 picks a random `loctbl030x`. Easy/normal/hard naming stays inferred from row counts.

Read rule: not done unless mode is 0..2, count equals 647/589/568, and row+0 and row+8 hold the expected room and item. Then done when row kind is 0 or `[mgr+0x2c+slot*0x5c]` is -1 (script `ObjDeleteType` frees a slot through `0x5745a9`).

## Script-given keys (kind 0x78, 18 rows)
Kind 0x78 never spawns. The item comes from a script group, which sets a flag in the bit array. Row +0x39 is only set when a key left on the floor is taken (`0x5e6b60`), so it does not cover the normal case.

## Puzzles and locks
Flags of the bit array `[0xdcc014]+0x20`, done when set. Largest is 0x19c, so 13 words are enough. The array has 71 words (`0x59ba39`).
A lock is proven when the tag 31 group holding `door(target)` reaches it with the flag forced to 1, and with the flag 0 only after writing it. A puzzle is proven when the tag 8 group with y = item writes the flag, with `item_sub` where the item is consumed. A flag that any reachable script clears is not called proven.

Polarity: `ResFlag` puts the bit in the result (`0x576b60`), `CmpRegImm` subtracts (`0x576960`), `je` jumps when the result is 0 (`0x576570`).

## Rows with no flag
- Hookshot, 4 rows: reusable shortcuts with no done state.
- Lock "Key" at room 12: `door(13)` is unconditional and its `key_check(64)` subroutine is unreachable. Not a lock.
- MO Disk locks at rooms 45, 53, 43: no script in those rooms touches MO Disk. The only use site is sh0b.

## Corrections to earlier notes
- Handler column: the command table is handler, format, name. `Commands.ops[k][2]` holds the next command's handler. The real handler of command k is at `0xcd57dc+12*k-4`. Formats and names are right.
- `event_disasm.groups()` ends a group at the next header's offset. A next offset of 0 gives an empty group (33 main-game groups, including the Motherboard use in pl0b g6), and other groups run on into their neighbours, which attributes writes to the wrong group. A scan that follows control flow fixes both. The SetEnemyFlag bytes and values behind `arrange-conditions.json` are unchanged.
- Script scene twins `<scene>b` have unguarded doors and match the Leech Hunter room range; only the base script applies to the main game (inferred).
- Magnetic Card puzzle row is at room 0 from the external page. Its use group is in tr0a/tr1a (rooms 10, 26).

## Unicorn checks (0 mismatches)
`0x59b8d0` over 0..0xffff; `0x40fd70` over every slot; `0x410610` and `0x410bb0` up to `0x410c36` over all kinds; `0x4101f0`+`0x40fb10` slot order for the three tables; `0x4de730` on every table slot followed by the spawn gate; `0x412060` on table and dropped slots.

## Not exercised
The running game; the UI path that calls `0x4de730` (read statically from `0x5d85c6`, `0x5d8cb0`, `0x5e67a0`, `0x5e69b8`); the table loader `0x412110` itself; the save and load functions; real saves; event script execution, which is evaluated here and not run. Script conditions other than the forced flag are treated as either way.

## Enemies
Read from native code. This corrects the earlier note here, which took row+0x41 with row+0x3c at or below 0 as the kill: `0x412c30` keeps `esi=mgr+0x28+slot*0x5c`, so its `[esi+0x41]` at `0x412d7a` is row+0x39, the taken byte, and row+0x41 is `[esi+0x49]` at `0x412ce8`, set for every saved actor. Most classes also return before storing HP at death, so row+0x3c does not hold the kill either.

- Save: `0x412c30` stores the actor into its row and calls vtable +0x94. Return 1 sets row+0x39; return 2 frees the slot through `0x412060`.
- Class rule: `enemy_save_runs` runs each class's +0x94 with HP given by native setter `0x529310`: all 32 classes with rows but uEnemy47 return 1 at HP 0 and below, and 0 at HP 1 (`native_checks.enemy_saves`). Cerberus is uEnemy2a, `0x4d7880`.
- Respawn: `0x410c02` and the room loop `0x411ba8` refuse a row with +0x39 set. Row +0x39 and the rest of the row go through save `0x4115d0` and restore `0x4103e0`.
- When a row is written: when a room unloads, `0x61dde0` -> `0x61d2c0` -> walk `0x51fd40` -> `0x61d510` -> `0x412c30`, and at a save, `0x613854` -> `0x61d460`. Nothing writes it at the moment of death.
- Still in the room: the actor holds it. The ASI walks the lists as `0x51fd40`: `[[0xe2d434]+layer*0x18+0x2c]`, next +0x14, layers 9, 0xc, 0xd (`0xccfeb0`), skipping state +0xc&7 of 3 or 4 (`0x5201d0`), slot +0xff0, HP +0x1030. Item and player actors hold HP 0 too, so the row's kind must be an enemy (`0x61d544`: 0x10..0x6f without 0x3b).

Read rule: row+0x39 set, kind 0, link -1, or an actor on the slot with HP at or below 0. Polarity: nonzero byte means gone, HP at or below 0 means dead.

Limits:
- uEnemy47 (Queen Leech second form, 1 row, room 165): its +0x94 is the default `0x5290a0`, which returns 0 and stores no HP, so nothing marks the row. It goes while its actor is on the list at HP 0 and comes back after the room unloads.
- A class's +0x94 also returns 1 for state flag 8 at HP above 0, and the zombie class for flag 0x8000. The row follows at unload; the live read only sees HP.
- If an actor is deleted before its room unloads, native code saves nothing and the row stays live, so the mark returns, as the enemy would. Which classes do this was not traced.
- The review page has no actors. Under `finished` it sets +0x39 as native code leaves it; the live path is covered by the gate.

Decisions:
- Script-spawned enemies: `SetEnemyFlag` only enables table rows (`0x4109f0`), which have slots and follow the rule above. No other enemy spawn route was traced, and an actor without a table slot has no mark.
- Several rows at one spot: each table record is now its own row. Four leech places hold one record per condition 173 and 174 (pl0b g4 clears 173 and sets 174, so never both), and room 104 holds two equal records. One mark would have read only the last slot, and `condition_also` and the `also` field are gone.
- Row guard: room, kind or 0, and item except for enemies, as `0x412c30` rewrites row+8 from actor +0xfe8.

Kinds: 2 and 5 are uPlayerRebecca and uPlayerBilly (150 and 250 HP in the amount field), wrongly marked Zombie by the co-occurrence naming; removed, 6 rows. 0x6a and 0x6b are enemies of the zombie family that the old `kind<0x60` dropped; added, 14 rows. Names of all enemy marks remain the inference in `enemy_names`.

## Script-given items
`SCRIPT_GRANTS` in `tools/extract/placements.py` lists 16 rows, each checked here against its own group. `script_row` reports per row. `only_external` in `placement-crosscheck.json` now carries a class:

- 15 rows per difficulty matched by these. Exact at a trigger volume (11): Handgun Ammo x15 (tr02 g9), Hookshot Operator's Manual, Microfilm Image, Marcus' Diary 1, Old Photograph, and 6 chemical stations. Room level (4): Brake Operation Manual and Gate Operation Manual (automatic events, tags 6 and 36), Handgun Ammo x30 and Player's Manual 2 (tr0f cut-scene, tag 12).
- Not in `only_external`, added: Handgun Ammo x16 in ch0e g3, flag 0xec. The table has another Handgun Ammo there at another spot, which the catalogue row matches, so the catalogue lists one where the game gives two. Its volume falls outside the room's piece, so it is room level.
- `inside-item` (6 per difficulty, left out): Blue Keycard, Silver Ring, Angel Wings, Black Wing, Handgun Parts, Blue Leech Charm. The catalogue says each is inside an inventory item, and no script group gives them. Their containers are marked. Where the game gives them was not traced.
- `catalogue-repeat` (15, 12, 11, left out): one physical room on two floor pages, whose one table row is consumed by the first page: main hall, large hall, boiler room, platform, turntable yard.

Handgun Ammo x15, the Officers' Car row: `tr02 g9 tag 2 x=9`. On Edward's body after he comes through the window (catalogue). The group needs 0x41 set (tr02 g6 only) and 0x79 clear, then gives item 32 x15 and sets 0x65 when taken. 0x79 is written once, by tr00 g3 entering the engine cab, and no group clears it, so either flag ends the row.

Trigger volume: a tag 2 group's `x` picks list x of member `<scene>b`. This is an observed fit, not read from native code: on the 18 kind 0x78 rows, whose table position is independent, that list is the nearest to the position in 15, and contains it in 10. Keycard (pl0c) is 314 away, so a single row can be wrong.

Difficulty: no script command tests it, and the catalogue lists each row in all three. Chemical stations have no flag and stay shown. Gate Operation Manual is `inferred`: 0x179 follows the grant on a one-shot event with no reader. Script twins and alternate scenes (tr10, tr1b for tr02) share these flags and were not given rows.
