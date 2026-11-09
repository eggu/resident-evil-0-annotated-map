# 02 Display spec

[한국어](02-display-spec.md) | [English](02-display-spec.en.md) · [Index](README.en.md)

Paths are relative to the RE0 project root. Citations name files and functions, not line numbers.

## General (any RE map mod)

### Coordinate model

- The game's map GUI has a fixed virtual canvas. Store every location, room box and layout in canvas units. Map canvas to screen with a view `(scale, ox, oy)`; the screen factor is `back-buffer height / canvas height`.
- The view is inferred from the room boxes the game really drew (captured), checked against the boxes stored at build time. Accept it only if the scale ratio of x and y agree within 2% and every box edge is within 4 px; otherwise do not draw location marks (fall back to counts beside the captured boxes).
- Sizes scale with height only. Width is ignored; use the game's own render rectangle so wide displays that centre a 16:9 image stay aligned.
- Panels such as the legend use a separate factor `height / 1440` so the raster (made for 1440p) keeps its pixels 1:1 at 1440p.

### Zoom curves

- Native zoom is a progress value 0..1 mapped to a map scale from 1x to a maximum (3x here). Derive `t = clamp((view.scale / screen - 1) / (max - 1), 0, 1)` from the view, not from game memory.
- **Name zoom:** `name_zoom(t) = Z0 + (1 - Z0) * t`. Names are the set size when fully zoomed in and `Z0` of it zoomed out; they follow the map through the zoom. Room names and item names share one curve (tested).
- **Icon size** = `ICON_SIDE * user% * screen * name_zoom(t) * gain(category, t)`. `gain` is linear in `t` per category. Keep enemies unchanged; give key items and door keys an extra 10%; let door keys grow faster than others when zoomed in.
- Use one function for the mark side, and feed every consumer from it (reservation, off-screen test, legend overlap test, collision box, dropped-item icon). Two formulas drift apart.

### Opacity and colour

- Name opacity is an alpha byte `percent * 255 / 100` in the vertex colour. Icon opacity is a separate alpha. Do not mix them.
- Icons are white art tinted only by alpha; names take the category colour; the legend row, the mark name and the room-count badge of one category share one colour.
- One colour per category, fixed order. An off row is the same row in grey.
- Puzzle marks are an orange diamond with `!`; event marks (their own category, spoiler story scenes) are a purple diamond with `?`. Diamonds are drawn shapes (not a font) in the mipped icon texture: white fill so the tint colours them, dark outline and symbol, so stem and dot stay apart at small sizes. Diamond corners reach past the square mark by `side / 9` on each side; count that in collision and overlap checks.
- A dropped-item icon sits centred on the game's own coloured dot at 65% alpha so the dot's colour and blink stay visible. Do not offset it.

### Text wrap rules (mark names)

1. A trailing count (`xN`, `N%`) always takes line 2.
2. Otherwise a name of 8 or more characters, spaces included, wraps at the space nearest the middle.
3. A single word is never split (a no-space long name stays on one line).
4. At most two lines. A long name with a count keeps the name on one line and the count on line 2.
5. Enemies and events have no line 2.
6. Lines are separate raster glyphs; the whole wrapped box is collision-checked.
7. Alignment follows the side of the icon the name sits on: icon on the left, left-aligned; icon on the right, right-aligned; above or below, centred.
8. Room names: a one-line name wider than 150% of its room wraps between words, only if it has a space (page 03).

### Name rules

- Names are the game's own item names, translated by the project where the target language lacks them.
- Drop the particle in `A of B`-style item names (Korean `의`) when it reads naturally; keep it for one-syllable stems that read wrong without it. Keep that exception list in a verification file for review.
- Counts: show `xN` for stacks only; weapons show no count (their amount is rounds loaded); a count of 0 or 1 or an unset value shows nothing; ammo whose raw unit is not the catalogue unit is converted before display.
- Enemies show an icon and no name; events show no name.
- Rasterise names near the size they are shown (a 20 px raster stretched 1.65x looked blurred); outline text with 2 px dark stroke.

## RE0 HD Remaster specific

### Constants

| Constant | Value | Source |
| --- | --- | --- |
| Canvas | 1280 x 720 | `src/core/frame.h` |
| Native zoom | scale `1 + 2p`, p in 0..1, so 1x to 3x | `src/core/map_transform.c` |
| `t` | `clamp((view.scale / screen - 1) * 0.5, 0, 1)` | `frame.c` |
| `Z0` (`ZOOM_OUT_NAME`) | 0.7 | `frame.c` |
| Name raster font | 30 px (`NAME_FONT`); `NAME_SCALE = 20 / 30` | `build_labels.py`, `frame.c` |
| `NAME_SIZE_BASE`, `ICON_SIZE_BASE` | 1.1, 1.3 | `frame.c` |
| `ROOM_NAME_K` | `.88 * .8 * 1.1 = 0.7744` | `frame.c` |
| `ITEM_NAME_K` | `.8 * .8 * 1.1 = 0.704` | `frame.c` |
| `ICON_SIDE` | `18 * 1.2 = 21.6` canvas px | `frame.c` |
| Screen factor | `height / 720` (marks, names); `height / 1440` (legend, readout) | `frame.c` |
| Name/room alpha | `opacity * 255 / 100`, in the top byte | `frame.c` |
| Icon alpha | `clamp(icon_opacity, 10, 100) * 255 / 100` | `frame.c` |
| Dropped-icon alpha | `0xa6` (65%) times the icon alpha | `frame.c` |
| Fixed room-name scale in the generator | `.88 * .8 * 1.1 * .7 * 20 / 30 = 0.3614` canvas px per raster px at size 100, zoomed out | `tools/extract/room_layout.py` |
| View acceptance | 2% scale agreement, 4 px per edge | `frame.c` |

