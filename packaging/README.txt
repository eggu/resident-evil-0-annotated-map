RE0 Annotated Map - Survivor's Notes - Resident Evil 0 HD REMASTER
상세 지도: 생존자의 메모

지원: Steam 또는 GOG판 Resident Evil 0 / biohazard 0 HD REMASTER(re0hd.exe) + Ultimate ASI Loader(포함).
게임 지도에 방 이름, 잠긴 문, 핵심 아이템, 문서·지도, 퍼즐, 이벤트, 일반 아이템, 적을 표시합니다.

설치
1. 게임을 종료합니다.
2. re0hd.exe가 있는 폴더를 엽니다.
   Steam: 라이브러리에서 게임을 우클릭 → 관리 → 로컬 파일 탐색.
   GOG: GOG Galaxy에서 게임 → 설치 관리 → 폴더 표시.
3. ZIP의 내용을 그 폴더에 폴더 구조 그대로 복사합니다.
   (dinput8.dll, scripts/RE0.AnnotatedMap.asi, scripts/RE0.AnnotatedMap.bgra,
    scripts/RE0.AnnotatedMap.icons.bgra, scripts/RE0.AnnotatedMap.ini)
   다른 ASI 모드로 dinput8.dll이 이미 있으면 dinput8.dll은 건너뛰고 scripts만 복사하세요.
4. 게임을 실행하고 지도를 엽니다.
업그레이드할 때는 기존 scripts/RE0.AnnotatedMap.ini를 건너뛰거나 백업 후 복원하세요.

사용 (지도 화면에서만 작동)
- 숫자 키: 0 전체 표시, 1 방 이름, 2 잠긴 문, 3 핵심 아이템, 4 문서·지도, 5 퍼즐,
  6 이벤트(스포일러, 처음에는 꺼짐), 7 일반 아이템, 8 적,
  9 표시 범위(방문한 방 → 공개된 방 → 모든 방), \(₩) 한국어 / English.
- 이름 크기: - · + (숫자패드 포함), 불투명도: [ · ]
- 아이콘 크기: Ctrl + - · +, 불투명도: Ctrl + [ · ]
- 아이템 이름: H (모두 → 일반 아이템 제외 → 끔, 처음에는 끔). 범례 접기: ~ (1 왼쪽 키)
- 기본값: 한국어, 이름 100%, 불투명도 60%, 아이콘 100%, 아이콘 불투명도 80%, 방문한 방만 표시.
- 표시는 게임 진행을 따릅니다. 주운 아이템, 푼 퍼즐, 연 문, 처치한 적은 사라지고, 난이도는 게임에서 읽습니다.
- 설정은 scripts/RE0.AnnotatedMap.ini에 저장됩니다. [Colors]에서 분류별 색을 #RRGGBB로 바꿀 수 있습니다(저장해도 그대로 남습니다).

제거
scripts의 RE0.AnnotatedMap으로 시작하는 파일을 지웁니다. 다른 ASI 모드가 없으면 dinput8.dll도 지웁니다.
EXE와 세이브는 수정하지 않습니다.

제작: 커트씨. 비공식 팬 모드입니다. Capcom과 관련이 없으며 게임 파일을 포함하지 않습니다.
소스 라이선스는 LICENSE.txt(MIT), 참고 자료와 글꼴 출처는 NOTICE.md에 있습니다.
https://github.com/eggu/resident-evil-0-annotated-map

================================================================
English
================================================================

Supported: Resident Evil 0 / biohazard 0 HD REMASTER, Steam or GOG version (re0hd.exe)
+ Ultimate ASI Loader (included).
Shows room names, locked doors, key items, files and maps, puzzles, events, common items
and enemies on the game's map.

Installation
1. Close the game.
2. Open the folder containing re0hd.exe.
   Steam: in your library, right-click the game -> Manage -> Browse local files.
   GOG: in GOG Galaxy, open the game -> Manage installation -> Show folder.
3. Copy the ZIP contents into that folder, keeping the folder structure
   (dinput8.dll, scripts/RE0.AnnotatedMap.asi, scripts/RE0.AnnotatedMap.bgra,
    scripts/RE0.AnnotatedMap.icons.bgra and scripts/RE0.AnnotatedMap.ini).
   If you already have a dinput8.dll from another ASI mod, skip it and copy scripts only.
4. Launch the game and open the map.
When upgrading, skip scripts/RE0.AnnotatedMap.ini or back it up and restore it.

Controls (on the map screen only)
- Number keys: 0 all annotations, 1 room names, 2 locked doors, 3 key items, 4 files/maps, 5 puzzles,
  6 events (spoilers, off at first), 7 common items, 8 enemies,
  9 scope (visited -> revealed -> all rooms), \ (won sign on Korean keyboards) Korean / English.
- Name size: - · + (numpad too). Opacity: [ · ]
- Icon size: Ctrl + - · +. Icon opacity: Ctrl + [ · ]
- Item names: H (all -> all except common items -> off; off at first). Fold the legend: ~ (key left of 1)
- Defaults: Korean, name size 100%, opacity 60%, icon size 100%, icon opacity 80%, visited rooms.
- Marks follow your progress: taken items, solved puzzles, opened doors and defeated enemies disappear,
  and the difficulty is read from the game.
- Settings are saved in scripts/RE0.AnnotatedMap.ini. [Colors] sets a colour per category as #RRGGBB (saving keeps it).

Uninstall
Delete the files in scripts that start with RE0.AnnotatedMap. If you have no other ASI mods, delete dinput8.dll too.
The EXE and saves are not modified.

Created by 커트씨. Unofficial fan mod, not affiliated with Capcom. No game files are included.
Source license: LICENSE.txt (MIT). References and font credits: NOTICE.md.
https://github.com/eggu/resident-evil-0-annotated-map
