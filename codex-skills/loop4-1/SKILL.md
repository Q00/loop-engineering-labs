---
name: loop4-1-codex
description: "Codex 앱에서 graph engineering 실습을 진행한다. 내용 5/5인 Beamer 보고서를 차트 코드 노드, 권한이 제한된 디자인 서브에이전트, XeLaTeX 빌드, 내용·본문 권한·렌더·생성물 gate로 나누고, 미달이면 디자인 노드로 되돌아가는 수렴 루프를 tail 로그와 함께 관찰한다. Triggers: loop4-1, /loop4-1, 루프 실습 4.1, 그래프 엔지니어링, graph engineering, 디자인 루프"
---

# 루프 실습 4.1: 책임이 다른 일을 노드로 나누기

이 실습은 Claude Code용 `loop4-1`을 Codex 앱에 맞게 옮긴 버전이다.

`내용 gate → 차트 코드 노드 → 디자인 에이전트 → 빌드 → 4개 gate → 미달 시 디자인으로 복귀 → 사람 확인`

핵심은 “예쁘게 만들기”가 아니다. 내용, 차트, 디자인, 빌드, 검문은 책임·권한·검증 방법이
다르므로 별도 노드가 된다. 그리고 디자인 노드 안에는 종료 조건이 있는 루프가 들어간다.

## 진행 계약

- STEP 하나가 끝날 때마다 멈추고 사용자 확인을 받는다.
- 디자인 라운드는 중간에 멈추지 않고 `design → build → gates`까지 이어서 실행한다.
- 모든 `exec_command`는 `~/.codex/skills/loop4-1/run_logged.sh`를 경유한다.
- `apply_patch`와 서브에이전트 호출 직전에는 `record_tool_call.py`로 목적·대상을 먼저 기록한다.
- `loop41-work/codex-tool-calls.jsonl`은 Codex 내부 transcript가 아니라 실습용 계측 로그라고 설명한다.
- 판정은 오직 `check.py`, `body_guard.py`, `render_check.py`, `make_chart.py --check` 출력으로 한다.
- 디자인은 `multi_agent_v1__spawn_agent`를 `fork_context: false`로 호출한다.
- 디자인 에이전트에게 gate 코드나 정답을 주지 않는다. 디자인 계약과 대상 파일만 준다.
- 디자인 에이전트는 전체 `.tex`만 반환하고 메인 에이전트가 `apply_patch`로 저장한다.
- XeLaTeX은 `build_twice.sh`로 정확히 두 번 실행한다.
- 에이전트 디자인은 최대 2라운드다. 그 뒤에는 `apply_reference_theme.py` 안전망을 사용한다.
- 안전망 사용을 에이전트 성공처럼 말하지 않는다. `agent 2회 실패 → deterministic fallback`이라고 기록한다.
- 어떤 gate든 미달이면 사람에게 넘기지 않고 디자인 노드로 돌아간다.
- 모든 gate 통과 뒤에만 사람이 before/after를 보고 취향을 판단한다.
- 기존 Claude용 스킬과 설치된 번들 파일은 수정하지 않는다. 작업은 `loop41-work/`에서만 한다.

## 아주 친절한 설명 형식

각 호출 전 다음 다섯 가지를 자연스러운 한국어로 설명한다.

> 지금 실행할 노드는 **[노드]**입니다. 이 노드의 책임은 **[책임]**이고,
> 건드릴 수 있는 범위는 **[권한]**입니다. 사용할 도구는 **[도구]**입니다.
> 옆 터미널에는 `purpose=[목적]`인 JSON 한 줄이 나타나야 합니다.
> 실행 후에는 **[파일·점수·gate 판정]**을 함께 확인하겠습니다.

결과 뒤에는 다음 관계를 짚는다.

> `tail`은 어떤 노드가 실행됐는지 보여주고, Codex 도구 블록은 실제 입력과 결과를 보여줍니다.
> gate가 X를 내면 실패를 숨기지 않고 그래프의 되돌아가는 엣지를 따라갑니다.

## STEP 0: 작업 사본과 관찰 로그 준비

첫 bootstrap은 `loop41-work/`가 아직 없으므로 바깥 로그에 남긴다.

