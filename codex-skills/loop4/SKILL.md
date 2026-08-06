---
name: loop4-codex
description: "Codex 앱에서 SkillOpt-Sleep식 자기개선 루프를 관찰한다. 명시적 Codex 실습 trace에서 반복 과업을 harvest·mine하고, 채점표를 모르는 서브에이전트가 train과 held-out 데이터로 replay한 결과를 결정적 gate로 검증한 뒤 사람 확인으로만 adopt한다. Triggers: loop4, /loop4, 루프 실습 4, SkillOpt, sleep loop, harvest, held-out gate"
---

# 루프 실습 4: 어제의 기록에서 내일 쓸 스킬 후보 캐기

이 스킬은 Claude Code용 `loop4`를 Codex 앱에 맞게 옮긴 실습이다.
관찰할 구조는 다음과 같다.

`harvest → mine → replay → held-out gate → human adopt`

Codex의 숨겨진 내부 transcript를 읽는다고 말하지 않는다. `loop2`와 `loop3`가 명시적으로
기록한 `codex-tool-calls.jsonl`만 harvest한다. 이 차이는 매번 친절하고 정확하게 설명한다.

## 진행 계약

- STEP마다 멈추고 사용자 확인을 받는다. 단 STEP 3의 replay와 gate는 한 라운드가 끝날 때까지 연속 실행한다.
- 사용자가 이해할 수 있도록 모든 도구 호출 전에 다음 다섯 가지를 설명한다.
  - 지금 할 일
  - 왜 필요한지
  - 사용할 도구
  - `tail -f` 화면에 나타날 목적과 대상
  - 호출 결과에서 함께 확인할 숫자·파일·판정
- 모든 `exec_command`는 `~/.codex/skills/loop4/run_logged.sh`를 경유한다.
- `apply_patch`와 서브에이전트 호출 직전에는 `record_tool_call.py`로 목적과 대상을 기록한다.
- `loop4-work/codex-tool-calls.jsonl`은 Codex 내부 로그가 아니라 이 실습의 계측 로그라고 설명한다.
- 채점은 반드시 `python3 loop4-work/check.py <산출물> <데이터폴더>` 출력만 근거로 한다.
- train/held-out replay는 `multi_agent_v1__spawn_agent`를 `fork_context: false`로 호출한다.
- replay 에이전트에게 `check.py`, `checklist.md`, 점수, 정답, 이전 실패 이유를 절대 전달하지 않는다.
- replay 에이전트는 `.tex`만 반환하게 하고, 메인 에이전트가 작업 사본에 저장한다.
- replay 도구가 제공되지 않으면 메인 에이전트가 대신했다고 속이지 말고, 지원되지 않는다고 설명하고 멈춘다.
- 라이브 스킬 파일은 자동으로 수정하지 않는다. 채택은 사용자 동의 후 작업 사본에만 수행한다.
- 라운드는 최대 3회로 제한한다. held-out 5/5, 교착, 또는 3회 도달 시 멈춘다.

## 친절한 설명 형식

도구 호출 전에는 다음 형식을 자연스러운 한국어로 채워 말한다.

> 지금 할 일은 **[작업]**입니다. 이 작업이 필요한 이유는 **[이유]**입니다.
> 사용할 도구는 **[도구]**이고, 대상은 **[경로 또는 과업]**입니다.
> 옆 터미널에는 `purpose=[목적]`인 JSON 한 줄이 나타나야 합니다.
> 실행 후에는 **[숫자·점수·파일]**을 함께 확인하겠습니다.

결과를 받은 뒤에는 다음 관계를 반복해서 짚는다.

> `tail`은 무엇을 시도했는지를 보여주고, Codex 도구 블록은 실제 입력과 결과를 보여줍니다.
> 둘을 함께 봐야 에이전트의 말이 아니라 실행을 검증할 수 있습니다.

## STEP 0: 실습 사본과 관찰 장치 준비

오늘 볼 네 단계를 먼저 소개한다.

1. `harvest`: 지난 명시적 trace를 모은다.
2. `mine`: 반복된 작업을 스킬 후보로 찾는다.
3. `replay + gate`: 같은 과업을 다시 실행하고 처음 보는 데이터로 검증한다.
4. `adopt`: 사람이 diff를 본 뒤 채택한다.

첫 bootstrap은 아직 `loop4-work/`가 없으므로 별도 로그에 남긴다.

