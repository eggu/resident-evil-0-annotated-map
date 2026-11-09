# Event audit

As of 2026-11-05. Static reading of every main-game room script in `nativePC/arc/scene`; no game run, and no cutscene viewed. Rules are in `tools/extract/events.py`. `script_read` is only that: the script has a done flag and a mark can follow it. It does not show what the scene shows.

In scope: groups that reach `Demo_Start` or `PlayMovie`, or with no cutscene turn an enemy on (`SetEnemyFlag x,1`). Out of scope, with no row: groups with neither, such as messages, doors and pickups. An enemy that appears through the table's own condition with no script group is not an event here.

## What tags mean
The loader is known: `0x57d100` reads up to 32 headers to `+0x70`, stride 0x10 (tag, offset, x, y). The native code that picks a group by tag was searched for and not found: the search covered tag comparisons in `0x4d0000`-`0x640000`, table accessors and jump tables. `0x583260` has a 47-case table but takes an actor command's argument (`0x56ad1a`) and has no case for 17 or 18, so it is not this. Tag meanings are therefore observed:

- 2, 14: `x` below the volume count of `<scene>b` in 384/394 and 11/11 groups. Treated as volumes.
- 17: `x` is an item in that room's table in 2/2. 25, 39: `x` is an enemy kind in that room in 14/14 and 1/1, not used for position.
- 4, 5, 6, 12, 31, 35, 36, 38 and others: no position rule. Room level, named Event (room). Its floor is the first piece's and it is not where the event happens.

## Limits
- Variant scene files with no map piece are unresolved; most repeat a script already read.
- `need` is only the first such flag.
- Stinger: `tr0b` g6 was not confirmed by viewing movie 11.

## Groups
Tag 18 is omitted: all excluded.