```bash
~/.codex/skills/loop4-1/run_logged.sh loop41-bootstrap.jsonl exec_command "loop4-1 작업 사본 준비" $'mkdir -p loop41-work/data\ncp ~/.codex/skills/loop4-1/GRAPH.md ~/.codex/skills/loop4-1/design_checklist.md ~/.codex/skills/loop4-1/check.py ~/.codex/skills/loop4-1/body_guard.py ~/.codex/skills/loop4-1/render_check.py ~/.codex/skills/loop4-1/make_chart.py ~/.codex/skills/loop4-1/theme.reference.tex ~/.codex/skills/loop4-1/build_twice.sh ~/.codex/skills/loop4-1/apply_reference_theme.py loop41-work/\ncp ~/.codex/skills/loop4-1/data/metrics.jsonl ~/.codex/skills/loop4-1/data/app.log ~/.codex/skills/loop4-1/data/deploys.log loop41-work/data/\ncp ~/.codex/skills/loop4-1/sample/outline.tex loop41-work/outline.tex\n: > loop41-work/codex-tool-calls.jsonl\n: > loop41-work/rounds.tsv'
```

사용자에게 새 터미널을 열고 실행하게 한다.

```bash
tail -f loop41-work/codex-tool-calls.jsonl
```

반드시 설명한다.

> 이 JSONL은 Codex의 숨겨진 원본 로그가 아닙니다. 그래프의 각 노드를 실행하기 직전에
> 목적과 대상을 직접 기록합니다. 다음 단계부터 `content_gate`, `chart`, `design`, `build`,
> `render_gate` 같은 노드가 한 줄씩 올라옵니다.

tail을 켰다는 확인을 받기 전에는 STEP 1로 가지 않는다.

## STEP 1: 런타임과 시작 상태 확인

먼저 필요한 런타임을 검사한다.

```bash
~/.codex/skills/loop4-1/run_logged.sh loop41-work/codex-tool-calls.jsonl exec_command "렌더 gate 런타임 확인" "command -v xelatex pdftoppm pdfinfo && kpsewhich pgfplots.sty && kpsewhich xeCJK.sty && python3 -c 'from PIL import Image; print(Image.__version__)'"
```

하나라도 없으면 렌더 gate를 건너뛰지 말고 멈춘다. 필요한 항목을 정확히 알려준다.

내용 gate를 실행한다.

```bash
~/.codex/skills/loop4-1/run_logged.sh loop41-work/codex-tool-calls.jsonl exec_command "content_gate baseline" "python3 loop41-work/check.py loop41-work/outline.tex loop41-work/data"
```

반드시 5/5인지 확인한다. 5/5가 아니면 디자인을 시작하지 않는다.

baseline을 XeLaTeX으로 두 번 빌드하고 4쪽을 이미지로 뽑는다.

```bash
~/.codex/skills/loop4-1/run_logged.sh loop41-work/codex-tool-calls.jsonl exec_command "baseline XeLaTeX 2회 빌드" "bash loop41-work/build_twice.sh loop41-work/outline.tex"
```

```bash
~/.codex/skills/loop4-1/run_logged.sh loop41-work/codex-tool-calls.jsonl exec_command "baseline 4쪽 이미지 추출" "pdftoppm -png -r 90 -f 4 -l 4 loop41-work/outline.pdf loop41-work/before"
```

가능하면 `view_image`로 `loop41-work/before-4.png`를 보여준다. 화면비 4:3, 기본 네비게이션,
큰 여백, 차트 없음만 관찰한다. “못생겼다”는 gate 판정이 아니라 사람의 관찰이라고 구분한다.

다음 문장으로 STEP을 닫는다.

> 내용은 5/5지만 픽셀은 검사한 적이 없습니다. 루프는 자신이 보는 것만 지킵니다.

## STEP 2: 그래프와 권한 계약 읽기

`GRAPH.md`와 `design_checklist.md`를 화면에 보여준다.

```bash
~/.codex/skills/loop4-1/run_logged.sh loop41-work/codex-tool-calls.jsonl exec_command "그래프와 디자인 계약 읽기" "nl -ba loop41-work/GRAPH.md && nl -ba loop41-work/design_checklist.md"
```

네 어휘를 짚는다.

- 노드: 책임이 하나인 작업
- 엣지: 성공·실패 뒤에 갈 수 있는 다음 경로
- 상태: 파일 경로, 데이터, 현재 라운드
- 권한: 노드가 건드려도 되는 범위

디자인 노드의 권한을 정확히 설명한다.

- 허용: 프리앰블 교체, 차트 `\input`, `\vspace` 같은 배치 명령
- 금지: 원본 본문 삭제·수정, 한글 문장 추가, 생성된 차트 수정

사용자에게 묻는다.

> 내용과 디자인을 한 에이전트에게 한 번에 맡기면 어떤 숫자가 슬쩍 바뀔 수 있을까요?

답을 받은 뒤 STEP 3으로 간다.

## STEP 3: 차트 코드 노드

차트는 판단이 필요 없으므로 에이전트가 아니라 코드가 만든다.

```bash
~/.codex/skills/loop4-1/run_logged.sh loop41-work/codex-tool-calls.jsonl exec_command "chart_node 데이터 기반 그림 3종 생성" "python3 loop41-work/make_chart.py loop41-work/data loop41-work"
```

