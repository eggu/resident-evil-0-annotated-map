# RE0 discovery — 2026-11-03

## Verified static evidence

- Installed EXE SHA-256: `67418c3a307b49e9bde8123df4cad1fa910f3a29adc3e4c0ba64eb96524bc14b`.
- PE32 x86, image base 0x400000, build string `MasterRelease Jan 28 2025 16:45:59`.
- Import table includes d3d9.dll, d3dx9_43.dll, DINPUT8.dll and XINPUT1_3.dll. This supports a D3D9 integration investigation; no live device/hook claim is made.
- Encrypted .text and .bind present. An analysis-only image was decoded locally without changing the installed EXE, headers or non-.text bytes. See native-evidence.json for the exact analysis hash and bounded signatures. Decode research followed the upstream [Steamless Variant31 x86 implementation](https://github.com/atom0s/Steamless/tree/master/Steamless.Unpacker.Variant31.x86); no third-party source or decoding keys are copied into tracked code.
- `0x5bd6f3` passes `arc\\map\\maploc` and the archive type to the resource manager; `0x5bd6fd` calls its vtable slot +0x30 and stores the result at owner +0x88.
- GUI loader at `0x885e30` relocates tables. Header +0xa4 is the animation table; +0xac object table; +0xb4 static property table; +0xbc instance table; +0x104 string pool; +0x10c boolean pool; +0x110 scalar pool; +0x114 vector pool. Properties are 16-byte rows. Object property count is a byte at object +4, not the entire packed word (`0x88645d`).
- Animation lookup at `0x885aa0` compares the ID in 24-byte rows, rather than treating IDs as row indices. Source resource trees validated this for all six regional GUI files.
- `0x5b4a3c` supplies format `i_%2s%02x%1x%1d` for map-instance lookup. Exported encoded identities preserve the fields; their complete gameplay meaning is not assumed.
- `maploc.arc`: 175 mloc records. Header `mloc`, version u32=1, count byte at +8, count bytes at +9. Values include 0 and 255. These bytes are not labelled as floor IDs or counted as rooms.
- `map_eng.arc`: six regional GUI resources. Their authored canvas is 1280×720. Native floor groups yield 23 floor scenes, 138 map-piece instances and 115 door drawing instances. Alternate section pieces and drawing placeholders must not be counted as distinct physical rooms/connections.
- TEX dimensions use 13-bit width and height fields; formats 0x14/0x18 decode as BC1/BC3. Independent synthetic red-block decoding test validates the wrapper/codec, not actual game shader colour. Upstream [MT texture format notes](https://github.com/wmltogether/MT-Framework-Tool/blob/master/texture-format.txt) corroborate these encodings and warn of variant 0x2b channel interpretation. That variant remains refused.

## External checks

Sources accessed 2026-11-03: Evil Resource's own [RE0 maps index](https://www.evilresource.com/resident-evil-zero/maps) and six regional pages linked in floor-crosscheck.json. Their 23 floor headings match the regional GUI group catalogue. This is a floor-catalogue claim only; the website's applicability to the exact HD build has not independently been established.

The six source pages contain 124 distinct external location IDs (split image-map polygons retained under one ID). Train room-name/floor correspondences now cover 19 external places and 21 native pieces, visually reviewed against the source image and native resource geometry. See room-crosscheck.json and ../data/room-matches.json. Other 105 external places remain unmapped. No door-connection, item-placement, difficulty or spawn-condition match is claimed. Korean names are proposed project translations, not verified installed-game terminology. The HTML is kept locally under local/external; only extracted factual identifiers/geometry and source URLs are in data/external-locations.json.

## Executed checks

- Read-only inventory: all members in maploc.arc, map.arc and map_eng.arc decompress with exact stream/size boundaries.
- Static resource preview: all 23 floor scenes generated; 292 sprites drawn and zero resource omissions within room-floor groups. Exact shared Japanese texture paths are resolved from map_jpn.arc; no language aliases are guessed. Room floor groups are rendered; separate door groups are not rendered yet.
- Offline review page built with floor selection, diagnostic pan/zoom, sprite inspection and PNG export.
- 35 portable tests passed: archive boundaries, decompression limits and size, mloc shape, GUI scalar/vector pools and packed counts, unknown array preservation, malformed references, hierarchy cycles, BC3 sample, source parser/duplicates/geometry, PE32 inventory/truncation, shared C zoom/quad/UV boundaries, resource-class hashes, event group bounds/zero offsets, curated-room identity/floor/hash validation, review-page interactions with a mocked DOM/canvas. These are not browser/GPU or gameplay tests.
- Bounded original-x86 execution: native map method `0x5b5320` executed under Unicorn; 56 progress/focus/dense/sparse cases match shared C scale/translation setter values bit-for-bit (float32). See native-zoom.json. No game process is involved.
- Byte evidence: 13 native signatures and two strings verified; all non-.text bytes match original.

## Gate and limitations

W0/G0 remains OPEN. Resource-reader contracts are known, but runtime state/zoom/clip/input contracts are not ready for ASI work. W1 and W2 received resource-only research prototypes; their completion gates remain OPEN.

- Diagnostic centre anchoring/background and arbitrary scale/pan are explicit preview choices. Native setter arithmetic is now shared C and independently checked, but its composition with parent matrices is not yet verified. ControlPoint and supplied-matrix quad arithmetic are verified against native execution. Native viewport, parent-matrix construction, animation evaluation, zoom limits and pixel agreement require further native tracing and independent capture comparison.
- Default static visibility is read; visited/revealed/save eligibility is not implemented. Player markers, dynamic dropped items, enemies, game-state capture and shared annotation eligibility/placement core are absent. The shared C core currently contains native map transform, anchor/quad and UV arithmetic; annotation eligibility/placement is absent.
- Shared icon references now resolve by exact resource path. These are resource-level results; the game loader’s language substitution behavior is not claimed.
- Door instances lack verified destination/lock semantics. Fixed item extraction and external item/door cross-check are not implemented.
- Existing re0box source is available from [upstream](https://github.com/descawed/re0box); its version tables are research leads, not byte-verified addresses for this mod. Existing game mods/settings were not changed.

## Next bounded work

1. Trace uGUIMap/uGUIMapCommon state ownership and native transform setters; validate ControlPoint, hierarchy transform, clip and scene transitions before declaring emulator parity.
2. Resolve explicitly referenced shared textures and TEX 0x2b shader interpretation; implement door drawing separately from door gameplay logic.
3. Trace native room/item/door tables and conditions, establish runtime state contract, then correlate the 124 source locations with native IDs using independently checked geometry and evidence.
4. Batch the smallest read-only game reference capture request only after all required fields/scenes are known. Do not launch a game or install a capture plugin automatically.

Research source revisions: Steamless `cd770bf9749d3e4f438d23ac643917ad1a804257`, re0box `067c0143e695a2a560f86a684eeea10b82ea3edb`.

## Native zoom helper evidence

`0x5b5320` takes a float progress argument, calculates `1 + 2*t`, and visits 12 pairs of optional GUI instances. Non-unit scale uses focus from `[[map+0x278]+0x5c/+0x60]`, centre constants (640,360), multiplier -3 and progress t. It applies scale X/Y through 0x880a20/0x880a50 and translation X/Y through 0x880610/0x880640. The unit-scale branch resets translations to positive zero. All 56 test cases compare the actual returned setter argument bits, with sparse and full instance arrays. This establishes the helper arithmetic, not the caller's valid progress range, input mapping, native viewport or final rendered pixels.

## Additional offline implementation — 2026-11-03

- Native anchor/quad helpers 0x892680/0x889300 and the normal-winding vertex-emission prefix 0x8918d0 were executed under Unicorn. Shared C matches 162 quad cases and 15 UV cases bit-for-bit, including nine anchors, both Y signs, supplied affine matrices, reversed UV rectangles and sampler half-texel behavior. Scope is bounded helper calculations, not a renderer/GPU acceptance test.
- Every preview sprite now calls shared C geometry and UV routines. Pillow uses those source extents, but its raster filtering is not claimed pixel-identical to D3D9.
- Native room ID helper 0x61a260 adds the region base table at 0xdb0b70 to the local room index; prefix lookup 0x61a500 uses 0xdb1110. Main region bases are tr=0, sh=36, dm=86, ch=99, bt=132, pl=141, next region=175. All 175 mloc slots agree with these ranges. They remain room slots, not a count of physical locations.
- Scene metadata: 159/175 main room slots have scene archives, containing 218 rEventScript resources and 2,406 unclassified groups. One group in event/pl0b has offset zero; the index preserves it as unresolved. The 16 absent scene slots are listed explicitly, without treating them as corrupt/missing gameplay data.
- Type identities derive from complement CRC32 masked to 31 bits and native class strings: rEventScript=0x714ec77c, rSceneInfo=0x0b2face7, rEventCollision=0x2b399b97, rCollision=0x51fc779f, rCutScrParamPackage=0x04e9ebe9. The cut parameter package is not used as an item database.
- Train source images were accessed 2026-11-03 at the map image URLs retained in room-matches.json. The 19 mappings are scoped to room names/floor geometry. Two pairs of native section variants share external places; their eligibility remains unresolved. The offline review page can show internal IDs, English names and proposed Korean translations, and shows bracketed IDs for unmapped pieces.

## Adapter work — 2026-11-03

The earlier no-ASI boundary described the then-unproven draw route. Native instance animation/sprite dispatch and viewport shader constants are now bounded-tested, and the source links an actual room-overlay ASI. There are 26 static signatures, 39 portable tests, 8 compiled synthetic adapter cases and 24 native viewport cases. See the [render contract](../schemas/render-contract.md) for addresses, artifacts and limitations. Native instance scissor, final composition and full item/door/enemy/state semantics remain open; no game/GPU acceptance is claimed.