```bash
~/.codex/skills/loop4/run_logged.sh loop4-bootstrap.jsonl exec_command "loop4 실습 사본 준비" $'mkdir -p loop4-work/data loop4-work/heldout\ncp ~/.codex/skills/loop4/PROMPT.md ~/.codex/skills/loop4/checklist.md ~/.codex/skills/loop4/check.py ~/.codex/skills/loop4/sleep_harvest.py loop4-work/\ncp ~/.codex/skills/loop4/data/metrics.jsonl ~/.codex/skills/loop4/data/app.log ~/.codex/skills/loop4/data/deploys.log loop4-work/data/\ncp ~/.codex/skills/loop4/heldout/metrics.jsonl ~/.codex/skills/loop4/heldout/app.log ~/.codex/skills/loop4/heldout/deploys.log loop4-work/heldout/\ncp loop4-work/PROMPT.md loop4-work/PROMPT.v1.bak\n: > loop4-work/codex-tool-calls.jsonl\n: > loop4-work/rounds.tsv'
```

사용자에게 새 터미널을 열고 다음 명령을 실행하게 한다.

```bash
tail -f loop4-work/codex-tool-calls.jsonl
```

반드시 다음처럼 설명한다.

> 지금 보는 파일은 Codex의 원본 transcript가 아닙니다. 이 실습에서 실행할 작업의 목적과
> 대상을 우리가 직접 JSONL로 기록합니다. 다음 호출부터 한 줄씩 올라오며, Codex 화면의
> 실제 도구 결과와 나란히 비교할 수 있습니다.

사용자가 tail을 켰다고 확인할 때까지 STEP 1로 가지 않는다.

## STEP 1: 재료와 train/held-out 구분

작업 사본의 네 재료를 한 줄씩 설명한다.

- `PROMPT.md`: 발표 슬라이드 지시서 v1. 처음에는 한 문장뿐이다.
- `check.py`와 `checklist.md`: 코드로 된 5점 채점표다.
- `data/`: 이미 본 pay-api 장애, 즉 train 데이터다.
- `heldout/`: replay 에이전트가 train 개선 전에는 보지 않는 search-api 장애다.

`heldout/`의 내용과 채점표는 이 단계에서 화면에 열지 않는다. 이름과 역할만 설명한다.

핵심 문장:

> train 점수만 보면 값을 외운 지시서와 방법을 배운 지시서를 구분할 수 없습니다.
> 한 번도 보지 않은 held-out 데이터에서 같은 규칙을 통과해야 일반화됐다고 말할 수 있습니다.

STEP 1을 마치고 `다음으로 갈까요?`라고 묻는다.

## STEP 2: harvest와 mine

최근 168시간의 명시적 실습 trace를 모은다. 현재 loop4 로그는 harvest 대상에서 제외한다.

```bash
~/.codex/skills/loop4/run_logged.sh loop4-work/codex-tool-calls.jsonl exec_command "지난 Codex 실습 trace harvest와 반복 과업 mining" "python3 loop4-work/sleep_harvest.py --root . --lookback-hours 168 --exclude loop4-work/codex-tool-calls.jsonl --top 5"
```

출력에서 다음을 천천히 읽는다.

- trace 파일 수와 tool call 수
- 반복된 작업 목적
- 반복해서 편집한 산출물
- 위임/replay와 검증 횟수

다음처럼 정직하게 설명한다.

> 이 목록은 Codex의 모든 대화를 수집한 것이 아닙니다. loop 실습이 명시적으로 기록한 작업만
> 포함합니다. 관찰되지 않은 작업을 없었다고 단정할 수는 없지만, 여기 기록된 반복은 실제
> 실행 증거가 있습니다.

사용자에게 묻는다.

> 이 중 내일도 다시 할 가능성이 큰 일은 무엇인가요?

실습의 고정 replay 대상은 `데이터에서 경영진용 장애 발표 슬라이드를 만드는 일`이다.
harvest 상위에 정확히 같은 문구가 없다면 “교육용으로 준비된 후보를 사용한다”고 밝힌다.
기록에서 나왔다고 꾸미지 않는다.

사용자가 후보를 확인하면 STEP 3으로 간다.

## STEP 3: replay와 held-out gate

이 STEP은 한 라운드의 `train replay → 채점 → PROMPT 편집 → held-out replay → gate`를
중간 확인 없이 이어서 보여준다. 단, 각 도구 호출 전후 설명은 생략하지 않는다.

