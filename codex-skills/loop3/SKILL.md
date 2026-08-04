---
name: loop3-codex
description: "Codex 앱에서 GEPA식 지시서 자기개선 루프를 단계별로 실험한다. 의도적으로 부실한 postmortem 지시서로 v1을 실행·채점하고, 사용자 피드백만 PROMPT에 반영해 v2를 재실행하면서 같은 모델의 결과가 지시서 품질에 따라 개선되는 과정을 관찰한다. Triggers: loop3, /loop3, 루프 실습 3, GEPA, 지시서 개선, prompt improvement"
---

# 루프 실습 3: Codex에서 지시서가 학습하는 과정을 보기

이 실습은 Claude Code용 `loop3`를 Codex의 도구와 로그 방식에 맞춰 다시 만든 버전이다.
모델 가중치는 바뀌지 않는다. 사용자의 피드백으로 `PROMPT.md`만 편집하고, 같은 장애 데이터에 다시 실행한다.
관찰할 루프는 다음과 같다.

`실행 → 채점 → 명시적 tool trace 읽기 → 사용자 reflection → PROMPT 편집 → 재실행 → 재채점`

## 반드시 지킬 진행 계약

- 실습을 시작하기 전에 `loop3-work/` 사본과 `loop3-work/codex-tool-calls.jsonl`을 준비한다.
- 모든 `exec_command`는 반드시 `~/.codex/skills/loop3/run_logged.sh`를 경유한다.
- `apply_patch` 직전에는 `record_tool_call.py`로 tool·purpose·target을 먼저 기록한다.
- 모든 도구 호출 전에 정확히 세 줄로 예고한다.
  - `목적: ...`
  - `도구: exec_command 또는 apply_patch`
  - `대상: ...`
- 도구 결과를 받은 뒤 파일명·행 번호·점수·숫자 중 하나 이상을 구체적으로 짚는다.
- 한 번에 한 작업만 실행한다. 조사·작성·검증을 한 shell command에 묶지 않는다.
- STEP 하나를 끝낼 때마다 멈추고 `다음으로 갈까요?`라고 물은 뒤 사용자의 확인을 기다린다.
- 사용자가 직접 확인하지 않은 tail·도구 결과·파일 내용을 본 것처럼 말하지 않는다.
- 이 실습을 서브에이전트에 위임하지 않는다. 자식 세션의 작업은 이 실습용 JSONL에 남지 않는다.
- Codex 내부 transcript를 읽는다고 말하지 않는다. JSONL은 실습이 별도로 기록하는 관찰용 로그다.

설치 후에는 `~/.codex/skills/loop3/`를 사용한다. 저장소에서 직접 실습할 때는 같은 경로의 `codex-skills/loop3/`로 바꾼다.

## STEP 0: 재료와 관찰 장치 소개

먼저 아래 문장으로 오늘의 목표를 소개한다.

> 오늘은 모델을 바꾸지 않고 지시서만 바꿔서 결과가 좋아지는지 확인합니다. 처음 결과가 일부러 밋밋해야 다음 라운드의 개선이 눈에 보입니다.

실습 자료를 설명한다.

- `loop3-work/data/`: 2강과 같은 `pay-api` 장애 데이터다.
- `loop3-work/PROMPT.md`: postmortem 지시서 v1이다. 한 단락을 쓰라는 최소 지시만 있다.
- `loop3-work/checklist.md`: 5점 채점표다. STEP 1이 끝날 때까지 열지 않는다.
- `loop3-work/codex-tool-calls.jsonl`: Codex의 숨겨진 내부 로그가 아니라, 우리가 목적과 대상을 직접 기록하는 실습용 trace다.

작업 사본을 준비한다. 작업 사본의 부모 디렉터리가 아직 없으므로 첫 호출은 bootstrap 로그에 기록한다.

Bootstrap guard: 이 명령은 실습을 실행할 작업 디렉터리를 `workdir`로 지정한 상태에서 그대로 실행한다. 첫 번째 로그 경로는 `loop3-bootstrap.jsonl`처럼 `loop3-work/` 바깥에 둔다. `loop3-work/codex-tool-calls.jsonl`은 아래 명령이 `mkdir`와 초기화를 끝낸 뒤에만 사용한다. 임시 디렉터리를 쓸 때 아직 확장되지 않은 변수나 존재하지 않는 `loop3-work` 경로를 첫 로그 인자로 넣지 않는다.

