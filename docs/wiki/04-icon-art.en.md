# 04 Icon art spec

[한국어](04-icon-art.md) | [English](04-icon-art.en.md) · [Index](README.en.md)

Paths are relative to the RE0 project root. Citations name files and functions, not line numbers.

## General (any RE map mod)

### Source and display size

- Draw each icon at a large source size (96 px) and show it small. Never upscale to get a source: a small icon stretched later looks soft. The displayed side at default settings should stay at or below the source size; larger icon-size settings will magnify.
- Keep every icon the same canvas size, soft alpha (not 1-bit), square. Check this by test: size, mode, and that the alpha histogram holds 0, 255 and in-between values.
- Record every icon in a manifest with name, file and SHA-256; a test compares the files to the manifest so a silent art swap is caught.

### Look decisions

- Match the game's own look (its inventory and map art): worn metal and real materials, not cartoon colours or toy shading.
- Brighter and more saturated than a first pass drawn from dark game art; the map floor is dark, so dark objects (weapons, black birds) need a lift to separate from it. Herbs of different colours must be clearly different colours.
- Fill the canvas. An elongated item (a bar, a long-necked bottle) is drawn larger along its length than its true proportion so it fills the cell, but its silhouette must stay recognisable: do not turn a bar into a bracket or a bottle into a jar.
- Disc-shaped items are drawn face-on (label side), not in a three-quarter view.
- Where several game items share one name and differ only by recipe or colour, tell them apart with the icon, not with extra text in the name.
- Enemies get an icon and no map name. Enemy icons are heads only, and only for human and animal types, each kind distinguishable from the others, following the concept art or in-game look (a general rule carried over from RE1 HD).
- Derive the asset size from the largest size it is shown at, never from an unexamined constant (see the 24 px mistake below).
- Puzzle and event marks are drawn shapes, not art (page 02).
- Keep one lock-icon rule: a lock shows the key that opens it when art for that key exists, otherwise a padlock.

### Pipeline (build time)

1. Load the manifest icons (RGBA, 96 px).
2. Darken the edge: a band about 3 px inside the alpha edge, fading inward, alpha and interior unchanged. Use a stronger value for the items that read worst against the map (herbs and keys).
3. Paste each icon into a grid of cells in one texture sheet; paste the two diamonds into the last cells.
4. Build the mip chain on **premultiplied** data, channel by channel, with a box filter. Store the result as straight (non-premultiplied) BGRA, because the blend state is `SRCALPHA / INVSRCALPHA`. Texels with alpha below 8 take the colour of the nearest coarser level so linear filtering pulls no black into soft edges.
5. Refuse to build if any level brightens the alpha-weighted colour by more than a small limit relative to level 0.
6. Put icons in their own texture with a mip chain; keep text in a separate atlas without mips. Mips on a shared atlas would bleed across the gutters into text and cost memory.
7. Bind the icon texture with linear mip filtering for icon draws; bind the text atlas with no mip filter for text. Restore the game's full device state afterwards.
8. If the icon file is missing, the wrong size, or a level fails to create or lock, release the texture, count the failure, log once per device, and draw plain grey squares so a mark is still seen.

### The white-rim bug (lesson)

- Symptom (live): icon outlines looked white and haloed.
- Cause: the library's RGBA `resize` un-premultiplies its result; feeding it already-premultiplied data and then un-premultiplying again brightened every soft edge. Faint level-0 texels also took colour from the brightened coarse levels.
- Fix: reduce channel by channel; refuse a brightening chain at build; add a test over every icon at every level that compares the edge's alpha-weighted luminance with the source's.
- Not the cause (checked): mipmapping itself, the art, blend state, gamma or sRGB state.

### Per-icon fix policy

- Judge from the live shot first; replace art only when the problem is in the art, and verify old and new SHA-256 against the manifest before and after the copy.
- When an icon's opaque extent fills the whole canvas and looks larger than its neighbours, resample the old file down into the centre of the canvas (no upscaling) rather than redrawing.
- Keep a whole-set test for any fix that applies to a class of icons.

## RE0 HD Remaster specific

### Constants and layout

