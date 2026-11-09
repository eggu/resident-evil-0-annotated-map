# RE0 HD annotated map mod wiki

[한국어](README.md) | [English](README.en.md)

Reference for reusing the features, specs and placement rules of the Resident Evil 0 HD REMASTER annotated map mod (project `resident-evil-0-annotated-map`) in other map-mod projects: RE1, RE1 HD, RE2, RE3, Dino Crisis. This is a developer reference, not a user manual; the user manual is the [README](../../README.md).

## How to use this wiki from another project

1. Read [08 Porting checklist and lessons](08-porting-lessons.en.md) first. Its opening table says, for every rule, whether it is general or RE0-specific and where it is described.
2. Every page has two sections. **General (any RE map mod)** is written without RE0 names and can be copied. **RE0 HD Remaster specific** holds addresses, offsets, data formats, game behaviour, art references and the numbers tuned for this game. Copy the first section; use the second as a worked example and re-derive its numbers for your game.
3. Content that could not be classified is labelled **unclassified**, not guessed.
4. Every number comes from the RE0 project's code and from files in `verification/` and `data/`. Citations are paths relative to the RE0 project root.
5. Evidence levels used on every page: **static** (code or data reading), **synthetic** (offline harness or emulator), **live** (seen in the running game). Most statements are static or synthetic; where a statement was seen live the page says so.

## Pages

| Page | Contents |
| --- | --- |
| [01 Features and controls](01-features-controls.en.md) | User-facing features, keys, legend and settings panel, INI, defaults, migration |
| [02 Display spec](02-display-spec.en.md) | Sizes, opacities, zoom curves, on-screen size vs resolution, colours, diamonds, drop icon, text wrap, name rules |
| [03 Placement rules](03-placement-rules.en.md) | Room names, marks, item names, collision order, frame avoidance, out-of-room handling, duplicates, whole-data audits |
| [04 Icon art spec](04-icon-art.en.md) | Art decisions, 96 px source, mip chain, edge darkening, white-rim bug, per-icon fixes, pipeline |
| [05 Data and conditions](05-data-conditions.en.md) | Placements, conditions, events, dropped items, category rules |
| [06 Runtime and rendering](06-runtime-rendering.en.md) | Hooks, Present-time drawing, gates, frame detection, textures and memory, D3D state, counters |
| [07 Verification workflow](07-verification.en.md) | Build and test gates, native dispatch mutants, emulator, live capture, install rules, coverage gaps |
| [08 Porting checklist and lessons](08-porting-lessons.en.md) | Classification table, what to reuse, what is RE0-specific, mistakes and how they were found |

## Known limitations (summary; details on each page)

- Frame rectangles that the overlay avoids were measured from one 2560x1440 screenshot ([03](03-placement-rules.en.md)).
- Dropped items in the 13 rooms that span more than one floor cannot be assigned to a floor from the data; two rooms use an inferred height split ([05](05-data-conditions.en.md)).
- Partner character and scenario differences were not traced ([05](05-data-conditions.en.md)).
- The "show only items already seen" feature is deferred; no per-item seen record exists in the game ([05](05-data-conditions.en.md)).