```bash
~/.codex/skills/loop3/run_logged.sh loop3-bootstrap.jsonl exec_command "실습 사본 준비" $'mkdir -p loop3-work/data\ncp ~/.codex/skills/loop3/PROMPT.md ~/.codex/skills/loop3/checklist.md loop3-work/\ncp ~/.codex/skills/loop3/data/metrics.jsonl ~/.codex/skills/loop3/data/app.log ~/.codex/skills/loop3/data/deploys.log loop3-work/data/\n: > loop3-work/codex-tool-calls.jsonl'
```

수강생에게 다른 터미널을 열고 다음 명령을 실행하게 한다.

```bash
tail -f loop3-work/codex-tool-calls.jsonl
```

반드시 설명한다.

> 이 파일은 Codex의 숨겨진 transcript가 아닙니다. 우리가 실행할 작업의 목적과 대상을 별도 JSONL에 기록합니다. 다음 단계의 명령이 실행되면 옆 터미널에 한 줄이 나타나고, 그 줄과 Codex 도구 결과를 함께 비교합니다.

tail이 실행됐다는 사용자의 확인을 받은 뒤 STEP 1로 간다.

## STEP 1: 지시서 v1 실행

먼저 실행 구간을 자른다.

```bash
~/.codex/skills/loop3/run_logged.sh loop3-work/codex-tool-calls.jsonl exec_command "v1 구간 마커 생성" "touch loop3-work/mark-v1.txt"
```

그 다음 `PROMPT.md`만 읽고 화면에 보여준다. 이때 `checklist.md`는 열지 않는다. 수강생에게 다음 요청을 그대로 입력하게 한다.

> `loop3-work/PROMPT.md`의 지시만 따라 `loop3-work/data`의 장애 기록을 보고 결과를 `loop3-work/out_v1.md`에 작성해줘. `checklist.md`는 열지 말고, 지시서에 없는 형식·수치·인용·재발 방지 액션을 추가하지 마.

Codex가 v1을 수행할 때 지켜야 할 범위:

- `PROMPT.md`의 한 단락 지시만 따른다.
- 채점표의 요구사항을 미리 반영하지 않는다.
- `out_v1.md`만 만든다. v1 단계에서 `PROMPT.md`를 고치지 않는다.
- 파일을 만들기 전 아래 기록 명령을 실행하고, 그 뒤 `apply_patch`를 호출한다.

```bash
~/.codex/skills/loop3/run_logged.sh loop3-work/codex-tool-calls.jsonl exec_command "v1 결과 작성 기록" "python3 ~/.codex/skills/loop3/record_tool_call.py loop3-work/codex-tool-calls.jsonl apply_patch 'v1 결과 작성' 'loop3-work/out_v1.md'"
```

초안을 만든 뒤 `out_v1.md`를 한 번 읽어 보여준다. 결과를 미리 좋게 고치지 않는다. 보통 v1은 0~2/5 정도이며, 빠진 내용이 있어야 다음 단계의 필요성이 생긴다.

실제 결과를 받은 뒤 다음을 짚는다.

> 방금 trace에는 목적과 대상이 기록됐고, Codex 도구 블록에는 실제 명령과 결과가 있습니다. 지금 결과가 부족한 것은 모델이 고장 나서가 아니라 지시서가 요구하지 않았기 때문일 수 있습니다.

STEP 1을 마치고 멈춘다.

## STEP 2: v1 채점

이제 처음으로 채점표를 연다. 두 호출을 분리한다.

```bash
~/.codex/skills/loop3/run_logged.sh loop3-work/codex-tool-calls.jsonl exec_command "채점표 읽기" "nl -ba loop3-work/checklist.md"
```

```bash
~/.codex/skills/loop3/run_logged.sh loop3-work/codex-tool-calls.jsonl exec_command "v1 초안 읽기" "nl -ba loop3-work/out_v1.md"
```

5개 항목을 한 번에 점수 내리지 말고 하나씩 읽는다. 각 항목마다 `out_v1.md`의 어느 문장이 O 또는 X인지 수강생에게 묻고, 합의된 점수를 대화창에 `v1 = N/5`로 기록한다.

예상 질문에는 이렇게 답한다.