| Scene | Group | Tag | x | Basis | Scenes | Enemy flags | Done | Need | Status | Reason | Position |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bt00 | 4 | 6 | 0 | enemy on |  | [115] | 62 |  | script_read | done flag 0x3e | room level, corner of its first piece, exact position unresolved |
| bt02 | 5 | 2 | 4 | cutscene | Demo_Start 179 |  |  |  | unresolved | no flag decides it has happened |  |
| bt02 | 12 | 8 | 11 | cutscene | Demo_Start 102 |  |  |  | excluded | item use, has a puzzle mark |  |
| bt02 | 13 | 4 | 12 | cutscene | PlayMovie 37 |  | 246 |  | script_read | done flag 0xf6 | room level, corner of its first piece, exact position unresolved |
| bt02 | 14 | 12 | 0 | cutscene | Demo_Start 103 | [103] | 247 |  | script_read | done flag 0xf7 | room level, corner of its first piece, exact position unresolved |
| bt04 | 4 | 8 | 2 | cutscene | PlayMovie 27 |  |  |  | excluded | item use, has a puzzle mark |  |
| bt04 | 5 | 8 | 2 | cutscene | PlayMovie 27 |  |  |  | excluded | item use, has a puzzle mark |  |
| bt05 | 4 | 6 | 0 | enemy on |  | [115] | 62 |  | unresolved | no map piece for its room |  |
| bt06 | 5 | 2 | 4 | cutscene | Demo_Start 179 |  |  |  | unresolved | no flag decides it has happened |  |
| bt06 | 12 | 8 | 11 | cutscene | Demo_Start 102 |  |  |  | excluded | item use, has a puzzle mark |  |
| bt06 | 13 | 4 | 12 | cutscene | PlayMovie 37 |  | 246 |  | unresolved | no map piece for its room |  |
| bt06 | 14 | 12 | 0 | cutscene | Demo_Start 103 | [103] | 247 |  | unresolved | no map piece for its room |  |
| bt07 | 5 | 2 | 4 | cutscene | Demo_Start 179 |  |  |  | unresolved | no flag decides it has happened |  |
| bt07 | 12 | 8 | 11 | cutscene | Demo_Start 102 |  |  |  | excluded | item use, has a puzzle mark |  |
| bt07 | 13 | 4 | 12 | cutscene | PlayMovie 37 |  | 246 |  | unresolved | no map piece for its room |  |
| bt07 | 14 | 12 | 0 | cutscene | Demo_Start 103 | [103] | 247 |  | unresolved | no map piece for its room |  |
| bt08 | 5 | 2 | 4 | cutscene | Demo_Start 179 |  |  |  | unresolved | no flag decides it has happened |  |
| bt08 | 12 | 8 | 11 | cutscene | Demo_Start 102 |  |  |  | excluded | item use, has a puzzle mark |  |
| bt08 | 13 | 4 | 12 | cutscene | PlayMovie 37 |  | 246 |  | unresolved | no map piece for its room |  |
| bt08 | 14 | 12 | 0 | cutscene | Demo_Start 103 | [103] | 247 |  | unresolved | no map piece for its room |  |
| ch01 | 4 | 6 | 3 | cutscene | Demo_Start 66, Demo_Start 64 | [83] | 404 | [403] | script_read | done flag 0x194 | room level, corner of its first piece, exact position unresolved |
| ch01 | 6 | 12 | 0 | cutscene | Demo_Start 92 |  | 213 |  | script_read | done flag 0xd5 | room level, corner of its first piece, exact position unresolved |
| ch03 | 2 | 31 | 1 | cutscene | Demo_Start 90, PlayMovie 21 | [98, 99, 113, 151, 157] | 217 | [216] | script_read | done flag 0xd9 | room level, corner of its first piece, exact position unresolved |
| ch03 | 5 | 2 | 4 | cutscene | PlayMovie 23 | [198] | 22 |  | script_read | done flag 0x16 | trigger volume 4 |
| ch03 | 6 | 6 | 0 | cutscene | Demo_Start 81, Demo_Start 82 |  | 218 |  | script_read | done flag 0xda | room level, corner of its first piece, exact position unresolved |
| ch04 | 12 | 8 | 2 | enemy on |  | [77] |  |  | excluded | item use, has a puzzle mark |  |
| ch05 | 9 | 8 | 6 | cutscene | PlayMovie 24 | [80] |  | [224] | excluded | item use, has a puzzle mark |  |
| ch05 | 10 | 8 | 6 | cutscene | PlayMovie 24 | [79] |  | [223] | excluded | item use, has a puzzle mark |  |
| ch07 | 2 | 2 | 1 | enemy on |  | [84, 163] | 226 |  | script_read | done flag 0xe2 | trigger volume 1 |
| ch08 | 4 | 8 | 1 | enemy on |  | [76] |  |  | excluded | item use, has a puzzle mark |  |
| ch0c | 2 | 2 | 1 | cutscene | PlayMovie 26, PlayMovie 25 |  |  |  | unresolved | no flag decides it has happened |  |
| ch0e | 4 | 2 | 3 | cutscene | Demo_Start 75, Demo_Start 76 |  | 235 |  | script_read | done flag 0xeb | trigger volume 3 |
| ch11 | 4 | 6 | 3 | cutscene | Demo_Start 66, Demo_Start 64 | [83] | 404 | [403] | unresolved | no map piece for its room |  |
| ch11 | 6 | 12 | 0 | cutscene | Demo_Start 92 |  | 213 |  | unresolved | no map piece for its room |  |
| ch13 | 2 | 31 | 1 | cutscene | Demo_Start 90, PlayMovie 21 | [98, 99, 113, 151, 157] | 217 | [216] | unresolved | no map piece for its room |  |
| ch13 | 5 | 2 | 4 | cutscene | PlayMovie 23 | [198] | 22 |  | unresolved | no map piece for its room |  |
| ch13 | 6 | 6 | 0 | cutscene | Demo_Start 81, Demo_Start 82 |  | 218 |  | unresolved | no map piece for its room |  |
| ch14 | 2 | 31 | 1 | cutscene | Demo_Start 90, PlayMovie 21 | [98, 99, 113, 151, 157] | 217 | [216] | unresolved | no map piece for its room |  |
| ch14 | 5 | 2 | 4 | cutscene | PlayMovie 23 | [198] | 22 |  | unresolved | no map piece for its room |  |
| ch14 | 6 | 6 | 0 | cutscene | Demo_Start 81, Demo_Start 82 |  | 218 |  | unresolved | no map piece for its room |  |
| ch15 | 2 | 31 | 1 | cutscene | Demo_Start 90, PlayMovie 21 | [98, 99, 113, 151, 157] | 217 | [216] | unresolved | no map piece for its room |  |
| ch15 | 5 | 2 | 4 | cutscene | PlayMovie 23 | [198] | 22 |  | unresolved | no map piece for its room |  |
| ch15 | 6 | 6 | 0 | cutscene | Demo_Start 81, Demo_Start 82 |  | 218 |  | unresolved | no map piece for its room |  |
| ch17 | 9 | 8 | 6 | cutscene | PlayMovie 24 | [80] |  | [224] | excluded | item use, has a puzzle mark |  |
| ch17 | 10 | 8 | 6 | cutscene | PlayMovie 24 | [79] |  | [223] | excluded | item use, has a puzzle mark |  |
| ch18 | 9 | 8 | 6 | cutscene | PlayMovie 24 | [80] |  | [224] | excluded | item use, has a puzzle mark |  |
| ch18 | 10 | 8 | 6 | cutscene | PlayMovie 24 | [79] |  | [223] | excluded | item use, has a puzzle mark |  |
| ch19 | 9 | 8 | 6 | cutscene | PlayMovie 24 | [80] |  | [224] | excluded | item use, has a puzzle mark |  |
| ch19 | 10 | 8 | 6 | cutscene | PlayMovie 24 | [79] |  | [223] | excluded | item use, has a puzzle mark |  |
| ch1c | 2 | 2 | 1 | cutscene | PlayMovie 26, PlayMovie 25 |  |  |  | unresolved | no flag decides it has happened |  |
| ch1d | 2 | 2 | 1 | cutscene | PlayMovie 26, PlayMovie 25 |  |  |  | unresolved | no flag decides it has happened |  |
| ch1f | 4 | 6 | 3 | cutscene | Demo_Start 66, Demo_Start 64 | [83] | 404 | [403] | unresolved | no map piece for its room |  |
| ch1f | 6 | 12 | 0 | cutscene | Demo_Start 92 |  | 213 |  | unresolved | no map piece for its room |  |
| dm02 | 5 | 2 | 1 | cutscene | PlayMovie 17, Demo_Start 57, PlayMovie 18 | [66, 128, 134, 138, 156] | 10 |  | script_read | done flag 0xa | trigger volume 1 |
| dm05 | 5 | 6 | 0 | cutscene | Demo_Start 59, PlayMovie 19, Demo_Start 61, PlayMovie 20, Demo_Start 62 |  | 197 |  | script_read | done flag 0xc5 | room level, corner of its first piece, exact position unresolved |
| dm0a | 8 | 2 | 3 | enemy on |  | [100, 101] | 205 |  | script_read | done flag 0xcd | trigger volume 3 |
| dm0b | 5 | 31 | 1 | cutscene | Demo_Start 56 |  | 204 | [391] | script_read | done flag 0xcc | room level, corner of its first piece, exact position unresolved |
| dm0c | 5 | 2 | 1 | cutscene | PlayMovie 17, Demo_Start 57, PlayMovie 18 | [66, 128, 134, 138, 156] | 10 |  | unresolved | no map piece for its room |  |
| pl00 | 4 | 6 | 0 | cutscene | PlayMovie 28 |  | 249 |  | script_read | done flag 0xf9 | room level, corner of its first piece, exact position unresolved |
| pl01 | 6 | 2 | 4 | cutscene | PlayMovie 30 |  | 250 |  | script_read | done flag 0xfa | trigger volume 4 |
| pl04 | 5 | 8 | 2 | cutscene | Demo_Start 108, Demo_Start 107 | [176] |  |  | excluded | item use, has a puzzle mark |  |
| pl0b | 4 | 2 | 2 | enemy on |  | [174] | 278 |  | script_read | done flag 0x116 | trigger volume 2 |
| pl0c | 5 | 8 | 2 | enemy on |  | [81] |  |  | excluded | item use, has a puzzle mark |  |
| pl0d | 11 | 6 | 0 | enemy on |  | [169] |  | [418] | unresolved | no flag decides it has happened |  |
| pl0f | 4 | 6 | 0 | cutscene | PlayMovie 31 | [95] | 258 |  | script_read | done flag 0x102 | room level, corner of its first piece, exact position unresolved |
| pl11 | 5 | 2 | 3 | cutscene | PlayMovie 32, Demo_Start 132, Demo_Start 131 |  | 241 |  | script_read | done flag 0xf1 | trigger volume 3 |
| pl13 | 5 | 35 | 48 | cutscene | Demo_Start 111, Demo_Start 110, Demo_Start 112 |  | 259 |  | script_read | done flag 0x103 | room level, corner of its first piece, exact position unresolved |
| pl14 | 4 | 2 | 2 | cutscene | Demo_Start 113, Demo_Start 114 | [91] | 261 |  | script_read | done flag 0x105 | trigger volume 2 |
| pl17 | 4 | 8 | 1 | enemy on |  | [171] |  |  | excluded | item use, has a puzzle mark |  |
| pl17 | 5 | 8 | 1 | enemy on |  | [171] |  |  | excluded | item use, has a puzzle mark |  |
| pl17 | 6 | 8 | 2 | enemy on |  | [171] |  |  | excluded | item use, has a puzzle mark |  |
| pl17 | 7 | 8 | 2 | enemy on |  | [171] |  |  | excluded | item use, has a puzzle mark |  |
| pl17 | 10 | 25 | 70 | cutscene | Demo_Start 122 | [159] | 385 |  | script_read | done flag 0x181 | room level, corner of its first piece, exact position unresolved |
| pl17 | 11 | 36 | 0 | cutscene | PlayMovie 33 |  | 384 |  | script_read | done flag 0x180 | room level, corner of its first piece, exact position unresolved |
| pl18 | 2 | 36 | 0 | cutscene | PlayMovie 34, Demo_Start 124, PlayMovie 40, PlayMovie 41, PlayMovie 42, PlayMovie 43, PlayMovie 29, Demo_Start 130, PlayMovie 35 |  |  |  | unresolved | no flag decides it has happened |  |
| pl19 | 3 | 2 | 1 | cutscene | PlayMovie 38 |  | 389 | [268] | script_read | done flag 0x185 | trigger volume 1 |
| pl1a | 6 | 2 | 4 | cutscene | PlayMovie 30 |  | 250 |  | unresolved | no map piece for its room |  |
| pl1b | 11 | 6 | 0 | enemy on |  | [169] |  | [418] | unresolved | no flag decides it has happened |  |
| pl1d | 5 | 2 | 3 | cutscene | PlayMovie 32, Demo_Start 132, Demo_Start 131 |  | 241 |  | unresolved | no map piece for its room |  |
| pl1e | 4 | 2 | 2 | cutscene | Demo_Start 113, Demo_Start 114 | [91] | 261 |  | unresolved | no map piece for its room |  |
| pl20 | 4 | 2 | 2 | cutscene | Demo_Start 123 |  |  |  | unresolved | no flag decides it has happened |  |
| sh00 | 14 | 6 | 7 | cutscene | PlayMovie 13 |  | 158 |  | script_read | done flag 0x9e | room level, corner of its first piece, exact position unresolved |
| sh00 | 15 | 2 | 11 | enemy on |  | [107, 110] | 144 |  | script_read | done flag 0x90 | trigger volume 11 |
| sh00 | 16 | 8 | 11 | enemy on |  | [108, 110] |  |  | excluded | item use, has a puzzle mark |  |
| sh00 | 17 | 8 | 11 | enemy on |  | [109, 110] |  |  | excluded | item use, has a puzzle mark |  |
| sh00 | 24 | 6 | 6 | enemy on |  | [148, 149, 150] |  |  | unresolved | no flag decides it has happened |  |
| sh00 | 25 | 8 | 11 | enemy on |  | [107, 109] |  |  | excluded | item use, has a puzzle mark |  |
| sh00 | 26 | 8 | 11 | enemy on |  | [107, 108] |  |  | excluded | item use, has a puzzle mark |  |
| sh00 | 27 | 35 | 108409 | enemy on |  | [107, 108, 109, 110] |  |  | unresolved | no flag decides it has happened |  |
| sh04 | 7 | 6 | 0 | enemy on |  | [48] | 133 |  | script_read | done flag 0x85 | room level, corner of its first piece, exact position unresolved |
| sh07 | 7 | 8 | 2 | cutscene | PlayMovie 16, Demo_Start 54, Demo_Start 55, Demo_Start 53 | [74] |  |  | excluded | item use, has a puzzle mark |  |
| sh07 | 8 | 8 | 2 | cutscene | PlayMovie 16, Demo_Start 54, Demo_Start 55, Demo_Start 53 | [75] |  |  | excluded | item use, has a puzzle mark |  |
| sh07 | 9 | 8 | 2 | cutscene | PlayMovie 16, Demo_Start 54, Demo_Start 55, Demo_Start 53 | [73] |  |  | excluded | item use, has a puzzle mark |  |
| sh09 | 7 | 8 | 4 | enemy on |  | [70] |  |  | excluded | item use, has a puzzle mark |  |
| sh0a | 14 | 6 | 7 | cutscene | PlayMovie 13 |  | 158 |  | unresolved | no map piece for its room |  |
| sh0a | 15 | 2 | 11 | enemy on |  | [107, 110] | 144 |  | unresolved | no map piece for its room |  |
| sh0a | 16 | 8 | 11 | enemy on |  | [108, 110] |  |  | excluded | item use, has a puzzle mark |  |
| sh0a | 17 | 8 | 11 | enemy on |  | [109, 110] |  |  | excluded | item use, has a puzzle mark |  |
| sh0a | 24 | 6 | 6 | enemy on |  | [148, 149, 150] |  |  | unresolved | no flag decides it has happened |  |
| sh0a | 25 | 8 | 11 | enemy on |  | [107, 109] |  |  | excluded | item use, has a puzzle mark |  |
| sh0a | 26 | 8 | 11 | enemy on |  | [107, 108] |  |  | excluded | item use, has a puzzle mark |  |
| sh0a | 27 | 35 | 108409 | enemy on |  | [107, 108, 109, 110] |  |  | unresolved | no flag decides it has happened |  |
| sh0b | 11 | 2 | 6 | cutscene | PlayMovie 15 | [94] | 26 | [163, 168] | script_read | done flag 0x1a | trigger volume 6 |
| sh0b | 12 | 2 | 7 | cutscene | PlayMovie 15 | [94] | 26 | [163, 167] | script_read | done flag 0x1a | trigger volume 7 |
| sh0e | 10 | 2 | 5 | cutscene | Demo_Start 31 |  | 146 | [145, 147] | script_read | done flag 0x92 | trigger volume 5 |
| sh0e | 15 | 6 | 6 | enemy on |  | [92, 146, 148] |  |  | unresolved | no flag decides it has happened |  |
| sh0e | 16 | 8 | 7 | enemy on |  | [177] |  |  | excluded | item use, has a puzzle mark |  |
| sh12 | 7 | 4 | 6 | enemy on |  | [59] | 169 |  | script_read | done flag 0xa9 | room level, corner of its first piece, exact position unresolved |
| sh13 | 6 | 2 | 1 | enemy on |  | [71] | 152 |  | script_read | done flag 0x98 | trigger volume 1 |
| sh18 | 7 | 6 | 0 | enemy on |  | [148, 149, 150] |  |  | unresolved | no flag decides it has happened |  |
| sh19 | 6 | 8 | 1 | cutscene | Demo_Start 41, Demo_Start 42 | [57] |  |  | excluded | item use, has a puzzle mark |  |
| sh19 | 9 | 6 | 0 | enemy on |  | [148, 149, 150] |  |  | unresolved | no flag decides it has happened |  |
| sh19 | 11 | 6 | 0 | enemy on |  | [67] |  |  | unresolved | no flag decides it has happened |  |
| sh19 | 12 | 6 | 4 | enemy on |  | [67] |  |  | unresolved | no flag decides it has happened |  |
| sh1a | 5 | 2 | 1 | cutscene | Demo_Start 43, Demo_Start 44 |  | 154 |  | unresolved | done flag 0x9a cleared again by ['sh1a:g6'] |  |
| sh1a | 7 | 8 | 2 | enemy on |  | [69] |  |  | excluded | item use, has a puzzle mark |  |
| sh1a | 9 | 6 | 0 | enemy on |  | [148, 149, 150] |  |  | unresolved | no flag decides it has happened |  |
| sh1a | 11 | 6 | 0 | enemy on |  | [69] | 155 |  | unresolved | done flag 0x9b cleared again by ['sh1a:g7'] |  |
| sh1d | 8 | 2 | 4 | cutscene | Demo_Start 38 |  | 178 |  | script_read | done flag 0xb2 | trigger volume 4 |
| sh1d | 9 | 39 | 58 | cutscene | Demo_Start 52 | [147, 148] | 177 | [178] | script_read | done flag 0xb1 | room level, corner of its first piece, exact position unresolved |
| sh1d | 15 | 17 | 68 | cutscene | Demo_Start 51 | [87, 111] | 178 |  | script_read | done flag 0xb2 | table row of item 68 |
| sh1e | 6 | 36 | 0 | cutscene | Demo_Start 30 |  | 170 |  | script_read | done flag 0xaa | room level, corner of its first piece, exact position unresolved |
| sh20 | 7 | 8 | 2 | cutscene | PlayMovie 16, Demo_Start 54, Demo_Start 55, Demo_Start 53 | [74] |  |  | excluded | item use, has a puzzle mark |  |
| sh20 | 8 | 8 | 2 | cutscene | PlayMovie 16, Demo_Start 54, Demo_Start 55, Demo_Start 53 | [75] |  |  | excluded | item use, has a puzzle mark |  |
| sh20 | 9 | 8 | 2 | cutscene | PlayMovie 16, Demo_Start 54, Demo_Start 55, Demo_Start 53 | [73] |  |  | excluded | item use, has a puzzle mark |  |
| sh22 | 11 | 2 | 6 | cutscene | PlayMovie 15 | [94] | 26 | [163, 168] | unresolved | no map piece for its room |  |
| sh22 | 12 | 2 | 7 | cutscene | PlayMovie 15 | [94] | 26 | [163, 167] | unresolved | no map piece for its room |  |
| sh23 | 11 | 2 | 6 | cutscene | PlayMovie 15 | [94] | 26 | [163, 168] | unresolved | no map piece for its room |  |
| sh23 | 12 | 2 | 7 | cutscene | PlayMovie 15 | [94] | 26 | [163, 167] | unresolved | no map piece for its room |  |
| sh24 | 11 | 2 | 6 | cutscene | PlayMovie 15 | [94] | 26 | [163, 168] | unresolved | no map piece for its room |  |
| sh24 | 12 | 2 | 7 | cutscene | PlayMovie 15 | [94] | 26 | [163, 167] | unresolved | no map piece for its room |  |
| sh26 | 6 | 2 | 1 | enemy on |  | [71] | 152 |  | unresolved | no map piece for its room |  |
| sh28 | 6 | 36 | 0 | cutscene | Demo_Start 30 |  | 170 |  | unresolved | no map piece for its room |  |
| sh29 | 14 | 6 | 7 | cutscene | PlayMovie 13 |  | 158 |  | unresolved | no map piece for its room |  |
| sh29 | 15 | 2 | 11 | enemy on |  | [107, 110] | 144 |  | unresolved | no map piece for its room |  |
| sh29 | 16 | 8 | 11 | enemy on |  | [108, 110] |  |  | excluded | item use, has a puzzle mark |  |
| sh29 | 17 | 8 | 11 | enemy on |  | [109, 110] |  |  | excluded | item use, has a puzzle mark |  |
| sh29 | 24 | 6 | 6 | enemy on |  | [148, 149, 150] |  |  | unresolved | no flag decides it has happened |  |
| sh29 | 25 | 8 | 11 | enemy on |  | [107, 109] |  |  | excluded | item use, has a puzzle mark |  |
| sh29 | 26 | 8 | 11 | enemy on |  | [107, 108] |  |  | excluded | item use, has a puzzle mark |  |
| sh29 | 27 | 35 | 108409 | enemy on |  | [107, 108, 109, 110] |  |  | unresolved | no flag decides it has happened |  |
| sh2a | 8 | 2 | 4 | cutscene | Demo_Start 38 |  | 178 |  | unresolved | no map piece for its room |  |
| sh2a | 9 | 39 | 58 | cutscene | Demo_Start 52 | [147, 148] | 177 | [178] | unresolved | no map piece for its room |  |
| sh2a | 15 | 17 | 68 | cutscene | Demo_Start 51 | [87, 111] | 178 |  | unresolved | no map piece for its room |  |
| sh2e | 10 | 2 | 5 | cutscene | Demo_Start 31 |  | 146 | [145, 147] | unresolved | no map piece for its room |  |
| sh2e | 15 | 6 | 6 | enemy on |  | [92, 146, 148] |  |  | unresolved | no flag decides it has happened |  |
| sh2e | 16 | 8 | 7 | enemy on |  | [177] |  |  | excluded | item use, has a puzzle mark |  |
| sh2f | 8 | 2 | 4 | cutscene | Demo_Start 38 |  | 178 |  | unresolved | no map piece for its room |  |
| sh2f | 9 | 39 | 58 | cutscene | Demo_Start 52 | [147, 148] | 177 | [178] | unresolved | no map piece for its room |  |
| sh2f | 15 | 17 | 68 | cutscene | Demo_Start 51 | [87, 111] | 178 |  | unresolved | no map piece for its room |  |
| sh30 | 10 | 2 | 5 | cutscene | Demo_Start 31 |  | 146 | [145, 147] | unresolved | no map piece for its room |  |
| sh30 | 15 | 6 | 6 | enemy on |  | [92, 146, 148] |  |  | unresolved | no flag decides it has happened |  |
| sh30 | 16 | 8 | 7 | enemy on |  | [177] |  |  | excluded | item use, has a puzzle mark |  |
| sh31 | 10 | 2 | 5 | cutscene | Demo_Start 31 |  | 146 | [145, 147] | unresolved | no map piece for its room |  |
| sh31 | 15 | 6 | 6 | enemy on |  | [92, 146, 148] |  |  | unresolved | no flag decides it has happened |  |
| sh31 | 16 | 8 | 7 | enemy on |  | [177] |  |  | excluded | item use, has a puzzle mark |  |
| tr00 | 2 | 2 | 1 | cutscene | PlayMovie 7, Demo_Start 19, Demo_Start 20 | [64] | 108 | [113] | script_read | done flag 0x6c | trigger volume 1 |
| tr00 | 3 | 6 | 0 | cutscene | Demo_Start 29, Demo_Start 13, Demo_Start 14 | [63] | 121 |  | script_read | done flag 0x79 | room level, corner of its first piece, exact position unresolved |
| tr01 | 3 | 6 | 0 | enemy on |  | [18, 22, 23, 24, 31] | 121 |  | script_read | done flag 0x79 | room level, corner of its first piece, exact position unresolved |
| tr02 | 1 | 31 | 0 | cutscene | PlayMovie 6 |  | 390 | [0] | script_read | done flag 0x186 | room level, corner of its first piece, exact position unresolved |
| tr02 | 6 | 2 | 5 | cutscene | Demo_Start 0 | [9, 10] | 76 |  | script_read | done flag 0x4c | trigger volume 5 |
| tr06 | 1 | 31 | 0 | enemy on |  | [145] |  |  | unresolved | no flag decides it has happened |  |
| tr06 | 2 | 31 | 1 | enemy on |  | [145] |  |  | unresolved | no flag decides it has happened |  |
| tr06 | 3 | 4 | 2 | enemy on |  | [145] |  |  | unresolved | no flag decides it has happened |  |
| tr06 | 8 | 6 | 0 | cutscene | PlayMovie 2 | [3, 4, 5] | 73 |  | script_read | done flag 0x49 | room level, corner of its first piece, exact position unresolved |
| tr06 | 9 | 38 | 0 | cutscene | PlayMovie 8 |  | 117 | [115, 116] | script_read | done flag 0x75 | room level, corner of its first piece, exact position unresolved |
| tr06 | 10 | 38 | 1 | cutscene | PlayMovie 8 |  | 117 | [68, 116] | script_read | done flag 0x75 | room level, corner of its first piece, exact position unresolved |
| tr06 | 11 | 38 | 2 | cutscene | PlayMovie 8 |  | 117 | [68, 115] | script_read | done flag 0x75 | room level, corner of its first piece, exact position unresolved |
| tr07 | 6 | 14 | 6 | enemy on |  | [1, 2] | 67 | [76] | script_read | done flag 0x43 | trigger volume 6 |
| tr07 | 7 | 6 | 1 | enemy on |  | [3, 4, 5, 11, 15, 22, 27, 35, 36, 37, 68, 69, 72, 78, 84, 86, 88, 89, 90, 96, 102, 104, 105, 112, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 152, 153, 170, 173, 175] | 63 |  | script_read | done flag 0x3f | room level, corner of its first piece, exact position unresolved |
| tr07 | 8 | 6 | 2 | cutscene | Demo_Start 16, Demo_Start 1 |  |  |  | unresolved | no flag decides it has happened |  |
| tr08 | 5 | 8 | 2 | cutscene | Demo_Start 9, Demo_Start 10 |  | 8 |  | excluded | item use, has a puzzle mark |  |
| tr08 | 11 | 6 | 0 | cutscene | Demo_Start 2 | [29] | 85 |  | script_read | done flag 0x55 | room level, corner of its first piece, exact position unresolved |
| tr08 | 13 | 22 | 0 | cutscene | Demo_Start 3 |  | 64 |  | script_read | done flag 0x40 | room level, corner of its first piece, exact position unresolved |
| tr0a | 3 | 2 | 2 | cutscene | Demo_Start 22, Demo_Start 23 |  | 110 |  | script_read | done flag 0x6e | trigger volume 2 |
| tr0a | 4 | 2 | 3 | cutscene | Demo_Start 17, Demo_Start 18 |  |  | [112] | unresolved | no flag decides it has happened |  |
| tr0a | 5 | 8 | 3 | cutscene | Demo_Start 17, Demo_Start 18 |  |  |  | excluded | item use, has a puzzle mark |  |
| tr0b | 6 | 14 | 4 | cutscene | PlayMovie 11 | [14, 97] | 78 | [120] | script_read | done flag 0x4e | trigger volume 4 |
| tr0b | 10 | 14 | 8 | cutscene | Demo_Start 4, Demo_Start 27 |  | 122 |  | script_read | done flag 0x7a | trigger volume 8 |
| tr0e | 1 | 31 | 0 | cutscene | PlayMovie 5 |  | 94 | [87] | script_read | done flag 0x5e | room level, corner of its first piece, exact position unresolved |
| tr0f | 4 | 14 | 3 | cutscene | PlayMovie 3 |  | 98 |  | script_read | done flag 0x62 | trigger volume 3 |
| tr0f | 5 | 12 | 0 | cutscene | PlayMovie 4, Demo_Start 26 | [30] | 99 |  | script_read | done flag 0x63 | room level, corner of its first piece, exact position unresolved |
| tr0f | 6 | 4 | 4 | cutscene | PlayMovie 4, Demo_Start 26 | [30] | 99 | [98] | script_read | done flag 0x63 | room level, corner of its first piece, exact position unresolved |
| tr0f | 10 | 11 | 98 | cutscene | PlayMovie 4, Demo_Start 26 | [30] |  |  | excluded | same cutscenes run from a placed group |  |
| tr10 | 1 | 31 | 0 | cutscene | PlayMovie 6 |  | 390 | [0] | unresolved | no map piece for its room |  |
| tr10 | 6 | 2 | 5 | cutscene | Demo_Start 0 | [9, 10] | 76 |  | unresolved | no map piece for its room |  |
| tr11 | 3 | 2 | 2 | cutscene | PlayMovie 9, PlayMovie 10 |  | 92 |  | script_read | done flag 0x5c | trigger volume 2 |
| tr15 | 5 | 8 | 2 | cutscene | Demo_Start 9, Demo_Start 10 |  | 8 |  | excluded | item use, has a puzzle mark |  |
| tr15 | 11 | 6 | 0 | cutscene | Demo_Start 2 | [29] | 85 |  | unresolved | no map piece for its room |  |
| tr15 | 13 | 22 | 0 | cutscene | Demo_Start 3 |  | 64 |  | unresolved | no map piece for its room |  |
| tr16 | 6 | 14 | 4 | cutscene | PlayMovie 11 | [14, 97] | 78 | [120] | unresolved | no map piece for its room |  |
| tr16 | 10 | 14 | 8 | cutscene | Demo_Start 4, Demo_Start 27 |  | 122 |  | unresolved | no map piece for its room |  |
| tr1a | 3 | 2 | 2 | cutscene | Demo_Start 22, Demo_Start 23 |  | 110 |  | unresolved | no map piece for its room |  |
| tr1a | 4 | 2 | 3 | cutscene | Demo_Start 17, Demo_Start 18 |  |  | [112] | unresolved | no flag decides it has happened |  |
| tr1a | 5 | 8 | 3 | cutscene | Demo_Start 17, Demo_Start 18 |  |  |  | excluded | item use, has a puzzle mark |  |
| tr1b | 1 | 31 | 0 | cutscene | PlayMovie 6 |  | 390 | [0] | unresolved | no map piece for its room |  |
| tr1b | 6 | 2 | 5 | cutscene | Demo_Start 0 | [9, 10] | 76 |  | unresolved | no map piece for its room |  |
| tr1e | 1 | 31 | 0 | enemy on |  | [145] |  |  | unresolved | no flag decides it has happened |  |
| tr1e | 2 | 31 | 1 | enemy on |  | [145] |  |  | unresolved | no flag decides it has happened |  |
| tr1e | 3 | 4 | 2 | enemy on |  | [145] |  |  | unresolved | no flag decides it has happened |  |
| tr1e | 8 | 6 | 0 | cutscene | PlayMovie 2 | [3, 4, 5] | 73 |  | unresolved | no map piece for its room |  |
| tr1e | 9 | 38 | 0 | cutscene | PlayMovie 8 |  | 117 | [115, 116] | unresolved | no map piece for its room |  |
| tr1e | 10 | 38 | 1 | cutscene | PlayMovie 8 |  | 117 | [68, 116] | unresolved | no map piece for its room |  |
| tr1e | 11 | 38 | 2 | cutscene | PlayMovie 8 |  | 117 | [68, 115] | unresolved | no map piece for its room |  |
| tr1f | 6 | 14 | 6 | enemy on |  | [1, 2] | 67 | [76] | unresolved | no map piece for its room |  |
| tr1f | 7 | 6 | 1 | enemy on |  | [3, 4, 5, 11, 15, 22, 27, 35, 36, 37, 68, 69, 72, 78, 84, 86, 88, 89, 90, 96, 102, 104, 105, 112, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 152, 153, 170, 173, 175] | 63 |  | unresolved | no map piece for its room |  |
| tr1f | 8 | 6 | 2 | cutscene | Demo_Start 16, Demo_Start 1 |  |  |  | unresolved | no flag decides it has happened |  |
| tr21 | 4 | 14 | 3 | cutscene | PlayMovie 3 |  | 98 |  | unresolved | no map piece for its room |  |
| tr21 | 5 | 12 | 0 | cutscene | PlayMovie 4, Demo_Start 26 | [30] | 99 |  | unresolved | no map piece for its room |  |
| tr21 | 6 | 4 | 4 | cutscene | PlayMovie 4, Demo_Start 26 | [30] | 99 | [98] | unresolved | no map piece for its room |  |
| tr21 | 10 | 11 | 98 | cutscene | PlayMovie 4, Demo_Start 26 | [30] |  |  | excluded | same cutscenes run from a placed group |  |
| tr22 | 5 | 8 | 2 | cutscene | Demo_Start 9, Demo_Start 10 |  | 8 |  | excluded | item use, has a puzzle mark |  |
| tr22 | 11 | 6 | 0 | cutscene | Demo_Start 2 | [29] | 85 |  | unresolved | no map piece for its room |  |
| tr22 | 13 | 22 | 0 | cutscene | Demo_Start 3 |  | 64 |  | unresolved | no map piece for its room |  |
