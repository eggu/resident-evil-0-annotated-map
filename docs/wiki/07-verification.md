# 07 검증 절차

[한국어](07-verification.md) | [English](07-verification.en.md) · [Index](README.md)

경로는 RE0 프로젝트 루트 기준입니다. 인용은 파일과 함수 이름만 적고 줄 번호는 적지 않습니다.

## 일반 규칙 (다른 RE 시리즈 공통)

### 증거 수준

따로 보고하며 하나로 다른 것을 대신하지 않습니다.

| 수준 | 의미 | 보여줄 수 없는 것 |
| --- | --- | --- |
| 정적 | 코드·데이터 판독, 역어셈블 | 실행되는지 |
| 합성 | 오프라인 하니스, 에뮬레이터, 합성이라 표시한 손으로 만든 상태 | 게임이 같게 동작하는지 |
| 네이티브 구축 | 게임 자체의 생성자와 함수를 x86 에뮬레이터에서 실행, 실제 vtable 슬롯으로 후크에 도달 | D3D, GPU, 실제 리소스, 타이밍 |
| 캡처 상태 재생 | 실제 캡처(F8)를 공용 코드로 재생 | 화면이 맞아 보이는지 |
| 이미지 비교 | 에뮬레이터 이미지와 게임 스크린샷 비교 | 동작 |
| 실게임 | 실행 중인 게임에서 확인 | 다른 해상도, 빌드, 모드 |

에뮬레이터가 성공해도 게임에 대해서는 아무것도 증명하지 않습니다. 가정한 상자에서 시작해 후크를 우회하는 리소스 미리보기나 배치 재생을, 런타임이 무엇을 캡처하거나 표시한다는 증거로 인용해서는 안 됩니다.

### 규칙

1. ASI와 에뮬레이터는 **하나의 공용 판단 모듈**을 씁니다. 한 구현을 똑같은 복사본에 대해서만 검증하지 않습니다.
2. **오프라인 증거는 게임의 경로를 따릅니다.** 객체 필드 값은 게임의 생성자·세터나 실게임 캡처에서 오며 손으로 쓴 픽스처만으로는 안 됩니다. 후크는 네이티브 디스패치와 실제 슬롯으로 도달합니다.
3. **공용 코드는 네이티브 코드가 그리는 것을 거부하면 안 됩니다.** 차분 검사는 작성자가 기대한 값만이 아니라 필드의 포장된 전체 범위를 표본으로 삼습니다(4비트로 마스크되는 기준 필드를, 테스트가 마스크된 값만 써서 거부했던 일).
4. **실게임에서 난 모든 실패는 네이티브 디스패치 검사의 변이체가 되고** 관찰된 값은 실게임 표본 픽스처에 들어갑니다. 살아남은 변이체가 있으면 패키징하지 않습니다. 변이체를 돌리기 전에 계약 테스트가 실제 코드에서 통과해야 합니다. 그렇지 않으면 항상 실패하는 계약이 모든 변이체를 잡은 것처럼 보입니다.
5. **모든 버림을 셉니다.** 카운터 없이 데이터를 버리는 후크 경로는 결함입니다.
6. **예시가 아니라 전체 데이터.** 제보는 예시이므로 같은 조건의 모든 행을 검사합니다.
7. **재현 가능한 빌드.** 두 번 컴파일해 바이트를 비교하고, 패키지 내용을 멤버와 대조하며, 생성된 헤더·아틀라스·아이콘 텍스처가 생성 기록의 해시 및 입력 해시와 맞지 않으면 패키징을 거부합니다.
8. 릴리스마다 **각 검사가 무엇을 실행하지 않았는지** 적습니다.

### 실게임 캡처 절차

1. 사용자에게 확인할 상태(층, 확대, 프레임 켬/끔, 목록 열림/닫힘)로 지도를 열고 캡처 키를 누르게 합니다. 같은 순간의 스크린샷을 잘라내지 않은 원본 크기로 요청합니다.
2. 캡처 키는 JSON 캡처(방 상자, 장애물, 설정, 진행 플래그, 완료 표식), 다음 한 프레임 전체의 스프라이트 덤프(스키마 버전 포함), 번호가 붙은 배치 행 덤프를 씁니다. 스프라이트 덤프와 캡처는 이전 파일을 덮어쓰고, 행 덤프는 덮어쓰지 않습니다(상한까지 비어 있는 첫 번호).
3. **다음 캡처 전에 모든 파일을 날짜 폴더에 복사합니다**(`local/live/...`). 다음 누름이 덮어씁니다.
4. 같은 뷰에 대한 공용 코드의 연산과 스크린샷을 비교하고, 관찰한 값을 실게임 표본 픽스처에 넣고, 결함마다 변이체와 테스트를 만듭니다.
5. 캡처가 증명하는 것은 좌표와 플래그뿐이며 GPU 출력이 아닙니다. 세이브, 인벤토리, 개인 정보는 없습니다.

### 설치 규칙

