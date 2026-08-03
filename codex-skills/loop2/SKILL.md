---
name: loop2-codex
description: "Codex 앱에서 툴콜이 무엇을 하고 왜 실행되는지 관찰하는 루프 실습. 가짜 장애 데이터로 postmortem 초안을 만들며 각 exec_command와 apply_patch의 목적·입력·결과를 단계별로 설명한다. Triggers: loop2, 루프 실습 2, 툴콜, tool call 관찰"
---

# 루프 실습 2: Codex의 tool call을 읽는 법

이 실습의 목적은 에이전트가 "분석했다"고 말하는 것과 실제로 실행한 작업을 구분하는 것이다.
Codex 앱에는 Claude의 `~/.claude/projects/*.jsonl`과 같은 로그를 이 스킬이 읽을 수 없으므로,
작업 직전에 남기는 **실습용 계측 JSONL**을 사용한다. 이것을 Codex 내부 로그라고 부르지 않는다.

## 진행 규칙

- 각 도구 호출 전에 반드시 세 줄로 예고한다.
  - 목적: 이번 호출이 왜 필요한가
  - 도구: `exec_command` 또는 `apply_patch`
  - 대상: 어떤 파일·명령·출력을 다루는가
- 호출 결과를 받은 뒤에는 결과에서 확인할 구체적인 파일명, 행 번호, 숫자를 한 줄로 짚는다.
- 한 단계가 끝나면 멈추고 사용자에게 다음 단계로 갈지 묻는다.
- 실제로 호출하지 않은 도구나 읽지 않은 파일을 사용했다고 말하지 않는다.
- 작업 사본은 현재 저장소 안에 만든다.
- `exec_command` 작업은 반드시 `run_logged.sh`로 실행한다.
- `apply_patch`는 호출 직전에 `record_tool_call.py`로 기록한다.
- 사용자가 각 단계의 의미를 이해할 수 있도록, 도구 호출 전에 목적·도구·대상·예상 로그를 설명한다.

## STEP 0: 재료 소개

`skills/loop2/data/`의 세 파일을 소개한다.

- `metrics.jsonl`: pay-api의 5분 간격 지표
- `app.log`: 장애 시각의 애플리케이션 로그
- `deploys.log`: 배포 이력

오늘은 이 데이터를 읽고 `loop2-work/draft.md`에 postmortem 초안을 만든다.

## STEP 1: 관찰용 tail 켜기

먼저 작업 사본과 계측 파일을 만든다.

```bash
mkdir -p loop2-work
cp skills/loop2/data/metrics.jsonl skills/loop2/data/app.log skills/loop2/data/deploys.log loop2-work/
: > loop2-work/codex-tool-calls.jsonl
```

수강생에게 터미널을 하나 더 열고 다음 명령을 실행하게 한다.

```bash
tail -f loop2-work/codex-tool-calls.jsonl
```

반드시 다음처럼 설명한다.

> 지금 보는 파일은 Codex의 숨겨진 내부 로그가 아닙니다. Codex에서는 이 실습이 Claude의
> transcript 파일에 접근할 수 없기 때문에, 우리가 실행하는 작업의 목적과 대상을 별도
> JSONL 파일에 기록하도록 계측한 것입니다. 다음 단계에서 명령을 실행하면 옆 터미널에
> JSON 한 줄이 나타납니다. 그 한 줄이 “무슨 작업을 시작했는가”를 보여줍니다.

tail을 켰다는 사용자의 확인을 받은 뒤에만 다음 단계로 진행한다.

## STEP 2: 툴콜을 한 번씩 관찰하며 분석

다음 순서로 호출을 분리한다. 한 호출 안에서 여러 작업을 묶지 않는다.

각 `exec_command` 전에 다음 형식으로 설명한다.

> 지금 할 일은 [목적]입니다. [도구]를 사용해 [대상]을 읽거나 실행합니다.
> 옆 터미널에는 `tool`, `purpose`, `target`이 들어간 JSON 한 줄이 나타나야 합니다.
> 그 뒤 아래 결과에서 [확인할 숫자·행·파일]을 함께 확인하겠습니다.

실행 형식은 다음과 같다.

```bash
~/.codex/skills/loop2-codex/run_logged.sh loop2-work/codex-tool-calls.jsonl exec_command "지표 계산" "<실행할 셸 명령>"
```

순서는 다음과 같다.

1. `metrics.jsonl`의 `p95_ms`와 `err_rate_pct` 최고값·시각을 계산한다.
2. `app.log`에서 ERROR·deploy·rollback 행을 행 번호와 함께 찾는다.
3. `deploys.log`를 읽는다.
4. 먼저 아래 기록 명령을 실행한 뒤 `apply_patch`로 `loop2-work/draft.md`를 작성한다.
   ```bash
   python3 ~/.codex/skills/loop2-codex/record_tool_call.py loop2-work/codex-tool-calls.jsonl apply_patch "postmortem 초안 작성" "loop2-work/draft.md"
   ```
5. 작성된 초안을 다시 읽어 검증한다.

각 호출이 끝나면 옆 터미널의 새 JSON 줄을 가리키며 이렇게 설명한다.

> 방금 추가된 줄은 실제 분석 명령의 목적과 대상을 기록한 것입니다. 아래 Codex 도구
> 블록에서는 같은 호출의 실제 명령과 결과를 확인할 수 있습니다. 로그는 “무엇을 하려
> 했는가”를, 도구 결과는 “실제로 무엇이 나왔는가”를 보여줍니다.

초안에는 타임라인, 원인, 영향, 근거 파일과 행을 포함한다. 알려진 기준값은 다음과 같다.

- 원인: v2.3.1 배포에서 `db_pool_size`가 50에서 10으로 변경됨
- p95 최고: 2500ms, 14:45
- 오류율 최고: 9.8%, 14:40
- 두 최고값의 시각은 다름

완료 후 실제로 사용한 도구와 순서를 다음 형식으로 복기한다.

`exec_command(지표 계산) → exec_command(로그 검색) → exec_command(배포 이력 읽기) → apply_patch(초안 작성) → exec_command(초안 검증)`

## STEP 3: 툴콜 읽는 법 정리

다음 매핑을 화면에서 확인한다.

| 도구 | 의미 | 관찰할 것 |
|---|---|---|
| `exec_command` | 터미널 명령 실행 | 명령어, 대상 경로, stdout/stderr, 종료 코드 |
| `apply_patch` | 파일 변경 | 어떤 파일의 어느 부분을 만들거나 수정했는지 |

강조할 문장: 도구 이름만 보는 것보다 **입력과 결과를 함께 봐야** 에이전트의 실제 작업을 검증할 수 있다.
`tail`에는 작업의 목적과 대상이 남고, Codex 대화창에는 실제 도구 호출과 결과가 남는다.

## 데이터 경로

이 저장소에서 직접 실행할 때는 `skills/loop2/data/`를 사용한다. 계측 래퍼는
`~/.codex/skills/loop2-codex/run_logged.sh`, 기록기는
`~/.codex/skills/loop2-codex/record_tool_call.py`에 설치된다.