| Item | Value | Source |
| --- | --- | --- |
| Icon source size | 96 x 96 RGBA | `tools/build_labels.py`, `assets/icons/manifest.json` |
| Icon count | 118 named PNGs in `assets/icons/` (manifest `names`) | `tests/test_icons.py` |
| Atlas glyph cells | 120 = 118 icons + `!` + `?` | `tests/test_icons.py`, `labels_generated.h` |
| Icon texture | 2048 x 1024, 5 mip levels, 11,173,888 bytes (`assets/icons.bgra`) | `labels_generated.h` |
| Cell layout | 20 columns, pitch 102 px, origin (3, 3); 120 cells fill 6 of 10 rows | `build_labels.py` |
| Text atlas | 4096 x 4096 BGRA, 67,108,864 bytes (`assets/labels.bgra`) | `labels_generated.h` |
| Edge darkening | 0.45 (band 3 px, MinFilter 7, Gaussian 0.7); 0.8 for names containing `Herb` or `Key`, plus Fire, Water, Conductor's (MinFilter 9) | `build_labels.py` |
| Mip brightening limit | 6 (alpha-weighted, 8-bit units) | `build_labels.py` |
| Mip reduction | `reduce_premult`: BOX per channel on premultiplied data | `build_labels.py` |
| Fully transparent texels | take the nearest coarse colour; alpha below 8 is not un-premultiplied | `build_labels.py` |
| Fallback | plain grey square `0xffa0a0a0`, counters `icon_load_failures`, `icon_fallback_ops` | `src/runtime/re0_map.c` |
| Draw state | icon ops: `MIPFILTER LINEAR`; text: `NONE` | `re0_map.c` |

Because the largest displayed side at the default 100% icon setting is 92.66 px (door key, zoomed in, 1440p; page 02), the 96 px source is not magnified at default settings up to 1440p. At 200% icon size it is.

118 icons, texture 2048x1024 = 11.2 MB. Texture memory budget: atlas 64 MiB + icons 10.66 MiB. A managed-pool texture can also keep a system-memory copy, so the real cost may be higher; this was not measured.

### Style decisions

- Look: keep the HD Remaster's realistic worn-metal and material style, bright and saturated. Herbs: green, blue and red clearly distinct. Dark weapons and the Crow must separate from the map floor. Avoid cartoon colours and toy shading.
- Icons are shown as a large 96 px source scaled down; the current display sizes are in page 02.
- Elongated items: enlarge the characteristic parts to fill the cell, keep the silhouette (Panel Opener stays a bar, not a 9-shaped bracket; a long-necked bottle does not become a wide jar).
- Handgun Ammo: drawn as the real red PARABELLUM box with its packaging colour and exposed bullets. Disc-type icons are drawn face-on with the label side; only MO Disk is disc-shaped, Microfilm A/B are film slides.
- Black Wing: brightened with gamma 0.7 and x1.15 at install.
- MO Disk padding: the source's occupied extent (alpha > 127) was 92 x 92 of 96; it is resampled to 68 px (LANCZOS, premultiplied, no upscaling) and centred, giving 64 x 64 (69.6%).
- Herbal Mix: ids 46-51 carry six combinations (`HERB_MIX` in `build_labels.py`: G+G, G+G+G, G+R, G+B, G+G+B, G+R+B) with six icons selected by `item_ids` in the manifest and one plain name. Only dropped rows use these ids; no placed row does.
- Weapons (including Molotov) are drawn as key items, not common items (page 05).
- Lock icons: the key's icon when the manifest has it (`LOCK_ICON` aliases in `build_labels.py`: Fire Key -> Fire, Water Key -> Water, Conductor's Key, Breeding Room Key, Green Leech Charm, Shaft Key (L/R) -> Shaft Key), else `Padlock`.
- Files and maps use the generic `Document` and `Map` icons.
- Asset size lesson: icons are drawn on screen at `18 * height/720` (27 px at 1080p, 54 px at 2160p), so a 24 px source is upscaled and loses detail. Derive asset size from the largest on-screen size, never from an unexamined constant.

### Verification

`tests/test_icons.py` (8 tests): 96 px soft alpha with manifest hashes; 120 atlas cells of 96 px inside the texture; mip chain (each level's alpha is the 2x2 average, no black fringe texels, level 0 equals the manifest icon); edge luminance per level over the whole set; only puzzle rows have no icon; frames draw icons, diamonds and no enemy name; a puzzle row alone never paints an icon; the mark size formula. `check_native_dispatch.py` has mutants for icons without mips, wrong mip filter for text, atlas-sampled icons, unrestored bind, level offset, level-0 reuse and ignored lock failure (`verification/native-dispatch.json`).
