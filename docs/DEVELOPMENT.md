# Development

## Environment

Python 3.10+ and Pillow are required for resource previews. Clang is required to build the shared C transform/geometry used by the preview. Node.js is optional for the offline review page's DOM/canvas smoke test. The read-only PE validator is reused from `../../common/re-mod-presets/tools/pe.py`; keep this workspace layout when running the inventory tool.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python tools/build_core.py
.venv/bin/python -m unittest discover -s tests -v
```

`--game` is always explicit. Tools do not discover personal paths, launch games, change configuration, or install plugins. Generated game-resource images, downloaded source pages and analysis-only binaries stay in ignored `local/`. JSON metadata under data/ and verification/ contains identifiers, properties, hashes and provenance, not full game payloads.

## Read-only inspection and resource preview

Set `RE0_GAME` to your own game folder containing `re0hd.exe`.

```sh
.venv/bin/python tools/inspect/inspect_game.py --game "$RE0_GAME" --output verification/resource-inventory.json
.venv/bin/python tools/extract/map_data.py --game "$RE0_GAME" --output data/native-map.json
.venv/bin/python emulator/render.py --game "$RE0_GAME" --region tr --floor 1f --labels --output local/previews/tr-1f.png
.venv/bin/python emulator/build_review.py --game "$RE0_GAME" --output local/review/index.html
```

Open `local/review/index.html` manually to inspect all floor previews. Floor selection, diagnostic zoom/pan, internal-ID labels, sprite click inspection and PNG export work offline. External-map links open only when clicked. Zoom/pan in this page is for resource inspection and is not a reproduction of the native game's input or limits.

`emulator/render.py` reads native GUI animation IDs, hierarchy and static properties and composes atlas sprites. It does not evaluate animated properties, gameplay visibility, native clipping/viewport, players, dropped items or enemies. Shared textures are resolved by exact resource name from map.arc/map_jpn.arc without language aliases. Unsupported transforms are listed as omissions. Separate door groups remain outside this preview scope. Its neutral background and centred canvas are diagnostic choices. Do not treat its output as a verified in-game screenshot.

The supported resource readers are ARC v7, mloc v1, TEX header 0x2000209d and a static subset of GUI 0x22013. Array/unknown GUI properties remain explicit unresolved records. The preview decodes only TEX formats 0x14/0x18 as BC1/BC3; 0x2b is deliberately refused until this game's channel/shader interpretation is established.

## External catalogue checks

The source HTML must be obtained separately and kept under local/external/{tr,sh,dm,ch,bt,pl}.html. Record the real access date; never substitute a file migration date.

```sh
.venv/bin/python tools/crosscheck/floor_catalogue.py --game "$RE0_GAME" --sources local/external --checked-on YYYY-MM-DD --output verification/floor-crosscheck.json
.venv/bin/python tools/crosscheck/external_locations.py --sources local/external --checked-on YYYY-MM-DD --output data/external-locations.json
```

Floor headings are compared automatically. The external catalogue retains its own identities and image-map areas; curated room correspondences are separate in data/room-matches.json. The train correspondences cover names/floor geometry only, with Korean names marked as proposed project translations. No door/item condition is verified. Room, door and item claims require their own evidence. See verification/discovery.md for the current boundary and the source references.

## Native evidence

`tools/inspect/verify_native.py` accepts the supported original EXE and an analysis-only decoded .text image. It checks both hashes, verifies that all other bytes remain unchanged and checks bounded signatures and two resource strings. It does not produce a runnable EXE, decode a game, patch files or install hooks.

```sh
.venv/bin/python tools/inspect/verify_native.py --exe "$RE0_GAME/re0hd.exe" --analysis-image <analysis-image> --output verification/native-evidence.json
```

The analysis image is intentionally not distributed. Missing native evidence means runtime contracts remain pending; the resource preview does not unlock the W0/G0 or W1/G1 gate by itself.

## Bounded native zoom math

`src/core/map_transform.c` is a shared C implementation of the native GUI setter calculations at 0x5b5320. The host renderer calls this exact library when `--native-progress` is supplied; the candidate ASI links the same source. Clang builds the host library without fused floating-point contraction.

```sh
.venv/bin/python tools/build_core.py
.venv/bin/python emulator/render.py --game "$RE0_GAME" --region tr --floor 1f --native-progress 1 --focus 240 363 --labels --output local/previews/tr-1f-native-zoom.png
```

The native helper computes scale `1 + 2*t` and, unless that float32 scale rounds to one, translations `(focus_x-640)*-3*t` and `(focus_y-360)*-3*t`. `--native-progress` is a synthetic progress input in 0..1, not a captured game input. It verifies one native transform layer, not parent matrices, native clipping or game-screen equivalence. The review HTML keeps its own diagnostic pan/zoom.

Optional independent check against the actual native instruction sequence (analysis image required):

```sh
.venv/bin/python -m pip install -r requirements-research.txt
.venv/bin/python tools/inspect/check_zoom.py --exe "$RE0_GAME/re0hd.exe" --analysis-image <analysis-image> --core local/libre0map.dylib --output verification/native-zoom.json
```

Use `local/libre0map.so` on Linux. The checker verifies image hashes and then executes only the bounded original function in Unicorn, with external setter calls intercepted and all other game systems absent. It compares bit patterns from the native SSE calculations against the shared C function, including tiny progress values and absent-instance paths. It does not launch the game or execute an installed plugin.

## Shared native sprite geometry and UVs

Every preview sprite now uses the same C corner/UV code intended for the ASI, through `emulator/core.py`. The anchor rectangle and affine quad calculations reproduce native 0x892680/0x889300, and normal-winding UVs reproduce the vertex emission prefix at 0x8918d0. Unit expansion and supplied matrices are covered; native construction of parent matrices, shader colour, exact raster filtering and viewport/clip are not established.

```sh
.venv/bin/python tools/inspect/check_geometry.py --exe "$RE0_GAME/re0hd.exe" --analysis-image <analysis-image> --core local/libre0map.dylib --output verification/native-geometry.json
.venv/bin/python tools/crosscheck/room_matches.py --native data/native-map.json --external data/external-locations.json --matches data/room-matches.json --output verification/room-crosscheck.json
.venv/bin/python tools/extract/scene_scripts.py --game "$RE0_GAME" --output data/scene-script-index.json
```

Room mappings are manually reviewed correspondences with source image hashes and GUI hashes. The validator checks their identity, region/floor, source hashes and coverage; it does not claim to repeat the visual review. A GUI hash change requires re-review.

The scene script index records rEventScript headers/groups only. Loader evidence is native 0x57d100 with big-endian u32 reader 0x684530: count, 12 skipped bytes, four words per group, up to 32 retained slots. Tags and extra words are unclassified. A zero payload offset stays explicitly unresolved. Missing scene files are listed as absent slots, not presumed missing content. `rCutScrParamPackage` is a cut/camera parameter resource and must not be relabelled as an item-placement table.

## Candidate ASI adapter and shared placement

The current room-overlay candidate links `map_transform.c` and `annotation.c`; the host binding calls those same functions. It does not invent item/door/enemy state rules.

`build.py --test` builds the x86 ASI with MinGW, repeats compilation to check byte reproducibility, runs portable tests and separately compiles a synthetic adapter probe for Unicorn. The probe DLL is never packaged. Normal builds need no game files or analysis image. The atlas/header and their data-input hashes must match `verification/label-build.json`.

```sh
.venv/bin/python build.py --test
.venv/bin/python tools/build_labels.py
```

The label command rasterizes with the bundled Pretendard Medium (`fonts/`, SIL Open Font License 1.1); `--font` selects another Korean-capable font. Name/ID metadata comes from `data/native-map.json` and the reviewed correspondences. The exporter now preserves numeric GUI instance IDs and floor-group IDs. Rebuild labels after changing input data.

Native draw wrappers preserve the original thiscall chain. A map-draw TLS context limits instance/sprite capture to this map. The instance owner and region must match, and the sprite must have a texture, nonzero alpha and supported normal sprite geometry. Closed-map/unsupported states publish an empty capture. EndScene consumes each snapshot once; captures older than 100 ms are refused. Read-only state is not persisted between saves. Only annotation INI/log/capture files may be written by the installed candidate.

The installer thread verifies the exact installed EXE file SHA256, fixed game image base, build string, three native code prefixes and the original vtable slots before replacing aligned pointers. It waits for Steam's decrypted code. Existing conflicting GUI slots cause refusal/rollback; the D3D9 EndScene original is retained per vtable and never replaced with a later hook. This is static/synthetic safety evidence, not a claim of runtime compatibility. Hot unload is unsupported.

Bounded original-x86 instance→animation→sprite virtual dispatch and viewport shader constants are checked independently:

```sh
.venv/bin/python tools/inspect/check_draw_route.py --exe "$RE0_GAME/re0hd.exe" --analysis-image <analysis-image> --output verification/native-draw-route.json
.venv/bin/python tools/build_annotation_review.py --game "$RE0_GAME" --output local/annotation-review
```

The second command creates both languages for all 23 static floor scenes. These are synthetic resource previews, not captured game states; their room eligibility, native icon obstacles and animation are not gameplay-verified.

F8 in the candidate exports only native-draw boxes/obstacles, target size, profile and label settings. Replay it with the same candidate catalogue:

```sh
.venv/bin/python emulator/annotations.py --capture /path/to/RE0.AnnotatedMap-capture.json --output local/replay.png
```

An optional `--background /path/to/screenshot.png` uses an image of exactly the recorded target size. Avoid an already-annotated background when checking output. Placement is shared C; Pillow filtering and GPU output remain distinct. Runtime-specific instance scissor, final render-target composition, animation timing and actual key delivery require a live game check.

## Evidence levels

`tools/inspect/check_native_dispatch.py` is the packaging gate: native constructors and dispatch through the real hook slots, with mutants of past live failures. Resource previews and `tools/build_annotation_review.py` test label layout only. D3D and GPU behaviour needs a live run.


## Faster checks while editing

`RE0_QUICK=1 python -m unittest discover -s tests` skips the frame mutants, about 2 s against about 23 s. Most of that time is macOS checking each newly built library on first load, so it does not parallelize. `build.py --test` does not set it.

## Native gate while editing

`tools/inspect/check_native_dispatch.py --quick` runs the gates without mutants in about 4 s and records nothing. Without the flag it runs every mutant in parallel, about 24 s on 14 cores, and writes the report. `build.py --test` always runs the full gate.
