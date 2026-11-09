# 01 Features and controls

[한국어](01-features-controls.md) | [English](01-features-controls.en.md) · [Index](README.en.md)

Paths are relative to the RE0 project root. Citations name files and functions, not line numbers.

## General (any RE map mod)

### User-facing features worth having

| Feature | Rule |
| --- | --- |
| Room names | Drawn on the game's own map, in two languages, switchable at run time. |
| Category marks | Seven categories in legend order: locked doors, key items, files and maps, puzzles, events, common items, enemies. Each has its own colour (configurable in the INI), its own toggle and a legend row. Events (purple `?` diamond) are spoiler story scenes: cutscene triggers and enemy-appearance points; they are hidden once the event has happened. Puzzles (orange `!` diamond) are devices that need an item or a solution. |
| Master toggle | Hides all annotations; the legend stays so the toggle can be read and undone. |
| Room names toggle | Names only, independent of marks. |
| Room scope | Three levels: visited rooms, rooms revealed by a held map, every room of a drawn floor. |
| Item names | Three states, one key cycles them: all, all except common items, off (default off). The legend row names the current state. In "all except common" only common-item names (and dropped common items' names) go; every other name keeps its place. |
| Sizes and opacities | Name size, name opacity, icon size, icon opacity, each with its own keys, 10-step changes and clamped ranges. |
| Legend | Bottom-left panel; rows turn grey when their category is off; one key folds it to a single hint line. |
| Readout panel | Bottom-right panel showing the four size and opacity values; folds with the legend. |
| State following | Marks disappear when the item is taken, the puzzle solved, the door unlocked, the enemy killed. Difficulty is read from the game, not asked from the user. |
| Dropped items | Items the player drops are drawn too (see page 05). |
| Debug capture | One key writes the current map geometry, progress flags and a sprite dump next to the mod for offline replay. |

### Control rules

- Keys act only while the mod's own overlay is being drawn on the map and the game window has focus. Keys also reach the game; choose keys the game does not bind. Read the game's `config.ini` key list before assigning.
- Prefer Ctrl over Shift for modified keys when the game binds Shift (aim, run). Avoid Alt.
- Debounce every toggle with a rest period: one physical press was seen to fire three times 200 ms apart in the live log.
- Persist every changed setting immediately, through a temporary file and an atomic replace. If saving fails, keep the previous file and log the failure.
- Keep the `0`-`9` rows in the legend as entries (with brackets); write the hints for the other keys in one form: keys, then label, then value, `/` between alternatives, `+` for combinations, no brackets.
- A setting with a debug-only key (room selection) is not saved and has no legend line.

### Settings file rules

- Keep a `Version` key. When a scale changes, convert old values once, rewrite the file with the new version, and never convert twice.
- A missing size key takes the default; opacities are scale-free and kept.
- Clamp every value on read; a bad value must not stop the mod.
- A setting that only matters when the game cannot answer (difficulty in random modes) stays in the file but has no key.

## RE0 HD Remaster specific

### Keys

Source: `src/core/frame.c` `re0_settings_key` (meaning), `src/runtime/re0_map.c` (key mapping), `README.md` (user text).

| Key | Action | Range / step | Saved |
| --- | --- | --- | --- |
| `0` | All annotations on/off (`enabled`) | | yes |
| `1` | Room names on/off | | yes |
| `2` `3` `4` `5` `6` `7` `8` | Locks, Key items, Files/Maps, Puzzles, Events, Common items, Enemies (`re0_legend_category`: category ids 0 1 2 3 6 4 5, bits of `Contents`) | | yes |
| `9` | Scope: Visited, Revealed, All rooms | 3-cycle | yes |
| `\` (`VK_OEM_5`; `₩` on Korean keyboards) | Korean/English | | yes |
| `-` `+` (also numpad) | Name size | 50-150, step 10 | yes |
| `[` `]` | Name opacity | 10-100, step 10 | yes |
| `Ctrl` + `-` `+` | Icon size | 50-200, step 10 | yes |
| `Ctrl` + `[` `]` | Icon opacity | 10-100, step 10 | yes |
| `H` | Item names: all -> all except common -> off -> all (a cycle, not hold) | | yes |
| `~` (`VK_OEM_3`, left of `1`) | Fold or show the legend; the readout panel goes with it | | yes |
| `,` `.` | Select previous/next room (debug; panel with the room's exits and contents) | | no |
| `F8` | Capture (see page 07) | | no |

Facts:

- Digits are the top row (`VK_0`-`VK_9`); numpad digits are not read. Numpad `+` and `-` are read (`re0_map.c`).
- Foreground window must belong to the game process (`re0_map.c`). The key handler runs before the draw gate (`re0_map.c` then `508`), so keys work while a capture exists even if the gate holds the overlay back.
- Debounce 350 ms per key (`re0_map.c`).
- Ctrl, not Shift: the game's `config.ini` binds `KC_kamae=KB_SHIFT`; no game binding uses Ctrl (`re0_map.c`). The map screen's own input code was not traced, so Shift's effect there is unknown.
- `~` is bound by no key in the game's `config.ini` (keys listed there: W A S D Space Shift F arrows E V R Q C). Whether the map screen reads other keys was not traced.
- The mod reads no gamepad input.
- `RE0Settings.hidden` (a "held H hides names" state, `frame.c`) is never set by the runtime; the comments mentioning "held H" (`frame.c`, `frame.c`) are stale. H is a toggle for item names.

### Legend and readout layout

Source: `src/core/frame.c`, `tools/build_labels.py`, `src/core/frame.c` (`lk = height/1440`).

| Item | Value |
| --- | --- |
| Legend position | Bottom-left; margin `28*lk`, padding `12*lk`, row pitch `30*lk` where `lk = height/1440` |
| Legend background | `0xd0080808` (ARGB) |
| Legend rows | Title `지도 메모` / `Map Notes`, then two columns: left `[0] All`, `[1] Rooms`, `[2] Locks`, `[3] Key items`, `[4] Files/Maps`; right `[5] Puzzles`, `[6] Events`, `[7] Items`, `[8] Enemies`, `[9]` scope (Visited / Revealed / All rooms). User 2026-11-08 |
| Hint line | One line under the grid: `[H] Item names: All / No common / Off` under the left column, `[\] 언어: 한국어` / `[\] LANGUAGE: ENGLISH` (current language) under the right, hint size, the same colour (grey when item names are off) |
| Panel width | The left column is as wide as the widest `[H]` state, so the panel holds still as `H` cycles (today the grid rows are wider, so it is the grid that sets the width); the fold hint `~ Hide` sits beside the title; folded legend shows `~ Legend` |
| Row off state | Same row in dark grey `0xff6a6a6a`, darker than the common-item grey so it stays distinct (also when `0` turns everything off) |
| Row on colours | `[0]` white; `[1]` cream `0xfff0e2be`; `[2]`..`[8]` the category colours (page 02) |
| Readout panel | Bottom-right with the same margins mirrored; four rows (name opacity, name size, icon opacity, icon size), 20 px raster, values gold `0xffffe080`, right-aligned in a column as wide as `100%`; hidden while the legend is folded |
| Readout hint strings | `[ / ] Name opacity`, `- / + Name size`, `Ctrl + [ / ] Icon opacity`, `Ctrl + - / + Icon size` (`build_labels.py`) |
| Legend and panels vs map | Legend, readouts and room panel are drawn on top of the frame and are obstacles for marks and names |
| Hints removed in 44 | The select-room line and the "(pickups, puzzles, kills tracked)" line |

When the name count under a room is shown instead of marks (view not accepted, see page 03), the badges are the letters `L K F P I E V` (by category id; `V` never has a count) followed by a digit capped at 9 (`frame.c`, `build_labels.py`).

### INI

`packaging/RE0.AnnotatedMap.ini`; loader `re0_map.c`; writer `re0_map.c`.

| Key | Default | Meaning |
| --- | --- | --- |
| `Version` | 52 | `RE0_SETTINGS_VERSION` (`frame.h`) |
| `Legend` | 1 | Legend shown |
| `Enabled` | 1 | `0` key |
| `English` | 0 | `\` key |
| `Names` | 1 | `1` key |
| `NameSize` | 100 | 50-150 |
| `NameOpacity` | 60 | 10-100 |
| `IconSize` | 100 | 50-200 |
| `IconOpacity` | 80 | 10-100 |
| `ItemNames` | 0 | `H` key: 0 off, 1 all, 2 all except common items |
| `Difficulty` | 1 | 0 Easy, 1 Normal, 2 Hard. Used only when the game's table cannot give a difficulty (random modes); no key (`re0_map.c`) |
| `Visibility` | 0 | 0 Visited, 1 Revealed, 2 All rooms; the name is RE1 HD's (`re0_map.c`) |
| `Contents` | 63 | Category bit mask by category id, bit 0 locks, 1 key items, 2 files, 3 puzzles, 4 common items, 5 enemies, 6 events. Events are spoilers and start off (user 2026-11-08), so the default is 63 |
| `[Colors]` | see below | `Lock`, `KeyItem`, `File`, `Puzzle`, `Event`, `Item`, `Enemy`: `#RRGGBB`, defaults `FFCD46 5ADCFF FF8CD2 FF9628 B070FF B8BCC4 EB3C3C`. A missing or malformed value keeps the shipped colour (`re0_map.c` `colors_load`, `re0_color_parse`) |

In-code defaults: `frame.c`.

### Migration

- The 100% defaults equal the earlier 110% names and 130% icons: the on-screen size is multiplied the on-screen size by `NAME_SIZE_BASE 1.1` and `ICON_SIZE_BASE 1.3` (`frame.c`).
- An INI without `Version=44` is read on the old scale once: `new = clamp(int(old/base + 5)/10*10)`, base 1.1 for names, 1.3 for icons (`frame.c`). 110 -> 100 and 130 -> 100 exactly. Absent keys -> 100. The file is then rewritten with `Version=44` (`re0_map.c`).
- Tests: `tests/test_review44.py` (new defaults, one-time conversion, a converted file is left alone, every old grid value keeps its screen size within half a step).

- Before `Version=50` `ItemNames` was on/off. `re0_settings_item_names` reads any non-zero value of an older file as 1 (all) and 0 as 0 once, and the file is rewritten with `Version=50`; from then on 0-2 are kept and anything else is 0. The size conversion above stays keyed to `Version` below 44 (`RE0_SIZE_SCALE_VERSION`).
- Tests: `tests/test_review50.py`, the contract's `item_name_states`, the native-dispatch INI gate, and their mutants.

- Before `Version=52` the event bit (64) is cleared once: events were puzzles with a flag until 51, and a later version copied the puzzle bit into them; `re0_settings_contents` now gives 63-or-less for any older file (so a file saved at 51 with events on also goes off). From Version 52 the user's choice is kept (`H`-style toggle on key `6`, saved). Legend numbering changed with 51 (see Keys); keys are not saved, so only `Contents` needs the migration.
- Saving edits the INI in place (`re0_ini_merge`): only the `[Map]` keys change; comments, key order and the user's `[Colors]` stay, a file without `[Colors]` gets the defaults appended. Tests: `tests/test_review51.py`, the contract's `category_rules` (merge cases, colour parsing, event bit), the native-dispatch INI gate (`Contents`, `[Colors]` through the real loader) and their mutants.

### Other files the mod writes (next to the ASI)

`RE0.AnnotatedMap.log`, `RE0.AnnotatedMap-capture.json`, `RE0.AnnotatedMap-sprites.json` (schema 2), `RE0.AnnotatedMap-rows-NN.json` (NN 01-32, never overwritten), and `.tmp` copies during writes (`re0_map.c`, page 07).

### Unclassified

- Whether the `~` fold behaviour and the readout panel suit games whose map screens bind more keys: not checked.