> 맞습니다. 모델이 알아서 잘 쓸 수도 있습니다. 그래서 v1에서는 지시서에 적힌 만큼만 하도록 범위를 고정했습니다. 결과 품질이 모델보다 지시서 품질에 좌우되는 상황을 실험으로 만든 것입니다.

채점표와 초안을 모두 확인한 뒤 멈춘다.

## STEP 2.5: 점수보다 실행 과정을 읽기

점수는 무엇이 빠졌는지만 알려준다. trace는 왜 빠졌는지 알려준다. v1 마커 이후의 대상 파일을 확인한다.

```bash
~/.codex/skills/loop3/run_logged.sh loop3-work/codex-tool-calls.jsonl exec_command "v1 과정 trace 읽기" "python3 ~/.codex/skills/loop3/trace_read.py --log loop3-work/codex-tool-calls.jsonl --since loop3-work/mark-v1.txt --touched"
```

그 다음 배포 이력을 실제로 다뤘는지 판정한다.

```bash
~/.codex/skills/loop3/run_logged.sh loop3-work/codex-tool-calls.jsonl exec_command "배포 이력 과정 검증" "python3 ~/.codex/skills/loop3/trace_read.py --log loop3-work/codex-tool-calls.jsonl --since loop3-work/mark-v1.txt --read-check deploys.log"
```

출력에서 `metrics.jsonl`, `app.log`, `deploys.log`의 존재 여부를 수강생과 대조한다. 없는 파일은 “안 읽었을 가능성이 있다”가 아니라, 이 실습의 계측 규칙상 해당 파일을 대상으로 한 기록이 없다는 뜻이라고 설명한다.

읽지 않은 파일이 있으면 다음처럼 연결한다.

> 점수는 “2번 항목 X”라고만 말하지만, trace는 “배포 이력을 대상으로 한 호출이 없었다”고 말합니다. GEPA가 점수만이 아니라 실행 기록을 읽는 이유가 여기 있습니다.

세 파일을 모두 읽었는데도 점수가 낮으면 다음처럼 말한다.

> 재료는 모두 읽었습니다. 그렇다면 이번에는 지시서가 읽은 내용을 쓰라고 충분히 말하지 않은 것이 원인입니다.

`trace_read.py`가 tool call 0개를 출력하면 실패로 단정하지 않는다. 먼저 로그 경로, 마커 경로, 마커보다 뒤에 호출했는지를 확인하고 `--log`와 `--since`를 명시해 다시 실행한다.

STEP 2.5를 마치고 멈춘다.

## STEP 3: 사용자 reflection을 PROMPT에 반영

수강생에게 한 번에 한 질문만 한다.

> v1에서 가장 아쉬웠던 점은 무엇인가요? 언제 시작·복구했는지, 원인이 무엇인지, 로그 근거가 어디인지처럼 말로 알려주세요.

수강생의 답과 STEP 2.5의 trace를 함께 근거로 삼는다. checklist를 보고 답을 대신 고르지 않는다. 사용자가 말한 불만을 자연어 지시문으로 번역한다.

먼저 버전을 백업한다.

```bash
~/.codex/skills/loop3/run_logged.sh loop3-work/codex-tool-calls.jsonl exec_command "PROMPT v1 백업" "cp loop3-work/PROMPT.md loop3-work/PROMPT.v1.bak"
```

그 다음 `apply_patch`로 `loop3-work/PROMPT.md`만 수정한다. 수정 직전에 반드시 기록한다.

```bash
~/.codex/skills/loop3/run_logged.sh loop3-work/codex-tool-calls.jsonl exec_command "PROMPT 편집 기록" "python3 ~/.codex/skills/loop3/record_tool_call.py loop3-work/codex-tool-calls.jsonl apply_patch '사용자 reflection 반영' 'loop3-work/PROMPT.md'"
```

편집 규칙:

- 사용자가 말한 피드백만 지시문으로 번역한다.
- checklist를 몰래 복사하지 않는다.
- 공통 규칙인 “지시서가 곧 상한이다”를 지우지 않는다.
- 2~3라운드의 개선 여지가 남도록 한 번에 모든 요구사항을 넣지 않는다.
- 백업 파일은 `PROMPT.v1.bak`, 다음 라운드는 `PROMPT.v2.bak`처럼 보존한다.

