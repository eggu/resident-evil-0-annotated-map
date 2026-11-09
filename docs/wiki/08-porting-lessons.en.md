# 08 Porting checklist and lessons

[한국어](08-porting-lessons.md) | [English](08-porting-lessons.en.md) · [Index](README.en.md)

Paths are relative to the RE0 project root. Citations name files and functions, not line numbers.

## Summary: every rule, general or RE0-specific, and where it is

"General" rules can be copied as written. "General rule, RE0 values" means the rule is general and the numbers were tuned for RE0, so re-derive them. "Unclassified" means it could not be decided from the sources.

| # | Rule | Class | Page |
| --- | --- | --- | --- |
| 1 | One shared C decision module for ASI and emulator | General | [06](06-runtime-rendering.en.md), [07](07-verification.en.md) |
| 2 | Canvas model, view inferred from captured room boxes and accepted only within tolerance | General rule, RE0 values (2%, 4 px, 1280x720) | [02](02-display-spec.en.md) |
| 3 | Name zoom curve and per-category icon gain, one function for mark size | General rule, RE0 values (0.7, 1.3, 0.96 to 1.5) | [02](02-display-spec.en.md) |
| 4 | One colour per category shared by legend, name, badge; off row grey | General rule, RE0 values (RE1 HD sampled) | [02](02-display-spec.en.md) |
| 5 | Orange `!` diamond puzzle, purple `?` diamond event, drawn shapes | General | [02](02-display-spec.en.md), [04](04-icon-art.en.md) |
| 6 | Mark-name wrap: count on line 2, 8+ characters at nearest space, never split a word, alignment toward icon | General | [02](02-display-spec.en.md) |
| 7 | Drop the Korean particle `의` in item names with a kept-exceptions list | General rule (Korean); the list is RE0-specific | [02](02-display-spec.en.md) |
| 8 | Dropped-item icon on the game's own dot at 65% | General if the game draws such a dot; otherwise unclassified | [02](02-display-spec.en.md), [05](05-data-conditions.en.md) |
| 9 | Room names fixed at generation, at the pole of inaccessibility of the real shape | General | [03](03-placement-rules.en.md) |
| 10 | Corridor leader lines with a length cap; 150% wrap | General rule, RE0 values (60 px, 150%) | [03](03-placement-rules.en.md) |
| 11 | Room names drawn first and excluded from collision | General (a style choice) | [03](03-placement-rules.en.md) |
| 12 | Mark tiers, collision weights, drop rule, event beside key | General rule, RE0 values (weights 8/4/1) | [03](03-placement-rules.en.md) |
| 13 | Lock key centred on its door, never moved | General | [03](03-placement-rules.en.md) |
| 14 | Duplicate pickups listed twice show once | General | [03](03-placement-rules.en.md) |
| 15 | Out-of-room positions snapped to the room shape and flagged | General | [03](03-placement-rules.en.md), [05](05-data-conditions.en.md) |
| 16 | Avoid the game's frame when drawing at Present; marks and names go together | General approach | [03](03-placement-rules.en.md) |
| 17 | The 14 frame rectangles (measured at 2560x1440) | RE0-specific | [03](03-placement-rules.en.md) |
| 18 | Whole-data audits, not examples | General | [03](03-placement-rules.en.md), [07](07-verification.en.md) |
| 19 | Key rules: Ctrl not Shift when the game binds Shift; debounce; atomic INI; `Version` and one-time migration | General | [01](01-features-controls.en.md) |
| 20 | The key bindings, INI keys and legend text | RE0-specific | [01](01-features-controls.en.md) |
| 21 | Icons: large source shown small, never upscaled, premultiplied mips, separate icon texture, edge darkening | General | [04](04-icon-art.en.md) |
| 22 | White-rim bug (RGBA resize un-premultiplies) | General | [04](04-icon-art.en.md) |
| 23 | The art itself, per-icon fixes, herb mixes, MO Disk padding | RE0-specific | [04](04-icon-art.en.md) |
| 24 | Art generation method, "A style" choice, elongated-item redesign, the 24 px mistake | RE0-specific (the lesson in it is general, row 49) | [04](04-icon-art.en.md), [08](08-porting-lessons.en.md) |
| 25 | World position to canvas through the game's own transform run in an emulator; scale proved by wall fit | General approach | [05](05-data-conditions.en.md) |
| 26 | The transform constants (0.07, 1.5, 163, -357), addresses, regions | RE0-specific | [05](05-data-conditions.en.md) |
| 27 | Condition byte to flag; unreadable flags mean off | General approach | [05](05-data-conditions.en.md) |
| 28 | Flag base 0x312, array address, Leech Hunter rewards | RE0-specific | [05](05-data-conditions.en.md) |
| 29 | Done state from the placement manager; table told by row count; kills read from actor lists | General approach, RE0 offsets | [05](05-data-conditions.en.md) |
| 30 | Event audit by forced-flag walk; excluded/unresolved/script_read | General method | [05](05-data-conditions.en.md) |
| 31 | Script tags, counts, Stinger and Large Hall cases | RE0-specific | [05](05-data-conditions.en.md) |
| 32 | Dropped items read every frame; validity by link; floor filter | General approach | [05](05-data-conditions.en.md) |
| 33 | Slot layout, 13 multi-floor rooms, partner and scenario | RE0-specific | [05](05-data-conditions.en.md) |
| 34 | Weapons are key items; Molotov is a weapon | General; lists RE0-specific | [05](05-data-conditions.en.md) |
| 35 | "Show only items already seen" | Unclassified (deferred; needs per-game save identity) | [05](05-data-conditions.en.md) |
| 36 | Hook GUI classes at vtable slots, thread-local map context, call original first | General approach | [06](06-runtime-rendering.en.md) |
| 37 | Guard by executable SHA-256, base, build string, code prefixes | General rule, RE0 values | [06](06-runtime-rendering.en.md) |
| 38 | The hook addresses, field offsets, render rectangle | RE0-specific | [06](06-runtime-rendering.en.md) |
| 39 | Draw at Present with full state block save and restore | General | [06](06-runtime-rendering.en.md) |
| 40 | Fade gate and generation latch for stale captures | General | [06](06-runtime-rendering.en.md) |
| 41 | Frame state from a sprite of unique size | General method; sizes RE0-specific | [06](06-runtime-rendering.en.md) |
| 42 | Texture memory budget in a 32-bit game | General rule, RE0 values (64 MiB + 10.66 MiB) | [06](06-runtime-rendering.en.md) |
| 43 | Counter on every drop path; capped logs | General | [06](06-runtime-rendering.en.md) |
| 44 | Native dispatch gate with mutants from live failures | General | [07](07-verification.en.md) |
| 45 | Live capture: copy before overwrite; screenshot at same moment | General | [07](07-verification.en.md) |
| 46 | Install rules (gate passed, game not running, hashes, atomic) | General | [07](07-verification.en.md) |
| 47 | Evidence levels and "what was not exercised" | General | [07](07-verification.en.md) |
| 48 | Enemy icons: heads only, human and animal types, distinguishable per kind (carried from RE1 HD) | General | [04](04-icon-art.en.md) |
| 49 | Derive asset size from the largest on-screen size, not from a constant | General | [04](04-icon-art.en.md), [08](08-porting-lessons.en.md) |

