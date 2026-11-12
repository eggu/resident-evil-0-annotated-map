# RE0 Annotated Map - Survivor's Notes 1.1.0

An ASI mod for Resident Evil 0 / biohazard 0 HD REMASTER (Steam or GOG) that adds annotations to the game's own map screen.

## English

- New in 1.1.0: Leech Hunter support. Items, Leech Charms and enemies are shown for the Leech Hunter layout you are playing (the game picks one of five), and enemies that appear after 90 charms are shown once they appear. The room list panel is not shown in Leech Hunter.
- Also new: puzzle marks for the crates, piano, chessboard and control panel, an Elevator mark for the storage lift, and the keycard lock moved onto the engine room door.
- Also works with the GOG version; the mod no longer checks the EXE hash or build string.
- Shows room names, locked doors, key items, files and maps, puzzles, events, common items and enemies, each with its own icon and colour.
- Annotations follow your progress: taken items, solved puzzles, opened doors and defeated enemies disappear, and items that appear later in the story or as Leech Hunter rewards are shown when they become available.
- The difficulty is read from the game, so the items and enemies shown match the difficulty you are playing.
- Events are marks for story scenes, shown as a purple `?` (off at first because they are spoilers). They disappear once the event has happened.
- Choose how much to reveal: visited rooms (default), rooms revealed by a map, or all rooms.
- Korean and English. Number keys 0-9 switch each category, `\` (`₩` on Korean keyboards) switches the language, and a legend on the map shows the current state.
- Adjust name size and opacity, icon size and opacity (with Ctrl), item names (H) and fold the legend (~). Settings are saved to `scripts/RE0.AnnotatedMap.ini`, including optional per-category colours.
- Room names are placed inside each room's real shape and follow the game's map zoom and scrolling.
- Installation: copy `dinput8.dll` ([Ultimate ASI Loader](https://github.com/ThirteenAG/Ultimate-ASI-Loader), included) and `scripts/` into the folder with `re0hd.exe`. If you already have a `dinput8.dll`, copy `scripts/` only. Close the game first.
- The executable and saves are not modified.

Known limits: marks show the room, not the exact spot inside it; on crowded rooms some names of common items and enemies may be hidden.

## 한국어

Steam·GOG판 Resident Evil 0 / biohazard 0 HD REMASTER의 지도 화면에 주석을 더하는 ASI 모드입니다.

- 1.1.0 변경: Leech Hunter를 지원합니다. 게임이 다섯 가지 중 하나를 고르는 Leech Hunter 배치에 맞춰 아이템, 거머리 부적, 적을 표시하며, 부적 90개 뒤에 나타나는 적은 나타난 뒤에 표시됩니다. Leech Hunter에서는 방 목록 패널을 표시하지 않습니다.
- 또한 상자, 피아노, 체스판, 제어판 퍼즐 표시와 창고 승강기의 엘리베이터 표시를 추가하고, 카드키 잠금을 기관실 문으로 옮겼습니다.
- GOG판에서도 작동합니다. 모드가 더 이상 EXE 해시와 빌드 문자열을 확인하지 않습니다.

- 방 이름, 잠긴 문, 핵심 아이템, 문서·지도, 퍼즐, 이벤트, 일반 아이템, 적을 분류별 아이콘과 색으로 표시합니다.
- 진행에 따라 표시가 바뀝니다. 주운 아이템, 푼 퍼즐, 연 문, 처치한 적은 사라지고, 이야기 진행에 따라 나타나는 아이템과 Leech Hunter 보상은 얻을 수 있게 되면 표시됩니다.
- 난이도는 게임에서 읽으므로, 플레이 중인 난이도에 맞는 아이템과 적이 표시됩니다.
- 이벤트는 이야기 장면의 표시로, 보라색 `?`입니다(스포일러라 처음에는 꺼짐). 이벤트가 일어나면 사라집니다.
- 표시 범위를 고릅니다: 방문한 방(기본), 지도로 공개된 방, 모든 방.
- 한국어/영어를 지원합니다. 숫자 키 0–9로 분류별로 켜고 끄고, `\`(한국어 키보드에서는 `₩`)로 언어를 바꾸며, 지도의 범례에 현재 상태가 표시됩니다.
- 이름 크기·불투명도, 아이콘 크기·불투명도(Ctrl과 함께), 아이템 이름(H), 범례 접기(~)를 조절할 수 있습니다. 설정은 `scripts/RE0.AnnotatedMap.ini`에 저장되며 분류별 색도 바꿀 수 있습니다.
- 방 이름은 방의 실제 모양 안쪽에 놓이고, 게임의 지도 확대·이동을 따릅니다.
- 설치: `dinput8.dll`([Ultimate ASI Loader](https://github.com/ThirteenAG/Ultimate-ASI-Loader), 포함)과 `scripts/`를 `re0hd.exe`가 있는 폴더에 복사합니다. `dinput8.dll`이 이미 있으면 `scripts/`만 복사하세요. 먼저 게임을 종료하세요.
- 실행 파일과 세이브는 수정하지 않습니다.

알려진 제한: 표식은 방 안의 정확한 위치가 아니라 방을 알려 줍니다. 붐비는 방에서는 일반 아이템과 적의 이름 일부가 숨겨질 수 있습니다.