STEP 3을 마치고 멈춘다.

## STEP 4: 지시서 diff 관찰

```bash
~/.codex/skills/loop3/run_logged.sh loop3-work/codex-tool-calls.jsonl exec_command "PROMPT diff 읽기" "diff -u loop3-work/PROMPT.v1.bak loop3-work/PROMPT.md"
```

diff에서 새로 추가된 문장을 수강생과 한 줄씩 읽는다. 다음 두 문장으로 의미를 정리한다.

> 방금 이 diff가 이 시스템의 학습입니다. 모델 가중치는 1비트도 바뀌지 않았습니다.

> 사람이 말로 준 feedback을 지시문으로 번역한 것이 reflection이고, 다음 실행에서 그 지시문이 결과를 바꾸는지 확인합니다.

STEP 4를 마치고 멈춘다.

## STEP 5: v2 재실행과 재채점

수정된 `PROMPT.md`만 사용해 같은 데이터를 다시 실행한다. 수강생에게 다음 요청을 입력하게 한다.

> 수정된 `loop3-work/PROMPT.md`의 지시만 따라 같은 `loop3-work/data`를 다시 분석하고, 결과를 `loop3-work/out_v2.md`에 작성해줘.

v2 파일을 만들기 전에도 `record_tool_call.py`로 `apply_patch`를 기록한다. v2가 끝나면 `out_v2.md`를 읽고, STEP 2와 같은 방법으로 checklist를 대조한다. 합의된 점수를 `v2 = N/5`로 기록한다.

두 점수를 받은 뒤 시각화한다.

```bash
~/.codex/skills/loop3/run_logged.sh loop3-work/codex-tool-calls.jsonl exec_command "점수 변화 시각화" "python3 ~/.codex/skills/loop3/loop_view.py <v1점수> <v2점수>"
```

예를 들어 `v1 = 1`, `v2 = 4`라면 `python3 .../loop_view.py 1 4`로 실행한다. 출력의 `lift`와 “오른 것은 모델이 아니라 PROMPT.md”라는 문장을 함께 확인한다.

v2가 5/5가 아니면 실패로 끝내지 않는다. `PROMPT.v2.bak`을 만들고 STEP 3으로 돌아가 한 라운드만 더 진행한다. 시간이 부족하면 현재 점수와 다음 개선 후보를 말하고 수강생의 확인을 받은 뒤 멈춘다.

## STEP 6: 마무리

다음 세 줄로 정리한다.

1. 오늘의 루프는 실행 → 채점 → trace 읽기 → reflection → PROMPT 편집 → 재실행 → 재채점이다.
2. 사람의 채점은 프로덕션에서 자동 평가가 되고, 사람의 reflection은 나중에 에이전트가 맡을 수 있다.
3. 편집 대상이 prompt·skill·memory 같은 문서라면 diff·리뷰·롤백으로 관리할 수 있다.

마지막으로 질문한다.

> 여러분의 업무에서 `PROMPT.md` 역할을 하는 문서는 무엇인가요?

## Claude 버전과 다른 점

- `~/.claude/projects/*.jsonl`을 읽지 않는다. `loop3-work/codex-tool-calls.jsonl`에 명시적으로 기록한다.
- `Bash`, `Read`, `Grep`, `Write`를 전제하지 않는다. Codex에서는 `exec_command`와 `apply_patch`를 사용한다.
- `~/.claude/skills/loop3` 대신 설치된 `~/.codex/skills/loop3`의 번들 파일을 사용한다.
- `showThinkingSummaries`나 원본 사고 내용을 사용하지 않는다.
- 작업 폴더 변경에 의존하지 않고 `loop3-work/...` 경로를 명시한다.
- trace를 읽는 명령 자체도 tool call이므로 “우리 발자국도 함께 찍힌다”고 설명한다.

## 번들 리소스

- `PROMPT.md`: 실험용 v1 지시서
- `checklist.md`: 5점 채점표
- `data/`: 공통 pay-api 장애 데이터
- `run_logged.sh`: 목적·대상 기록 후 shell 명령 실행
- `record_tool_call.py`: `apply_patch` 직전 기록
- `trace_read.py`: 명시적 Codex 실습 로그의 최근 호출·대상 파일·read-check 판정
- `loop_view.py`: v1/v2 점수와 lift 표시