## General (any RE map mod)

### Porting checklist, in order

1. **Pin the build.** Hash the executable, record the image base and a build string, and refuse anything else. Record the as-of date and hashes of every inspected file.
2. **Find the map's GUI classes.** Identify the map object, the room instance and the sprite classes and their virtual-table slots; confirm by class-name CRC. Several classes look alike; the wrong one is easy to hook first.
3. **Capture room boxes.** Union the sprite boxes per room; keep small non-room sprites as obstacles. Infer the view and accept it only within tolerance.
4. **Extract placements.** Parse placement tables strictly; run the game's own transform; prove the scale with a test that a wrong scale fails.
5. **Find the flag array and the placement manager.** Write the condition rule, the done rule, the kill rule and the difficulty rule; read nothing without a readability check.
6. **Decide categories.** Six categories in a fixed order with fixed colours; weapons are key items; characters unmarked; objects the game already marks skipped.
7. **Generate names and icons.** Pre-render names near their display size; one text atlas, one icon texture with mips; check the 32-bit memory budget.
8. **Lay out room names at build time** from room sprite alpha (pole of inaccessibility, leaders, wrap), with an independent check that stops the build.
9. **Write the shared frame module** (marks, tiers, names, drops, legend, readout); add the contract and its mutants.
10. **Hook and draw at Present** with the fade gate and the generation latch; restore all device state.
11. **Measure the frame** (chrome) from a live sprite dump at the resolution you support; record the resolution.
12. **Build the native dispatch gate and mutants** before the first live test; add counters to every drop path.
13. **Live loop:** capture, copy, compare, add a mutant, add a fixture value.
14. **Documents:** a first-time-user README (install, keys, limits) kept apart from internal records; never put test counts, progress or validation history in a public README.

