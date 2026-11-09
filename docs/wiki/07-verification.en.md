# 07 Verification workflow

[한국어](07-verification.md) | [English](07-verification.en.md) · [Index](README.en.md)

Paths are relative to the RE0 project root. Citations name files and functions, not line numbers.

## General (any RE map mod)

### Evidence levels

Report these separately and never let one stand in for another.

| Level | Meaning | Cannot show |
| --- | --- | --- |
| Static | Code or data reading, disassembly | That it runs |
| Synthetic | Offline harness, emulator, hand-built state labelled synthetic | That the game does the same |
| Native-built | The game's own constructors and functions run in an x86 emulator, hooks reached through real vtable slots | D3D, GPU, real resources, timing |
| Captured-state replay | A real capture (F8) replayed through the shared code | That the screen looks right |
| Image comparison | Emulator image vs a game screenshot | Behaviour |
| Live | Seen in the running game | Other resolutions, builds, mods |

An emulator that succeeds proves nothing about the game. A resource preview or placement replay that starts from assumed boxes and bypasses the hooks must never be cited as evidence that the runtime captures or displays anything.

### Rules

1. **One shared decision module** for the ASI and the emulator. Never validate one implementation against an identical copy of itself.
2. **Offline evidence follows the game's path.** Object field values come from the game's constructors and setters or from live captures, never from a hand-written fixture alone. Reach hooks through native dispatch and the real slots.
3. **Shared code must not refuse what native code draws.** Differential checks sample the field's full packed range, not only the values the author expects (an anchor field masked to 4 bits was refused because tests only used masked values).
4. **Every live failure becomes a mutant** in the native dispatch check, and its observed values enter the live-samples fixture. Do not package with a surviving mutant. A contract test must pass on the real code before the mutants are run, otherwise a contract that always fails would make every mutant look caught.
5. **Count every drop.** A hook path that drops data without a counter is a defect.
6. **Whole data, not examples.** A report is an example; check every row with the same condition.
7. **Reproducible build.** Compile twice and compare bytes; verify the package contents against the members; refuse to package if the generated header, atlas and icon texture do not match the generation record's hashes and input hashes.
8. **State what each check did not exercise** in every release.

### Live capture workflow

1. Ask the user to open the map in the state to inspect (floor, zoom, frame on/off, list open/closed) and press the capture key; ask for a screenshot of the same moment at full size, not a crop.
2. The capture key writes: a JSON capture (room boxes, obstacles, settings, progress flags, done markers), a sprite dump of the next whole frame (schema-versioned), and a numbered placement-rows dump. Sprite dumps and captures overwrite the previous file; rows dumps never overwrite (first free number up to a cap).
3. **Copy every file to a dated folder before the next capture** (`local/live/...`): the next press overwrites them.
4. Compare the screenshot with the shared code's ops for the same view; add observed values to the live-samples fixture; turn each defect into a mutant and a test.
5. A capture proves coordinates and flags only, not GPU output. It contains no saves, inventory or personal data.

### Install rules

- Install only candidates that passed the native dispatch gate; refuse when the build report says the gate did not run.
- Refuse when the game is running (wait for it to exit, never stop it); refuse an unsupported executable hash; refuse a ZIP that differs from the build report.
- Replace each file through a temporary file and an atomic rename, verify its hash, and leave the user's INI alone unless it does not exist.
- Check that the other files in the game folder (executable, loader, other mods and their INIs) have unchanged hashes before and after.
- Write an installation record (time, build, files and hashes).
- Never launch or stop the game, and never publish.

## RE0 HD Remaster specific

### Build and gate

`build.py --test` (`build.py`):

1. `tools/build_core.py`: compiles `map_transform.c`, `annotation.c`, `frame.c` into `local/libre0map.dylib` (clang, `-ffp-contract=off`) for the emulator; a wasm build of `frame.c`, `annotation.c` and `src/wasm/glue.c` serves the review page (`tools/build_core.py`).
2. `python -m unittest discover -s tests -v`.
3. If the analysis image (not distributed) exists: `tools/inspect/check_hook_classes.py` and `tools/inspect/check_native_dispatch.py`, then `gate_passed = True`. Without the image the gate does not run.
4. Check the atlas and icon texture sizes and SHA-256 against `verification/label-build.json` and the generated header and input hashes (`build.py`).
5. Cross-compile the ASI with `i686-w64-mingw32-gcc` (`-std=c11 -O2 -Wall -Wextra -Werror -shared`, image base `0x62000000`, dynamicbase, nxcompat), twice, and compare bytes; verify it is an x86 DLL.
6. Compile `tests/runtime_probe.c` and run `tools/inspect/check_adapter.py` (8 synthetic adapter cases, `verification/adapter-synthetic.json`).
7. Write the release ZIP `dist/RE0-Annotated-Map-<version>.zip` (members: loader `dinput8.dll`, ASI, `.bgra`, `.icons.bgra`, `.ini`, loader license, README, `LICENSE.txt`, `NOTICE.md`) and `dist/build-report.json`.

Numbers: 189 tests, 73 native dispatch mutants caught, 8 adapter cases (the 73 are also listed in `verification/native-dispatch.json`). `build.py --test` always runs the full gate; `RE0_QUICK=1` skips the frame mutants (about 2 s vs 23 s); `check_native_dispatch.py --quick` runs the gates without mutants (about 4 s) and records nothing (`docs/DEVELOPMENT.md`).

