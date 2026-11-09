# 06 Runtime and rendering

[한국어](06-runtime-rendering.md) | [English](06-runtime-rendering.en.md) · [Index](README.en.md)

Paths are relative to the RE0 project root. Citations name files and functions, not line numbers. Runtime code is `src/runtime/re0_map.c` (this page calls it `re0_map.c`); decisions are in `src/core/frame.c` and are shared with the emulator.

## General (any RE map mod)

### Division of labour

- One shared C module decides everything the overlay shows and returns a list of draw operations (rectangle, colour, glyph). The ASI and the emulator only paint that list. Do not duplicate eligibility, projection or placement logic anywhere else.
- The ASI does only what needs the running game: hooks, reading memory, settings, input, D3D.

### Learning where the game drew its map

- Do not guess room boxes. Hook the game's GUI classes at their virtual-table slots: the map object, the room instance, the sprite. Call the original first. A thread-local context exists only during the map draw, so sprites from other GUI are not taken for rooms.
- Accept an instance only if its owner is the map being drawn and its id matches a known room of the displayed region. Accept a sprite only if it has a texture, non-zero alpha and a valid quad. Union the sprite boxes of one room; keep small non-room sprite boxes as obstacles (cap the side so the map's own large art never counts).
- Use the sprite's final, parent-composed matrix and the game's render-argument origin and scale to get pixel coordinates; map them to the back buffer through the game's render rectangle (viewport, bound target, blit rectangle when the display aspect differs from the render aspect).
- Reach hooks through the real vtable slots and the native constructors in tests, not by calling your hook directly (page 07).
- Several map objects may draw in one frame: an empty one must not replace the one holding rooms.

### Safe installation

- Refuse unknown builds: check the executable's SHA-256, the fixed image base, the build string, and the first bytes of every function you hook. Wait (with a timeout) until a protected executable has decrypted its code.
- Replace slots with compare-and-exchange; roll back earlier patches if a later one conflicts; log the reason and disable, never crash the game.
- Never replace a remembered original with a later hook (chain recursion). One original per device vtable. Hot unload is unsupported.
- A byte patch of the game's code (if any) is minimal, context-checked first, read-only in effect, and a mismatch only loses that feature.
- Read game memory only after a page-readability check; unreadable means unknown, never "taken" or "done".

### Drawing at Present

- Draw at `Present`, where the back buffer holds the finished frame. `EndScene` may be an intermediate pass.
- Keep drawing the latest capture on every Present, because Present outpaces map draws; consuming a capture once flickers.
- Save the full device state with a state block (all), set render target, no depth, no shaders, an explicit list of render and sampler states, `XYZRHW` vertices with the half-pixel offset (-0.5), alpha blending `SRCALPHA / INVSRCALPHA`. Restore everything afterwards. If restore fails, disable the overlay and log it.
- Bind the icon texture with linear mips for icon ops and the text atlas with no mips for text; track the bound texture so state changes only when needed.

### Fade gate and stale-capture gate

- Do not draw while the game's screen fade is up (alpha above a small limit): overlays that draw through a fade look wrong.
- Stale captures: because the latest capture is redrawn every Present, a closed map's last capture would reappear if the fade returned to clear before it aged out. A time window cannot fix this when another mod shortens fades. Use a **generation latch**: every map capture gets an increasing generation; at each Present, if the fade is up or the map object is not live, mark every capture so far stale (`stale = generation`); a capture draws only when its generation is above `stale`. After the fade has been up for even one Present, the old capture can never draw again; only a map draw made afterwards can. Keep an age limit only as an extra bound.
- Cost: after a fade-in or reopen the overlay waits for the next map draw (one or two frames).
- Log "held back" the first few times.

### Frame (chrome) detection

- Do not guess whether the game's frame is shown. Find a sprite whose size is unique to a state (a help panel drawn only when shown; a list strip drawn only while the item list is open) in a live sprite dump, count the sprites of the on and off states to prove it, and treat "seen within 2 Presents" as shown.
- Take scale and offset from that sprite's matrix and the render rectangle.

### Sprite dump (live capture)

One key arms a dump of every sprite the game draws in the next whole frame (object bytes, view, texture pointer, room, instance id, and the head of each texture resource) to a JSON file written through a temporary file and replace. Use it to compare an emulator with the game and to find frame sprites.

### Textures and memory in a 32-bit game

- The process has about 2 GB of address space and shares it with the game. Budget textures explicitly: text atlas 4096x4096 BGRA (64 MiB) is the practical limit (the generator raises above height 4096); keep icons in their own smaller texture; read files only after checking the exact size; create once per device and do not retry every frame.
- A managed-pool texture can also keep a system-memory copy; count it as up to twice.
- Count and log every failure path (texture missing, wrong size, creation or lock failure); fall back to grey squares for icons and skip names rather than crash.

### Logging and counters

- Every path that drops data in a hook has a counter, and a periodic or on-demand `Diag` line prints all of them. A silent drop is a defect.
- Log each new waiting reason once; log state changes with caps (a cap per line type).
- Capture files contain no saves, inventory or personal data; only progress flags.

## RE0 HD Remaster specific

### Supported build

| Item | Value | Source |
| --- | --- | --- |
| Executable SHA-256 | `67418c3a307b49e9bde8123df4cad1fa910f3a29adc3e4c0ba64eb96524bc14b` | `re0_map.c` |
| Image base | `0x400000` (the ASI links at `0x62000000`, ASLR on, DEP on) | `re0_map.c`, `build.py` |
| Build string | `MasterRelease Jan 28 2025 16:45:59` at `0xd1e574` | `re0_map.c` |
| Code signatures awaited | `0x883090` `55 8b ec 83 e4 f8`; `0x87cc40` `55 8b ec 83 e4 f0`; `0x890ae0` `56 8b f1 83 be e4` | `re0_map.c` |
| Wait | up to 2400 x 50 ms for the decrypted code | `re0_map.c` |

### Hooks

| Class | Vtable slot | Original | Fields read |
| --- | --- | --- | --- |
| Map | `0xcdc6a8` (vtable `0xcdc650` +0x58) | `0x883090` | `self == vtable 0xcdc650`, `+0x27c == 3`, state at `+0x278`, region `state+0x44 < 6`, zoom `state+0x54`, mode `+0x58`, pan `+0x5c..+0x6c` |
| Instance | `0xd25478` (vtable `0xd25448`, class `cGUIInstAnimation`, +0x30) | `0x87cc40` | id `+4`, owner `+0x6c` must equal the map |
| Sprite | `0xd26168` (vtable `0xd26138` +0x30) | `0x890ae0` | texture `+0xe4`, alpha `+0xb0 >> 24`, mode `+0xe8 & 0x30`, flags `+0x54` (bit 22 flip), anchor `+0xa0` masked `& 15` (live value `0xff5`), size `+0xc0`, matrix `+0x10`; render args view `+0xb8` |

Source: `re0_map.c`, `verification/hook-classes.json`. `schemas/render-contract.md` is stale on two points: it gives the instance vtable as `0xd254b0` (+0x30 = `0xd254e0`, the wrong class `cGUIInstAnimVariable`) and describes an EndScene draw with a 100 ms age; the code draws at Present with 250 ms. Patch order sprite, instance, map, with rollback (`re0_map.c`). A map capture published after the original returns (`re0_map.c`); an empty map draw does not replace one with rooms unless older than 100 ms.

Game rectangle (`re0_map.c`, `annotation.c`): renderer `[0xe2d40c]` (vtable `0xce5fc0` or `0xd1b278`; device at `+0x98`), view `+0xbc/+0xc0`, target `+0xfc/+0xfe`, render size `+0xb8/+0xbc` of sRender, blit rectangle `+0xa4..+0xb0`, back buffer `+0x433e50/54`. Setter `0x866ac0`; centring `0x72376a`. Unreadable counts `rect_unreadable` and assumes target = back buffer. The aspect gate (21:9) has a mutant in the dispatch check.

Present: vtable index 17; indices 16, 17, 42, 83 must be executable (`re0_map.c`). Overlay is skipped if the last capture is older than 250 ms or its region is negative (`re0_map.c`).

### Gates

- Fade: `[[0xdcbea4] + 0x20] + 0x277` (alpha), update `0x5aa060` keeps colour at `+0x274`; draw only while alpha `<= FADE_DRAW_ALPHA (64)` (`re0_map.c`). Unreadable: not gated, logged once.
- Map live at Present: vtable `0xcdc650` and `+0x27c == 3` re-read from the map object (`re0_map.c`). `+0x27c` is 3 once loaded and 4 at `0x5b4fad` when its GUI resource is gone; whether it changes before the map stops drawing was not traced, so the fade hold, not that field, is what ends the close case.
- Latch: `re0_present_gate` (`frame.c`, comment `frame.h`), called from `overlay_allowed` (`re0_map.c`).
- Symptom: with `RE0.NoUIWait.asi` `FadeSpeed=3.0`, a closed map's last capture redrew: the old gate drew while the last capture was under 250 ms old and fade alpha was at most 64; with a 3x fade the alpha returned to 0 inside the window. At 1x the fade-out outlasted the window, so it never showed. A generation latch fixes it (the NoUIWait flash is gone). The fix is covered by mutants "fade only: stale capture drawn when a fast fade returns to clear" and "map state ignored at Present", scenario `fade_gate`, and `tests/test_review48.py` (fade-up held 1, 2, 5 and 60 Presents).
- Log line: `Overlay held back: no map draw since the fade or the map is not live` (first 8).

### Frame detection

`re0_map.c`. Help panel sprite 176 x 152 means frame shown (frame on 39 sprites, off 25 at 2560x1440); list strip 744 x 93 means the list is open (76 sprites open, 39 without); shown if seen within 2 Presents (`present_count - seen_at <= 2`); frame-to-target scale from the panel sprite's matrix (2 at 2560x1440). The screen's frame key `V` hides the frame by not drawing those sprites.

### Textures and memory

| Item | Value | Source |
| --- | --- | --- |
| Text atlas | 4096 x 4096 BGRA, 67,108,864 bytes, `D3DPOOL_MANAGED`, `A8R8G8B8`, one level | `re0_map.c`, `labels_generated.h` |
| Icon texture | 2048 x 1024, 5 levels, 11,173,888 bytes | `re0_map.c` |
| Texture data total | about 75 MB | |
| Atlas limit | height above 4096 raises at build (`"4096 is the limit for a 32-bit game"`) | `build_labels.py` |
| Solid fills | sample 2 px inside an 8 x 8 white block so bilinear filtering cannot reach its edge | `re0_map.c` |
| Debounce | 350 ms per key | `re0_map.c` |

The atlas is 4096x4096 because names for every item id pass 2048 rows.

### D3D state

`re0_map.c`: `CreateStateBlock(D3DSBT_ALL)` + `Capture`; render target set to the back buffer, depth none; `BeginScene`; vertex and pixel shaders off; FVF `XYZRHW | DIFFUSE | TEX1`; Z off; alpha test off; blend on `SRCALPHA/INVSRCALPHA`, `BLENDOP ADD`; cull none; lighting, fog, stencil, scissor, sRGB write off; colour write 15; modulate colour and alpha; texture stage 1 off; linear min/mag, mip none (icons: linear), clamp; viewport the full back buffer. Vertices offset by -0.5. `Apply` failure sets `enabled = 0` and logs `D3D state restore failed; overlay disabled`. Tested only with a fake device (page 07); the real GPU result of mips, LOD and state restore is live-only evidence.

### Logging counters

`diag` (`re0_map.c`): maps, maps_closed, maps_empty, instances, no_context, owner_miss, id_miss, id_hit, sprites, sprite_no_context, sprite_unreadable, sprite_no_texture, sprite_alt_mode, sprite_transparent, sprite_bad_quad, sprite_room, sprite_other, flags_unreadable, layout_rejected, fade_unreadable, arrange_unreadable, arrange_mismatch, actors_unreadable, actors_overflow, rect_unreadable. Also `icon_load_failures`, `icon_fallback_ops`, drop statistics (`valid`, `drawn`, `unmapped`, `rejected`, `capped`; `frame.h`), rows dump counters. Printed by `Diag F8:` and `Diag map open 2s:` (`re0_map.c`). Capped log lines: game rect changes 8, placement table changes 8, fade gate changes 16, held-back 8, name-zoom lines 64.

### F8 outputs

`capture_report` (`re0_map.c`): schema 1 `captured-native-draw`: profile hash, region, target, settings, room boxes with piece state, obstacle boxes, flag words, `room_states` digits, table mode and rows, `markers_done`. `dump_write` (`re0_map.c`): schema 2 `captured-native-sprites`: up to 1536 sprites of 0x110 bytes, 64 textures with 0x80-byte heads. `rows_dump` (`re0_map.c`): `-rows-NN.json`, `CREATE_NEW`, 32 files at most. The capture contains the game's progress flags and no save file, inventory or personal information.

### Observed live

- Drawing at Present on the back buffer works; D3D state restore caused no reported problem; one map object, five room instances per draw, all owners and ids matched.
- Room names displayed and zoomed labels sat on the right rooms (`tests/fixtures/live-samples.json`).

### Unclassified

- Behaviour under Windows and with mods other than `re0box`, FusionFix and `RE0.NoUIWait`: not tested .