### General lessons

- A hook reached by calling it directly proves nothing; reach it through the real vtable slot and check class identity.
- Test inputs must cover the full packed range of a field; native code may mask bits the author never saw set.
- A hook path that drops data silently hides every later failure; give each a counter.
- D3D output cannot be tested offline. Draw at Present, restore all state, and keep a live checklist.
- Test the state after loading a save, not only after a new game.
- A rule proved by an inside-the-room test can still use a wrong scale; add a control that must fail.
- Treat a report as one example of a class; fix and test the whole class.
- Derive asset size from the largest size it is shown at, never from an unexamined constant. Pre-render text near its display size; never stretch small rasters; do mips on premultiplied channels and test the edge brightness at every level.
- Time windows do not fix stale draws when another mod changes timing; use a latch tied to events.
- Copy live capture files before the next capture overwrites them; ask for the resolution and a full screenshot with every report.
- Give every build that may be installed its own number.
- When the cause of a live symptom is not proven, keep the working order or workaround, say so in the record, and do not claim a fix.

## RE0 HD Remaster specific

### Mistakes made in this project and how each was found

| Mistake | How it was found | What prevents it |
| --- | --- | --- |
| Instance hook placed on a neighbouring class's slot (`cGUIInstAnimVariable` instead of `cGUIInstAnimation`) | Live: no room identified; offline probe had called the hook directly, so the slot was never used | Reach hooks only through real vtable slots; check class identity by CRC |
| Sprites refused because anchor `0xff5` was rejected as > 10 | Log: `badquad` = 18 per map draw, `room=0` | Differential tests over the field's full packed range; native masks the low bits |
| Silent drops in hooks | Nothing reported the loss until a `Diag` line existed | A counter on every drop path |
| Overlay invisible at `EndScene` | Live: no display; after moving to Present it drew in the live game | Draw at Present; accept that D3D needs a live test |
| Table told by a mode field that is 0 after loading a save | Live: taken items and unlocked doors stayed shown after a load | Test the loaded-save state; identify tables by row count |
| Kill read from a row byte that every saved actor sets | Cerberus kill stayed marked; native code re-read (`state-flags.md`) | Run the native save routine in the gate, with an enemy row and an actor |
| Mark or room name tied to one piece of a multi-piece room | Ice Pick live report (mutant `mark tied to one piece of its room` in `verification/native-dispatch.json`) | Treat a place as all its pieces on the floor |
| Event marks absent | Reports of two missing events; cause was missing data, not logic | Audit every script group with a forced-flag walk |
| Scale constant "verified" by an inside-room test | The test passed at a wrong scale 648/648 (`data/placements.json` `sensitivity`) | Wall-fit test; always run a wrong-scale control |
| Room-level marks and names at the bounding-box centre | L-shaped rooms put them outside; pole of inaccessibility fixed it, 135 of 248 names moved (`placements.py`) | Use the real shape, check all anchors lie in it |
| Icons stretched from a small raster looked blurred | Names rastered at 20 px and stretched 1.65x read as blurred (`build_labels.py`); icons moved to 96 px sources shown small | Raster near display size; never upscale |
| White icon rims | Live; cause was RGBA `resize` un-premultiplying | Channel-wise premultiplied reduction; refuse a brightening chain; whole-set edge test |
| Icons exported at 24x24, 16 colours, binary alpha because `icon_size=24` was hard-coded; on screen they are `18 * height/720` (27 px at 1080p, 54 px at 2160p), so they were upscaled and lost detail | Found in the icon review; changed to a 96 px source shown small (page 04) | Derive asset size from the largest on-screen size, never from an unexamined constant |
| Mips on the shared atlas | Would add 21 MB and bleed across 2 px gutters into text (`build_labels.py`) | Separate icon texture with its own sampler state |
| Rows dump using row `+0` as the room | Live slot 589: row `+0` was 0, the link `+0x2c` held 36 | Read live samples before coding the layout; mutant `dropped room read from row +0` |
| Freed drop slot drawn from stale bytes | rows-03 showed item 32 with link `0xffffffff` | Validity is the link, mutant `freed slot draws its stale bytes` |
| Dropped item names not visible | Names missing in a screenshot; reordering to all icons then all names made them appear; **cause not proven** | Unresolved: keep the order and say so |
| Frame rectangles from one resolution | The overlay draws after the frame, so rectangles were measured from a 2560x1440 shot | Known limitation; re-measure per supported resolution |
| Stale capture redrawn after the map closed | With `RE0.NoUIWait` fast fades the capture reappeared | Generation latch instead of a time window |
| Pan size report never reproduced | Logging and a test were added; it did not reproduce | Log inputs at the moment of report; do not change drawn values without evidence |
| Capture overwritten | Sprite dumps and captures overwrite the previous file | Copy before pressing again; numbered rows dumps |
| Review-only build overwrote an earlier ZIP | Same build number | Bump the number for every build that may be installed |
| Captures all at one resolution while play was at another | All captures were 1080p, the log showed 3840x2160 | Ask for the resolution with every report |