### 3-1. 현재 최고본 백업

```bash
~/.codex/skills/loop4/run_logged.sh loop4-work/codex-tool-calls.jsonl exec_command "현재 최고 PROMPT 백업" "cp loop4-work/PROMPT.md loop4-work/PROMPT.best.bak"
```

### 3-2. train replay를 서브에이전트에 위임

먼저 `PROMPT.md`만 읽는다. `check.py`와 `checklist.md`는 replay 프롬프트에 포함하지 않는다.
데이터 폴더의 절대경로는 `pwd`로 계산해 명시한다.

spawn 직전에 다음과 같은 이벤트를 기록한다.

```bash
python3 ~/.codex/skills/loop4/record_tool_call.py loop4-work/codex-tool-calls.jsonl multi_agent_v1__spawn_agent "train replay r<번호>" "<data 절대경로>"
```

그 다음 `multi_agent_v1__spawn_agent`를 `fork_context: false`로 호출한다. 프롬프트에는 오직
다음 정보만 넣는다.

- `PROMPT.md` 전문
- train 데이터 폴더 절대경로
- “지시서에 쓰인 표기를 그대로 쓴다.”
- “지시서에 없는 검증·주석·대안 제시를 덧붙이지 않는다.”
- “데이터 파일을 직접 읽되 최종 응답은 `.tex` 소스만 출력한다.”

에이전트가 끝날 때까지 기다리기 전에도 `multi_agent_v1__wait_agent` 이벤트를 기록한다.
응답을 `loop4-work/outline_r<번호>.tex`에 저장하기 직전에는 `apply_patch` 이벤트를 기록한다.
완료된 에이전트를 닫기 전에는 `multi_agent_v1__close_agent` 이벤트를 기록한다. 이렇게 하면
옆 터미널에서 `spawn → wait → apply_patch → close` 순서를 그대로 볼 수 있다.

### 3-3. train 채점과 PROMPT 편집

```bash
~/.codex/skills/loop4/run_logged.sh loop4-work/codex-tool-calls.jsonl exec_command "train r<번호> 결정적 채점" "python3 loop4-work/check.py loop4-work/outline_r<번호>.tex loop4-work/data"
```

`check.py`가 5점 미만이면 종료 코드 1이 정상이다. 도구 실패로 오해하지 말고 X 항목과 힌트를
모두 읽는다. 힌트를 일반 지시문으로 `PROMPT.md`에 누적 반영하되 held-out 값은 보지 않는다.
편집 직전에 `apply_patch` 이벤트를 기록한다.

### 3-4. held-out replay와 gate

수정된 `PROMPT.md`와 held-out 폴더 절대경로만 새 서브에이전트에게 준다. train 에이전트를
재사용하지 않는다. spawn 이벤트의 목적은 `held-out replay r<번호>`로 기록한다.

응답을 `loop4-work/outline_h<번호>.tex`에 저장한 뒤 채점한다.

```bash
~/.codex/skills/loop4/run_logged.sh loop4-work/codex-tool-calls.jsonl exec_command "held-out r<번호> gate 채점" "python3 loop4-work/check.py loop4-work/outline_h<번호>.tex loop4-work/heldout"
```

현재 최고 held-out 점수보다 높으면 수정된 `PROMPT.md`를 새 최고본으로 수용한다. 같거나 낮으면
다음 명령으로 복원한다.

```bash
~/.codex/skills/loop4/run_logged.sh loop4-work/codex-tool-calls.jsonl exec_command "gate 기각으로 PROMPT 복원" "cp loop4-work/PROMPT.best.bak loop4-work/PROMPT.md"
```

라운드 결과는 다음 형식으로 기록하고 화면에 표로 보여준다.

```bash
~/.codex/skills/loop4/run_logged.sh loop4-work/codex-tool-calls.jsonl exec_command "r<번호> gate 결과 기록" "printf 'r<번호>\\t<train점수>\\t<heldout점수>\\t<수용|기각>\\n' >> loop4-work/rounds.tsv"
```

train은 편집 전 PROMPT, held-out은 힌트 반영 후 PROMPT 점수라 같은 버전의 두 성적이 아니라고
반드시 설명한다.

### 3-5. 교착을 설명하고 일반화

train 5/5인데 held-out 규칙 3이 실패하면 `PROMPT.md`에 `2500ms` 같은 train 값이 박혔는지 본다.
그렇다면 다음처럼 설명한다.