생성 직후 무결성을 확인한다.

```bash
~/.codex/skills/loop4-1/run_logged.sh loop41-work/codex-tool-calls.jsonl exec_command "chart_gate 생성물 무결성" "python3 loop41-work/make_chart.py --check loop41-work/data loop41-work"
```

`kpi.tex`, `timeline.tex`, `chart.tex` 세 파일과 실측 p95·오류율을 확인한다.
세 파일이 없거나 `--check`가 미달이면 디자인 노드로 가지 않는다.

## STEP 4: 디자인 노드와 수렴 루프

이 STEP은 최대 두 번의 에이전트 라운드와 한 번의 결정적 fallback으로 제한한다.

### 4-1. 디자인 서브에이전트 생성

spawn 전에 trace에 이벤트를 기록한다.

```bash
python3 ~/.codex/skills/loop4-1/record_tool_call.py loop41-work/codex-tool-calls.jsonl multi_agent_v1__spawn_agent "design_node r<번호>" "loop41-work/outline.tex → loop41-work/outline.styled.tex"
```

`multi_agent_v1__spawn_agent`를 `fork_context: false`로 호출한다. 에이전트 프롬프트에는 다음만 준다.

- 원본 `outline.tex` 절대경로
- `kpi.tex`, `timeline.tex`, `chart.tex` 절대경로
- 결과는 전체 `.tex` 소스만 반환하고 코드 펜스·설명은 쓰지 않는다.
- 프리앰블 전체 교체 허용
- 원본 document 본문 줄은 삭제·수정·재정렬 금지
- 새 한글 문장 추가 금지
- `\noindent\input{kpi.tex}\par`는 결론 프레임 제목 바로 뒤
- `\noindent\input{timeline.tex}\par`는 장애 개요 프레임 제목 바로 뒤
- `\noindent\input{chart.tex}\par`는 영향 범위 프레임 제목 바로 뒤
- 16:9, `xeCJK`, `CJKspace=true`, navigation symbols 제거, `pgfplots` 사용
- 차트가 요구하는 `brand`, `warn`, `mut`, `ink`, `wash`, `mark_` 색 정의

`check.py`, `body_guard.py`, `render_check.py`, `theme.reference.tex`는 에이전트에게 주지 않는다.

wait 전 `multi_agent_v1__wait_agent` 이벤트를 기록한다. 완료 응답을 저장하기 전에
`apply_patch` 이벤트를 기록하고 `outline.styled.tex`에 원문 그대로 저장한다. 완료된 에이전트는
close 이벤트를 기록한 뒤 닫는다.

### 4-2. 빌드 노드

```bash
~/.codex/skills/loop4-1/run_logged.sh loop41-work/codex-tool-calls.jsonl exec_command "build_node r<번호> XeLaTeX 2회" "bash loop41-work/build_twice.sh loop41-work/outline.styled.tex"
```

빌드 실패 시 `build.log`의 마지막 오류 20줄만 읽는다. 원본 데이터나 gate 코드를 넘기지 않고,
다음 디자인 에이전트에게 현재 styled 소스 경로와 오류 줄만 추가로 준다. 이것이 build 실패 엣지다.

### 4-3. 네 개 gate

빌드 성공 뒤 네 gate를 각각 별도 호출로 실행한다.

```bash
~/.codex/skills/loop4-1/run_logged.sh loop41-work/codex-tool-calls.jsonl exec_command "content_gate r<번호>" "python3 loop41-work/check.py loop41-work/outline.styled.tex loop41-work/data"
```

```bash
~/.codex/skills/loop4-1/run_logged.sh loop41-work/codex-tool-calls.jsonl exec_command "authority_gate r<번호>" "python3 loop41-work/body_guard.py loop41-work/outline.tex loop41-work/outline.styled.tex"
```

```bash
~/.codex/skills/loop4-1/run_logged.sh loop41-work/codex-tool-calls.jsonl exec_command "render_gate r<번호>" "python3 loop41-work/render_check.py loop41-work/outline.styled.pdf loop41-work/outline.styled.tex"
```

```bash
~/.codex/skills/loop4-1/run_logged.sh loop41-work/codex-tool-calls.jsonl exec_command "chart_gate r<번호>" "python3 loop41-work/make_chart.py --check loop41-work/data loop41-work"
```

네 개가 모두 통과하면 루프를 종료한다. 하나라도 미달이면 다음 형식으로 중계한다.

> rN: build OK · content [통과/미달] · authority [통과/미달] · render [통과/미달] · chart [통과/미달]
> 미달 원인 때문에 design 노드로 돌아갑니다.