### What not to copy

Everything listed "RE0-specific" in the table above: addresses and offsets (page 05, 06), the 14 frame rectangles, the transform constants, the Leech Hunter condition rewards, the 13 multi-floor rooms and `DROP_FLOOR_Y`, the herb mix ids 46-51, the art, the Korean name list, and the INI keys.

### Known limitations (plain statement)

1. Frame rectangles were measured from a 2560x1440 screenshot. Other resolutions, aspect ratios, transition animations and maps other than the shot's are not verified. A mark touching a rectangle is hidden whole.
2. Dropped items in 13 multi-floor rooms (14, 17, 36, 43, 45, 50, 65, 103, 111, 132, 134, 142, 166) cannot be assigned to a floor from the data. Rooms 36 and 45 use an inferred height split; the other eleven draw on every matching floor.
3. Partner and scenario differences in the placement tables were not traced.
4. The "show only items already seen" feature is deferred.
5. Event contents were not seen; `script_read` only says a done flag exists. The Stinger identification of `tr0b` g6 is inferred.
6. Easy/normal/hard are inferred from table row counts (647/589/568), not checked against a difficulty menu.
7. Room names in Korean are project translations.
8. Windows and mods other than `re0box`, FusionFix and `RE0.NoUIWait` were not tested.
9. In-game confirmation is outside the scope of this wiki (see page 07 for the verification procedure).

### Documentation and code mismatches

| Where | Document says | Code says |
| --- | --- | --- |
| `schemas/render-contract.md` | Instance vtable `0xd254b0`; EndScene draw, snapshot consumed once, 100 ms | Instance slot `0xd25478` (vtable `0xd25448`); Present draw, 250 ms plus latch |
| `docs/DEVELOPMENT.md` (ASI adapter section) | EndScene consumes each snapshot once; older than 100 ms refused | Same as above |
| `tools/build_labels.py` comment | Atlas is 32 MB (4096x2048) | 4096x4096, 64 MiB (`labels_generated.h`) |
| `tools/extract/room_layout.py` docstring | Names never overlap key items, documents, locks, puzzles | Names ignore marks (`room_layout.py`, `frame.c`) |
| `frame.c` comments | "held H" hides names | H toggles item names; `hidden` is never set |

### Facts that could not be verified from the sources

- The overlap-audit counts (script missing).
- The number of frame mutants (57) is a pattern count of `tests/test_frame.py`; 189 tests and 73 native mutants are taken from `native-dispatch.json`; no test was run for this wiki.