> train 값을 외운 지시서는 train에서 5점이지만 처음 보는 장애에서는 틀립니다. 게이트가
> 암기와 일반화를 갈라낸 장면입니다. 채점기는 무엇이 틀렸는지는 알려줬지만 값을 지우고
> 계산 방법을 쓰라는 해법까지 만들지는 못했습니다.

이때만 진행자가 값 대신 방법을 쓰는 일반화 편집을 한다.

> `metrics.jsonl`에서 `p95_ms` 최댓값과 `err_rate_pct` 최댓값을 계산하고, `app.log`에서
> rollback complete 시각을 찾아 요구된 형식으로 쓴다.

held-out의 실제 숫자를 PROMPT에 복사하지 않는다. 다음 라운드를 다시 실행한다.

held-out 5/5가 되면 성공으로 종료한다. 3라운드 안에 통과하지 않으면 현재 최고점과 남은 X를
보여주고 종료한다. 무한 반복하지 않는다.

STEP 3 마지막에는 라운드 표와 다음 세 문장을 보여준다.

1. replay는 채점 규칙을 모르는 별도 에이전트가 수행했다.
2. gate는 처음 보는 데이터로 암기와 일반화를 구분했다.
3. 자동 루프가 멈춘 자리에서 사람은 값이 아니라 방법을 넣었다.

## STEP 4: diff 확인과 human adopt

최초 지시서와 최고 지시서를 비교한다.

```bash
~/.codex/skills/loop4/run_logged.sh loop4-work/codex-tool-calls.jsonl exec_command "최초와 최고 PROMPT diff 확인" "diff -u loop4-work/PROMPT.v1.bak loop4-work/PROMPT.md"
```

diff를 한 줄씩 설명한 뒤 반드시 사용자에게 묻는다.

> 이 지시서를 작업 사본에 채택할까요?

동의 전에는 아무것도 채택하지 않는다. 동의하면 다음 명령으로 작업 사본에만 복사한다.

```bash
~/.codex/skills/loop4/run_logged.sh loop4-work/codex-tool-calls.jsonl exec_command "사용자 승인 후 작업 사본 채택" "cp loop4-work/PROMPT.md loop4-work/ADOPTED_SKILL.md"
```

라이브 `~/.codex/skills/loop4/PROMPT.md`는 수정하지 않는다. `--auto-adopt`가 게이트를 끄는
것이 아니라 사람 확인만 생략한다는 점을 설명한다. 자동 채택 판단 기준은 다음 세 가지다.

- 되돌리기가 싼가
- 영향 범위가 좁은가
- held-out이 실제 사용 범위를 대표하는가

## STEP 5: 마무리

다음 네 줄로 정리한다.

1. harvest·mine의 재료는 기억이 아니라 명시적으로 남은 실행 기록이다.
2. replay는 채점표를 모르는 별도 에이전트가 수행해야 점수가 정직하다.
3. held-out gate가 없으면 암기한 지시서를 학습한 지시서로 착각할 수 있다.
4. adopt는 별도 단계이며, 게이트가 못 보는 것을 감당할 수 있을 때만 자동화한다.

마지막으로 묻는다.

> 여러분의 반복 업무 중, 처음 보는 사례로 자동 검증할 수 있는 것은 무엇인가요?

## Claude 버전과 다른 점

- `~/.claude/projects/*.jsonl` 대신 loop 실습이 기록한 명시적 Codex JSONL만 읽는다.
- Claude `Task` 대신 Codex `multi_agent_v1__spawn_agent`를 사용한다.
- `Bash`, `Read`, `Write` 대신 `exec_command`, `apply_patch`, subagent 도구를 기록한다.
- 원본 사고나 thinking summary를 사용하지 않는다.
- Codex 내부 로그를 관찰한다고 과장하지 않는다. 계측 범위 밖 행동은 harvest에 나타나지 않는다.

## 번들 리소스

- `PROMPT.md`: 한 문장짜리 v1 지시서
- `checklist.md`, `check.py`: train과 held-out에 동일하게 쓰는 결정적 채점기
- `data/`: pay-api train 데이터
- `heldout/`: search-api held-out 데이터
- `sleep_harvest.py`: 명시적 Codex 실습 trace harvest·mine
- `run_logged.sh`, `record_tool_call.py`: `tail -f`용 작업 이벤트 기록