다음 라운드에는 미달 gate의 출력만 전달한다. 성공한 gate의 내부 코드나 정답은 전달하지 않는다.

### 4-4. 두 번 실패한 경우의 안전망

에이전트 라운드 두 번 안에 전부 통과하지 못하면 다음 결정적 코드 노드를 실행한다.

```bash
~/.codex/skills/loop4-1/run_logged.sh loop41-work/codex-tool-calls.jsonl exec_command "design_node reference fallback" "python3 loop41-work/apply_reference_theme.py loop41-work/outline.tex loop41-work/theme.reference.tex loop41-work/outline.styled.tex"
```

fallback 뒤에도 build와 네 gate를 다시 실행한다. 통과하면 `fallback 통과`로 기록한다.
fallback도 미달이면 사람에게 넘기지 않고 정확한 X와 파일 경로를 보고하고 멈춘다.

라운드 결과는 `loop41-work/rounds.tsv`에 기록한다.

```bash
~/.codex/skills/loop4-1/run_logged.sh loop41-work/codex-tool-calls.jsonl exec_command "design 라운드 결과 기록" "printf 'r<번호>\\t<agent|fallback>\\t<build>\\t<content>\\t<authority>\\t<render>\\t<chart>\\n' >> loop41-work/rounds.tsv"
```

## STEP 5: 검문의 판별력 확인

baseline과 styled PDF에 같은 `render_check.py`를 실행해 실제로 판정이 갈리는지 확인한다.

```bash
~/.codex/skills/loop4-1/run_logged.sh loop41-work/codex-tool-calls.jsonl exec_command "baseline render gate 판별력" "python3 loop41-work/render_check.py loop41-work/outline.pdf loop41-work/outline.tex"
```

```bash
~/.codex/skills/loop4-1/run_logged.sh loop41-work/codex-tool-calls.jsonl exec_command "styled render gate 판별력" "python3 loop41-work/render_check.py loop41-work/outline.styled.pdf loop41-work/outline.styled.tex"
```

baseline은 화면비·그림에서 미달하고 styled는 통과해야 한다. 둘이 같은 판정을 내면 gate의
판별력이 입증되지 않은 것이므로 성공으로 끝내지 않는다.

## STEP 6: before / after와 사람 판단

styled PDF 4쪽을 이미지로 뽑는다.

```bash
~/.codex/skills/loop4-1/run_logged.sh loop41-work/codex-tool-calls.jsonl exec_command "styled 4쪽 이미지 추출" "pdftoppm -png -r 90 -f 4 -l 4 loop41-work/outline.styled.pdf loop41-work/after"
```

`before-4.png`와 `after-4.png`를 나란히 보여준다. 같은 본문과 숫자인지 `body_guard.py`와
`check.py` 결과를 다시 연결한다. 예쁜지 여부는 여기서만 사람에게 묻는다.

다음 네 줄로 마무리한다.

1. 노드는 책임·권한·검증 방법이 다를 때만 나눈다.
2. 차트는 데이터에서 결정적으로 만들고 디자인 에이전트는 차트를 수정할 수 없다.
3. 그래프 안의 디자인 루프는 네 gate가 모두 통과할 때 멈춘다.
4. gate 통과는 하한선이며 최종 취향 판단은 사람에게 남는다.

마지막 질문:

> 여러분의 업무에서 검증 방법이 서로 다른 두 단계는 무엇인가요? 거기가 노드를 나눌 자리입니다.

## Claude 버전과 다른 점

- Claude `Task` 대신 `multi_agent_v1__spawn_agent`를 `fork_context: false`로 사용한다.
- 모든 노드 실행을 명시적 JSONL에 기록해 `tail -f`로 관찰한다.
- XeLaTeX 두 번 실행을 `build_twice.sh`로 고정한다.
- 디자인 에이전트가 두 번 실패하면 결정적 `apply_reference_theme.py` 안전망을 쓴다.
- Codex 내부 transcript나 thinking summary를 사용하지 않는다.

## 번들 리소스

- `GRAPH.md`, `design_checklist.md`: 그래프와 디자인 계약
- `sample/outline.tex`, `data/`: 내용 5/5인 baseline과 원본 데이터
- `make_chart.py`: 데이터 기반 차트 3종 생성 및 무결성 gate
- `check.py`: 내용 gate
- `body_guard.py`: 디자인 권한 gate
- `render_check.py`: 화면비·가장자리·빈 페이지·그림 gate
- `build_twice.sh`: XeLaTeX 두 번 빌드
- `theme.reference.tex`, `apply_reference_theme.py`: 결정적 fallback
- `run_logged.sh`, `record_tool_call.py`: 관찰 로그 기록