- 네이티브 디스패치 게이트를 통과한 후보만 설치하고, 빌드 보고서에 게이트가 실행되지 않았다고 되어 있으면 거부합니다.
- 게임이 실행 중이면 거부하고(종료를 기다리며 절대 끄지 않음), 지원하지 않는 실행 파일 해시, 빌드 보고서와 다른 ZIP도 거부합니다.
- 각 파일은 임시 파일과 원자적 이름 변경으로 교체하고 해시를 검증하며, 사용자의 INI는 없을 때만 만듭니다.
- 게임 폴더의 다른 파일(실행 파일, 로더, 다른 모드와 그 INI)의 해시가 전후로 같은지 확인합니다.
- 설치 기록(시각, 빌드, 파일과 해시)을 남깁니다.
- 게임을 실행하거나 끄지 않으며 공개 배포하지 않습니다.

## RE0 HD Remaster 전용

### 빌드와 게이트

`build.py --test`(`build.py`):

1. `tools/build_core.py`: `map_transform.c`, `annotation.c`, `frame.c`를 에뮬레이터용 `local/libre0map.dylib`로 컴파일(clang, `-ffp-contract=off`). `frame.c`, `annotation.c`, `src/wasm/glue.c`의 wasm 빌드는 검수 페이지에 쓰입니다(`tools/build_core.py`).
2. `python -m unittest discover -s tests -v`.
3. 분석 이미지(배포하지 않음)가 있으면 `tools/inspect/check_hook_classes.py`와 `tools/inspect/check_native_dispatch.py`를 실행하고 `gate_passed = True`. 이미지가 없으면 게이트가 실행되지 않습니다.
4. 아틀라스와 아이콘 텍스처의 크기·SHA-256을 `verification/label-build.json`과, 생성된 헤더·입력 해시에 대조합니다(`build.py`).
5. `i686-w64-mingw32-gcc`로 ASI를 크로스 컴파일(`-std=c11 -O2 -Wall -Wextra -Werror -shared`, 이미지 베이스 `0x62000000`, dynamicbase, nxcompat)하고 두 번 컴파일해 바이트를 비교하며 x86 DLL인지 확인합니다.
6. `tests/runtime_probe.c`를 컴파일해 `tools/inspect/check_adapter.py`를 실행합니다(합성 어댑터 케이스 8개, `verification/adapter-synthetic.json`).
7. 릴리스 ZIP `dist/RE0-Annotated-Map-<버전>.zip`(멤버: 로더 `dinput8.dll`, ASI, `.bgra`, `.icons.bgra`, `.ini`, 로더 라이선스, README, `LICENSE.txt`, `NOTICE.md`)과 `dist/build-report.json`을 씁니다.

수치: 테스트 189개, 네이티브 디스패치 변이체 73개 포착, 어댑터 케이스 8개 (73개는 `verification/native-dispatch.json`에도 나열). `build.py --test`는 항상 전체 게이트를 돌립니다. `RE0_QUICK=1`은 프레임 변이체를 건너뛰고(약 2초 대 23초), `check_native_dispatch.py --quick`은 변이체 없이 게이트만 돌리며(약 4초) 기록하지 않습니다(`docs/DEVELOPMENT.md`).

### 네이티브 디스패치 게이트

`tools/inspect/check_native_dispatch.py`(약 60 KB). 증거: `original-x86-constructors-and-dispatch-through-real-hook-slots`(`verification/native-dispatch.json`): 지도 그리기 -> 루트 순회 -> 인스턴스 -> 애니메이션 -> 스프라이트를 네이티브 vtable과 생성자로. 스텁: 스프라이트 방출과 노드별 준비. 미포함: D3D/GPU, Present 타깃, 네이티브 행렬 생성, 실제 리소스 로딩. 보고서의 게이트: `aspect_gate`, `lock_gate`, `overlay_gate`, `ini_gate`, `scope_gate`, `arrange_gate`, `enemy_gate`, `emulator_gate`, `flag_gate`, `fade_gate`.

변이체(73개)는 실게임 실패의 이름을 따릅니다. 예: `21:9 overlay ignores the render rect`, `icons drawn without mips`, `freed slot draws its stale bytes`, `dropped room read from row +0`, `killed enemy stays shown`, `mark tied to one piece of its room (Ice Pick)`, `Conductor's Key on the Cabin 201 door`, `All patch opens the floor tabs too`, `fade only: stale capture drawn when a fast fade returns to clear`, `map state ignored at Present`. 전체 목록은 `verification/native-dispatch.json`의 `mutants_caught` 키입니다.

프레임 변이체(오버레이 규칙): `tests/test_frame.py`의 `MUTANTS` 표(파일의 패턴 계산으로 57개이며 이 위키를 위해 실행하지는 않음), 계약은 `tests/frame_contract.py`. 각 항목은 화면에서 발견된 결함이나 그 이웃을 재현합니다.

### 그 밖의 검사