### Native dispatch gate

`tools/inspect/check_native_dispatch.py` (about 60 KB). Evidence: `original-x86-constructors-and-dispatch-through-real-hook-slots` (`verification/native-dispatch.json`): scope map draw -> root walk -> instance -> animation -> sprite with native vtables and constructors. Stubbed: sprite emission and per-node preparation. Not covered: D3D/GPU, Present target, native matrix construction, real resource loading. Gates in the report: `aspect_gate`, `lock_gate`, `overlay_gate`, `ini_gate`, `scope_gate`, `arrange_gate`, `enemy_gate`, `emulator_gate`, `flag_gate`, `fade_gate`.

Mutants (73) are named after live failures, for example: `21:9 overlay ignores the render rect`, `icons drawn without mips`, `freed slot draws its stale bytes`, `dropped room read from row +0`, `killed enemy stays shown`, `mark tied to one piece of its room (Ice Pick)`, `Conductor's Key on the Cabin 201 door`, `All patch opens the floor tabs too`, `fade only: stale capture drawn when a fast fade returns to clear`, `map state ignored at Present`. The full list is the `mutants_caught` key of `verification/native-dispatch.json`.

Frame mutants (the overlay's rules): a `MUTANTS` table in `tests/test_frame.py` (57 entries by a pattern count of the file, not run for this wiki) whose contract is `tests/frame_contract.py`. Each entry reproduces a defect found on screen, or its neighbour.

### Other checks

| Check | What it proves | Result file |
| --- | --- | --- |
| `tools/inspect/check_zoom.py` | Shared zoom math equals native `0x5b5320` over 56 cases (bit patterns) | `verification/native-zoom.json` |
| `tools/inspect/check_geometry.py` | Quad (162) and UV (15) code equals native `0x892680/0x889300/0x8918d0`, including anchor `0xff5` | `verification/native-geometry.json` |
| `tools/inspect/check_draw_route.py` | Instance -> animation -> sprite dispatch and viewport shader constants (24 cases, under 0.001 px) | `verification/native-draw-route.json` |
| `tools/inspect/check_hook_classes.py` | Room instances are class `cGUIInstAnimation` (CRC of class names), vtable `0xd25448`, slot `0xd25478` | `verification/hook-classes.json` |
| `tools/inspect/verify_native.py` | Executable and analysis-image hashes, bounded signatures | `verification/native-evidence.json` |
| `tools/crosscheck/state_flags.py` | Done state of each row by Unicorn runs of native functions: `0x59b8d0` over 0..0xffff, `0x40fd70`, `0x410610`, `0x410bb0`, `0x4101f0`+`0x40fb10`, `0x4de730`, `0x412060`, 0 mismatches | `verification/state-flags.md` |
| `tools/extract/room_state.py` | Visited rule is an AND of the flags it asks for, on every combination | build step |
| `tests/test_placements.py` (32 tests), `test_conditions.py` (13), `test_enemy_state.py` (13), `test_drops.py` (9), `test_events.py` (6), `test_icons.py` (8), `test_room_layout.py` (10), `test_review1.py` (20) ... | Parsers refuse wrong layouts; data keeps the properties that made it trustworthy; per-defect checks | `tests/` |
| `tests/test_live_samples.py` | Values seen in the real game pass the shared code that once refused them | `tests/fixtures/live-samples.json` |
| `tests/wasm_parity.js`, `tests/review_page_harness.js`, `tests/test_review.py` | The wasm build equals the native build; the review page's DOM/canvas contract (not a real browser or GPU) | |

### Emulator and review page

- `emulator/core.py` binds `libre0map` built from the same C files as the ASI. `emulator/annotations.py` replays an F8 capture through them to a PNG. `emulator/render.py` and `emulator/screen.py` compose static GUI resources (23 floors, 292 room sprites) and are diagnostic only; the emulator's scope is limited to checking display rules and placement, not reproducing the game's rendering. `tools/build_placement_review.py` builds a review page whose canvas runs the wasm `frame.c`.
- Not exercised by the emulator: animated GUI properties, native clipping, the TEX codec `0x2b`, gameplay visibility, players, dropped items without a synthetic checkbox, real filtering or GPU output. Dropped-item emulation is labelled SYNTHETIC.
- Emulator colours: fill rule agrees with the game within 5 per channel on a single sample; background is lighter than the game's and side blur, frame art and vignette are not reproduced.

### Install

Installing a development build into a game folder used a local helper script that is not part of the public repository. Players install the release ZIP as described in the [README](../../README.md).

### What the checks did not cover

- The game itself: D3D pixels, real GPU filtering and mip LOD, state restoration under the real driver, real fade timing under `RE0.NoUIWait`, Windows, other mods.
- Frame rectangles at any resolution other than the one measured; transition animation.
- Partner and scenario differences in dropped items; floors of dropped items in 11 of the 13 multi-floor rooms.
- Event content: no cutscene was viewed.
- `~`, Ctrl keys and INI read/write on Windows were tested through the shared C code only.

### Documentation and code mismatches

- `docs/DEVELOPMENT.md` and `schemas/render-contract.md` describe an EndScene draw that consumes each snapshot once with a 100 ms age limit; the code draws at Present, redraws the latest capture and uses a 250 ms bound plus the generation latch.
