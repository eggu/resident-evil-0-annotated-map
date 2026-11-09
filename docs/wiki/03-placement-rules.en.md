# 03 Placement rules

[한국어](03-placement-rules.md) | [English](03-placement-rules.en.md) · [Index](README.en.md)

Paths are relative to the RE0 project root. Citations name files and functions, not line numbers.

## General (any RE map mod)

### Room names

1. **Fixed at generation, never moved at runtime.** A generator places each name in canvas space from the game's own room sprites; the runtime only transforms those positions through the view. Zoom and pan then keep names on their rooms with no run-time search.
2. **Real room shape, not the bounding box.** Build each room's mask from the alpha of its wall sprites; the light floor is a hole in that alpha, so close the door gaps and flood-fill from outside to get the filled silhouette. Merge all pieces of one place on one floor.
3. **Pole of inaccessibility.** Anchor the name at the cell farthest from the shape's edge (distance map; ties go nearest the centroid). Then fit the name box to the interior: among the points whose box is free of other names, take those within 0.05 of the best coverage (or coverage 1.0) and pick the one nearest the pole. A bounding-box centre can fall outside an L-shaped room.
4. **Order:** smallest rooms first (they have nowhere else to go).
5. **Corridors.** If the room is narrower than two name heights and the ideal box covers under half the shape, do not force the name inside: put it outside with a **leader line**.
6. **Leader lines.** Axis-aligned, from an edge cell of the room mask to a box in free space, shortest first. A leader may not run along a room outline (keep away from the room's corners and clear of neighbouring walls) and may not cross another name. Cap its length; a name further out no longer reads as its room's. If nothing is free, fall back to outside the floor's bounds at a price. At run time the leader end is fixed and a resized name grows away from that end.
7. **150% wrap.** A one-line name wider than 150% of its room's width wraps between words (only if it has a space).
8. **Drawn first, excluded from collision.** Room names are painted before everything else; nothing avoids them and they avoid no marks. They keep off each other and off the legend and readout panel.
9. **Both languages** are generated and checked separately.
10. **A check restated apart from the search** stops generation on a violation: fully on screen, not on the legend or readout panel, no overlap between names, outside names do not sit on a room, an anchor lies in its room's shape, a leader starts on its room and crosses no other name.

If the captured room boxes do not agree with the stored ones (view rejected), fall back to a run-time label search beside the captured boxes: try the box centre and six offsets, then rings of eight directions up to eight rings (each ring one name width/height plus margin out, tied back by an elbow leader), and last share space with other names, never with marks, doors or the legend. Show per-category counts instead of location marks.

### Marks

- **Tiers.** Key items and puzzles are never covered. Locks and documents come next. Common items and enemies may be covered or hidden.
- **Collision weights while names choose a slot:** key marks, puzzle marks, the legend and readout 8x; room names 4x; every other entry 1x. A placed key or puzzle name gets 8x, other placed names 2x.
- **Drop rule.** A lower-priority icon whose core (its middle, measured at the mark size before the zoom gain, so a bigger picture does not hide a row) touches a key or puzzle mark's core, or a key name that was not pushed out, is not drawn. A document centred on such a mark is instead moved to a badge position down and right of the mark. A common item or enemy there is dropped. Locks are exempt: a lock's key stays on its door and a mark there may cover it.
- **Event beside a key.** An event diamond that overlaps a key-item mark stands beside it (to the right if it fits on screen, else to the left) so both can be seen. An event sits over other marks without displacing them and is not counted as covering a lower-priority icon.
- **Paint order.** Lowest priority first so what must never be covered ends on top; a mark and its name are painted together.
- **Item names.** Candidate slots touch the mark with no gap: right, left, below, above, then four corner slots. Take the first slot with zero overlap score, else the least; if still overlapping, try a second ring one name height out. Names run by tier: key items, puzzles, locks, documents; common items last, and only into space that overlaps nothing of weight 2 or more, otherwise hidden. Enemies have no name.
- **Lock key centred on the door.** A lock's position is the painted centre of its door sprite. No other mark moves it. The icon keeps its size on a small door and may exceed it.
- **Hidden by the legend.** A mark whose box (diamond corners included) touches the legend or readout panel is skipped; a mark off screen is skipped, so no name is left without its mark.
- **Duplicates.** The same pickup can be listed twice (two table kinds, or a conditional row and its script twin a few pixels apart). Same category, same name and position (within 4 px, for conditional twins) shows once; each row still decides for itself whether it is visible.

### Out-of-room handling

- A position that falls outside its room's shape is snapped to the nearest cell of the shape at build time and flagged, because real 3D positions can overshoot walls drawn thin on the map.
- A row that waits under the world for a script to move it (placeholder height) has no usable x/z: use the room's centre cell and flag it.
- Events with no position use the room level (a fixed corner of the room's first piece) and are labelled so; the position is not where the event happens.
- Locks are exempt from snapping (their position is the door).
- Audit every placed row against its room's shape. Allow no unexplained row more than 12 px off.

### Frame-region avoidance

If the overlay is drawn after the game's frame (at Present), it cannot go under the frame. So avoid the frame in shared code:

- Three states: frame hidden, frame shown, frame shown with the item list open. Detect each from a sprite that is drawn only in that state (page 06).
- Keep a list of opaque frame rectangles in GUI units; scale them by the frame sprite's matrix and the game's render rectangle. The list box counts only while the list is open.
- A mark and its name are shown or dropped together at the frame; everything on the map is clipped away from the frame; the legend and panels stay on top.
- State plainly that the rectangles are measured, not native, and may misalign at other aspect ratios or during frame animation.

### Whole-data audits

When a bug report is one example, fix every row with the same condition and test over the whole data, not the example. Existing whole-data checks worth copying: every marker on every floor at game zoom and 3x with the frame on and off; every lock icon centred on its door; every mark within 12 px of its room; every duplicate group shows once; every name wraps by the rule; every icon has its art; every item id with a name has an icon or a counted fallback.

## RE0 HD Remaster specific

### Generator constants

`tools/extract/room_layout.py`, output `data/room-layout.json`, built with `--game <path>` (needs the game's `map_eng.arc` and `map.arc`; read-only).

| Constant | Value | Line |
| --- | --- | --- |
| Grid | 2 canvas px per cell | 14 |
| Fit / small fit | 0.9 / 0.8 | 17 |
| Wall margins tried | 4, 2, 0 | 18 |
| Door gap closed before fill | 7 cells | 20 |
| Leader clear / margin | 4 / 6 cells | 21 |
| Leader length cap | 30 cells (60 canvas px) | 124 |
| Mark size at its largest, on canvas | `12.6 / GRID` cells | 23 |
| Name scale | 0.3614 canvas px per raster px at size 100, zoomed out | 16 |
| 150% wrap | `lw > 1.5 * bw` | 202 |
| Corridor test | `min(bw, bh) < 2 * lh` and ideal coverage `< 0.5` | 204 |
| Pole | `pole()` | 99-102 |
| Interior spot (0.05 slack) | `interior_spot()` | 103-113 |
| Search and check | `place_floor()`, `check_floor()` | 190-234 |

Output at HEAD (`data/room-layout.json`): 248 name placements = 124 places x 2 languages; 0 with a leader; 15 wrapped. Compared with bounding-box centres: 135 moved (91 by more than 8 canvas px), 199 of 248 boxes fully inside the shape (141 of 245 before), 248 anchors inside. The leader rule stays in the code for other layouts.

Runtime: `frame.c` (`layout_ops`), fallback `frame.c` (`room_ops`) with `room_label` (`frame.c`) and `re0_place_label` (`src/core/annotation.c`: centre + 6 offsets, 2 px clearance). Names are skipped when they would sit on the legend or readout panel (`frame.c`). Docstring note: the header of `room_layout.py` still says names never overlap marks; that is now stale (`room_layout.py`, `frame.c`).

### Mark constants

| Item | Value | Source |
| --- | --- | --- |
| Max reserved boxes | 1536 | `frame.c` |
| Max obstacle side | 64 px | `frame.c` |
| Max drawn dropped items | 64 | `frame.c` |
| Weights | key and puzzle marks, legend 8; room names 4; others 1 | `frame.c` |
| Name slots | 8 (right, left, below, above, four corners) | `frame.c` |
| Core half-size | `is * 1.3 * 7 / 36` | `frame.c` |
| Badge offset | `is * 1.3 * 0.6` down and right | `frame.c` |
| Tier order for names | key, puzzle, lock, file | `frame.c` |
| Dedup distance for conditional twins | 4 px | `frame.c` |

Examples that needed the twin rule: Keycard in `pl-b7`, Book of Good in `sh-2f` (`frame.c`).

### Frame rectangles

`frame.c`. 12 rectangles in GUI 1280x720, measured from the user's 2560x1440 shot (art edges; its sprites are not all captured by the hook):

`{176,0,473,112} {176,112,461,138} {198,138,282,177} {848,0,1119,205} {925,205,1119,263} {0,448,192,720} {1088,448,1280,720} {192,538,230,582} {1050,538,1088,634} {192,662,422,720} {858,662,1088,720}` and, only while the item list is open, `{192,470,1088,720}`.

Corners are approximated by rectangles; the list-closed bottom is see-through. The three states were read from screenshots (frame on 39 sprites, off 25; open list 76). **Known limitation: measured at one resolution (2560x1440) from screenshots; other aspect ratios, transition animation and other maps than the shot's are not verified.**

### Out-of-room handling in data

`tools/extract/placements.py` (`snap_room_level`): placeholder row (world y below -1000, e.g. the Dial) takes the room's centre-most cell and `placeholder_position`; other rows outside the shape get `moved_into_room`. `verification/mark-room-audit.json`: 738 rows checked (758 placements minus 20 locks), 0 outside the shape, 0 more than 12 px away. Room-level event marks sit at `box[0] + 9, box[1] + 9` of the room's first piece (`placements.py`). One lock has no door: Keycard, room 174 (`data/placements.json` `locks_without_door`).

### Audits and numbers on record

Overlap audits are synthetic, over all rooms and floors with progress flags, counting marks / names / mark-mark / name-mark / roomname-mark / name-name overlaps: item names on, 1x `637/245/761/72/224/0`, 3x `493/188/277/29/80/1`; item names off, 1x `638/0/763/0/225/0`, 3x unchanged. The current rules allow every overlap except name-name. The audit script (`layout_audit.py`) is not in the repository; these counts cannot be reproduced from the tree (unverified).

Tests for these rules: `tests/test_room_layout.py`, `tests/test_review1.py`, `tests/test_review42.py`, `tests/test_frame_chrome.py`, `tests/frame_contract.py` (page 07).

### Unclassified

- The 150% wrap and the leader length cap (60 px) are values set for this game's art; whether they suit other games' maps is not established.