| 검사 | 증명하는 것 | 결과 파일 |
| --- | --- | --- |
| `tools/inspect/check_zoom.py` | 공용 확대 수식이 네이티브 `0x5b5320`과 56개 케이스(비트 패턴)에서 같음 | `verification/native-zoom.json` |
| `tools/inspect/check_geometry.py` | 사각형(162)과 UV(15) 코드가 기준 `0xff5` 포함 네이티브 `0x892680/0x889300/0x8918d0`과 같음 | `verification/native-geometry.json` |
| `tools/inspect/check_draw_route.py` | 인스턴스 -> 애니메이션 -> 스프라이트 디스패치와 뷰포트 셰이더 상수(24케이스, 0.001px 미만) | `verification/native-draw-route.json` |
| `tools/inspect/check_hook_classes.py` | 방 인스턴스가 클래스 `cGUIInstAnimation`(클래스 이름 CRC), vtable `0xd25448`, 슬롯 `0xd25478` | `verification/hook-classes.json` |
| `tools/inspect/verify_native.py` | 실행 파일·분석 이미지 해시, 제한된 서명 | `verification/native-evidence.json` |
| `tools/crosscheck/state_flags.py` | 네이티브 함수의 Unicorn 실행으로 본 행별 완료 상태: `0x59b8d0` 0..0xffff, `0x40fd70`, `0x410610`, `0x410bb0`, `0x4101f0`+`0x40fb10`, `0x4de730`, `0x412060`, 불일치 0 | `verification/state-flags.md` |
| `tools/extract/room_state.py` | 방문 규칙이 요구하는 플래그의 AND임을 모든 조합에서 증명 | 빌드 단계 |
| `tests/test_placements.py`(32개), `test_conditions.py`(13), `test_enemy_state.py`(13), `test_drops.py`(9), `test_events.py`(6), `test_icons.py`(8), `test_room_layout.py`(10), `test_review1.py`(20) ... | 파서는 틀린 레이아웃을 거부하고, 데이터는 신뢰할 수 있게 한 속성을 유지하며, 결함별 검사 | `tests/` |
| `tests/test_live_samples.py` | 실게임에서 본 값이 한때 거부했던 공용 코드를 통과 | `tests/fixtures/live-samples.json` |
| `tests/wasm_parity.js`, `tests/review_page_harness.js`, `tests/test_review.py` | wasm 빌드가 네이티브 빌드와 같음, 검수 페이지의 DOM/canvas 계약(실제 브라우저·GPU 아님) | |

### 에뮬레이터와 검수 페이지

- `emulator/core.py`는 ASI와 같은 C 파일로 만든 `libre0map`을 바인딩합니다. `emulator/annotations.py`는 F8 캡처를 그것으로 재생해 PNG를 만듭니다. `emulator/render.py`와 `emulator/screen.py`는 정적 GUI 리소스(23개 층, 방 스프라이트 292개)를 합성하는 진단용이며, 에뮬레이터 범위는 게임 렌더링 재현이 아니라 표시 규칙과 배치 검증으로 좁혀져 있습니다. `tools/build_placement_review.py`가 wasm `frame.c`를 canvas에서 돌리는 검토 페이지를 만듭니다.
- 에뮬레이터가 실행하지 않는 것: 애니메이션된 GUI 속성, 네이티브 클리핑, TEX 코덱 `0x2b`, 게임플레이 가시성, 플레이어, 합성 체크박스 없는 버린 아이템, 실제 필터링이나 GPU 출력. 버린 아이템 에뮬레이션에는 SYNTHETIC 표시가 있습니다.
- 에뮬레이터 색: 단일 표본에서 채움 규칙이 채널당 5 이내로 게임과 일치하고, 배경은 게임보다 밝으며 옆 블러, 프레임 아트, 비네트는 재현하지 않습니다.

### 설치

개발 빌드를 게임 폴더에 설치할 때는 공개 저장소에 포함되지 않은 로컬 도우미 스크립트를 썼습니다. 플레이어는 [README](../../README.ko.md)의 안내대로 릴리스 ZIP을 설치합니다.

### 검사가 다루지 않은 것

- 게임 자체: D3D 픽셀, 실제 GPU 필터링과 밉 LOD, 실제 드라이버에서의 상태 복원, `RE0.NoUIWait`에서의 실제 페이드 타이밍, Windows, 다른 모드.
- 실측한 해상도 외의 프레임 사각형, 전환 애니메이션.
- 버린 아이템의 파트너·시나리오 차이, 여러 층 방 13개 중 11개의 버린 아이템 층.
- 이벤트 내용: 컷신을 본 사람은 없습니다.
- `~`, Ctrl 키, Windows에서의 INI 읽기·쓰기는 공용 C 코드로만 테스트했습니다.

### 문서와 코드의 불일치

- `docs/DEVELOPMENT.md`와 `schemas/render-contract.md`는 EndScene에서 스냅샷을 한 번만 쓰고 100 ms 나이 한계를 두는 그리기를 설명하지만, 코드는 Present에서 그리며 최신 캡처를 다시 그리고 250 ms 한계와 세대 래치를 씁니다.