Defaults: name size 100, name opacity 60, icon size 100, icon opacity 80, item names off, names on, Korean, scope Visited (`frame.c`).

### Icon gain by category

`icon_gain(category, t)` and `mark_side` at `frame.c`:

- Enemy: gain 1.0, no extra.
- Door key (lock category): `1.3 * (0.96 + (1.5 - 0.96) * t)`, extra 1.1.
- Key item: `1.3 * (1 + 0.3 * t)`, extra 1.1.
- Files, puzzles, common items: `1.3 * (1 + 0.3 * t)`.

So relative to the 100% icon setting: items and key items go 100% -> 130%, door keys 96% -> 150%, enemies stay at 1.0 with no 1.3 base. Zoom gain is items 100 -> 130 and door keys 96 -> 150; enemies are not enlarged. Test: `tests/frame_contract.py` `icon_sizes`.

Icon side in screen px at the 100% setting (computed from the formulas above):

| Category | 720p out / in | 1080p out / in | 1440p out / in |
| --- | --- | --- | --- |
| Item, file, puzzle (square part) | 19.66 / 36.50 | 29.48 / 54.76 | 39.31 / 73.01 |
| Key item | 21.62 / 40.15 | 32.43 / 60.23 | 43.24 / 80.31 |
| Door key | 20.76 / 46.33 | 31.14 / 69.50 | 41.51 / 92.66 |
| Enemy | 15.12 / 21.60 | 22.68 / 32.40 | 30.24 / 43.20 |

Name scale per raster px (`screen * K * NAME_SCALE * name_zoom * size/100`) at size 100:

| Name | 720p out / in | 1080p out / in | 1440p out / in |
| --- | --- | --- | --- |
| Room (`ROOM_NAME_K`) | 0.3614 / 0.5163 | 0.5421 / 0.7744 | 0.7228 / 1.0325 |
| Item (`ITEM_NAME_K`) | 0.3285 / 0.4693 | 0.4928 / 0.7040 | 0.6571 / 0.9387 |

### Colours (ARGB)

Sampled from the RE1 HD legend rasters (`frame.c`).

| Use | Value |
| --- | --- |
| Locks | `0xffffcd46` |
| Key items | `0xff5adcff` |
| Files and maps | `0xffff8cd2` |
| Puzzles | `0xffff9628` |
| Common items | `0xffb8bcc4` (cool grey, user 2026-11-08; was `0xffff783c`) |
| Enemies | `0xffeb3c3c` |
| Events (diamond and legend row) | `0xffb070ff` |

The table lists the shipped defaults. The seven category colours are replaced at run time by the INI's `[Colors]` (page 01); the atlas stays white and the colour is the D3D9 vertex tint, so no texture changes with them. The off-row grey is fixed.
| Off row | `0xff6a6a6a` (was `0xff8c8c8c`) |
| Legend row [1], cream | `0xfff0e2be` |
| Small text, note text, value gold | `0xffc8c8c8`, `0xffa5a5a5`, `0xffffe080` |
| Room name text | `0xf8f0c8` with alpha; outline `0x080808` | 
| Panel backgrounds | `0xd0080808` (legend, readout), `0xc0080808` (room panel) |
| Leader line | casing `0x080808`, core `0xf8f0c8` |
| Selected-room frame | `0xffffe040` |

Diamonds: polygon `(48,4) (92,48) (48,92) (4,48)` ink, inner polygon `(48,12) (84,48) (48,84) (12,48)` white, on a 96 px canvas (`build_labels.py`); `?` drawn 10% smaller about the centre.

### Dropped-item icon

Items the player dropped are drawn on the game's own dot (12x12 sprite, scale 4 at 2560x1440 when 3x zoomed), centred, 65% alpha. The dot colour varies by item class (Ink Ribbon orange `ff5800`, herb green `0fa932`, ammo blue `287aff`, handgun red `ff0038`, key item yellow `ffff28`); the class-to-colour mapping is inferred from these five rows. Projection matched the dot to within 0.4 px at 2560x1440.

### Name text (Korean)

- `의` rule: remove the first `의 ` preceded by a non-space (`build_labels.py`). 33 names changed; 7 kept: `선의 서`, `악의 서`, `백의 조각상`, `흑의 조각상`, `불의 열쇠`, `물의 열쇠`, `시의 한 구절` (`build_labels.py`, `verification/ko-name-changes.md`). Enemy marker labels keep their full names (`build_labels.py`); room names are not touched by this rule.
- Counts: weapons no count; `amount <= 1` or `>= 65535` no count; Machinegun Ammo shows `(amount + 2) / 3 %`; others `xN` (`build_labels.py`).
- Mixed herbs (item ids 46-51): one plain name `조제한 허브` / `Herbal Mix`; only the icon tells the six mixes apart (project decision).
- Wrap code: `build_labels.py` (split), `221` (no line 2 for enemies and events), `frame.c` (box and alignment; the second line's top overlaps the first by 10 raster px, the tile margin).
- Room-name raster: font 30 px, 2 px outline, tile padding 6 px (`build_labels.py`).
- Whole-data wrap audit: Korean 197 single, 42 wrapped, 140 with count; English 29 single, 210 wrapped, 140 with count. Single-word 8+ character labels stay single: Briefcase, Hookshot, Motherboard.

### Unclassified

- Whether other games should keep the 0.7 zoomed-out name factor and the 1.3/1.5 gains: they are tuned for this game's icon art and zoom range.
