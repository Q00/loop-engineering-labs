# Talk 9 실습 — Ouroboros 한 바퀴

한 줄짜리 아이디어에서 실행까지, 명령 다섯 개.
`interview → seed → run → status/tui → qa`. Talk 7의 다섯 단계와 일대일로 대응한다.

각자 **자기 업무 아이디어 한 줄**로 한 바퀴 돈다. 고를 게 없으면 `interview-goal-examples.md`에서 하나 가져다 쓴다.

---

## 시작 전 확인 두 줄

```bash
ooo --version          # -> Ouroboros version 0.50.4
ooo status health
```

기대 출력:

```
Configuration:   ok - ~/.ouroboros/config.yaml
Database:        ok - data/ouroboros.db
Runtime backend: ok - codex: ~/.zeude/bin/codex
Credentials:     ok - OPENAI_API_KEY present for codex
```

네 줄이 전부 `ok`가 아니면 설정 마법사를 먼저 돌린다. 백엔드 선택과 자격 증명을 대화형으로 잡아 준다.

```bash
ooo setup
```

`Runtime backend`가 실행을 맡을 에이전트 CLI다. Claude Code · Codex · Gemini · Copilot 중 무엇이 잡혀 있는지 여기서 확인하고 시작한다.

---

## STEP 1 · 모호함을 깎는 인터뷰

```bash
ooo interview start -o "커밋 로그로 주간 배포 노트 초안을 만드는 CLI"
ooo interview list        # 세션 ID 확인 (다음 단계 입력값)
```

따옴표 안은 각자 자기 업무 아이디어로 바꾼다. 한 줄이면 충분하다.
질문에 답할수록 ambiguity 점수가 내려간다. Talk 7의 입구 게이트 `Ambiguity ≤ 0.2`가 바로 이 종료 조건.

> `ModuleNotFoundError: No module named 'litellm'`이 나오면 기본 백엔드가 litellm인 것.
> `-o` 또는 `--llm-backend claude_code`로 우회한다.

## STEP 2 · 대화를 spec으로 굳히기

```bash
ooo seed interview_20260726_014233
```

나온 `seed.yaml`에서 볼 것 다섯 가지.

- `goal` — 무엇을 만드는지 한 문장
- `constraints` — 지킬 선. `Non-goal:`로 시작하는 줄이 out-of-scope
- `acceptance_criteria` — 완료를 무엇으로 판정하는지. `semantic_ac_key`는 세대가 바뀌어도 같은 AC를 추적하는 키
- `exit_conditions` — `acceptance_verified`면 AC가 전부 검증될 때 멈춘다
- `metadata.ambiguity_score` — 이 spec이 얼마나 덜 모호한지

Talk 8에서 손으로 고친 `prompt.txt` 자리에 오는 것이 이 `seed.yaml`이다. 다른 점은 완료 판정 기준이 파일 안에 같이 들어 있다는 것.

## STEP 3 · spec을 실행에 넘기기

```bash
ooo run seed.yaml --dry-run          # 먼저 유효성만 확인
ooo run seed.yaml --max-decomposition-depth 1
```

실습장에서는 `--max-decomposition-depth 1`을 권장한다. 시간이 깊이에 비례한다.

## STEP 4 · 도는 동안 지켜보기

```bash
ooo tui monitor                 # 대화형 화면
ooo status executions           # 최근 실행 목록 + 상태
ooo status run <RUN_ID>         # 실행 하나를 Run/Stage/Step 트리로
```

관찰 목표: 실행이 어느 단계에서 시간을 쓰는지, 실패가 어디서 나는지 본다.
Talk 8의 `trace.jsonl`이 여기서는 `status`와 `tui`가 읽어 주는 이벤트 기록이다.

## STEP 5 · 산출물에 합격선 걸기

```bash
ooo qa ./release-notes.md \
  --quality-bar "주간 배포 노트로 바로 보낼 수 있는가: 항목마다 PR 링크와 영향 범위가 있고, 내부 용어에 설명이 붙어 있다" \
  --artifact-type document \
  --pass-threshold 0.8
```

`--quality-bar`는 실습의 핵심이다. ✗ "잘 썼는가" / ○ "항목마다 PR 링크가 있는가".
`ooo qa`는 실행과 무관하게 아무 산출물에나 따로 돌릴 수 있다.

## 보너스 · 한 명령으로 가는 길

```bash
ooo auto "커밋 로그로 주간 배포 노트 초안을 만드는 CLI"
```

인터뷰 · seed · 실행을 한 번에 진행한다.
**되돌리기 싼 일**에만 쓴다. 되돌리는 비용이 큰 일, 판정에 사람 눈이 필요한 일, spec 자체가 팀의 합의사항인 일은 단계별로 간다.

## 막혔을 때의 최소 경로

`ooo run`이 네트워크·플랜 문제로 막히면 `--dry-run`까지만 확인하고 STEP 5로 건너뛴다.
`ooo qa`는 실행과 무관하게 아무 파일에나 돌릴 수 있다 — 지금 갖고 있는 문서 하나로 `--quality-bar` 연습이 된다.

---

# `ooo` 치트시트

## interview

```bash
ooo interview start -o "<한 줄 goal>"
ooo interview start --llm-backend codex "<한 줄 goal>"
ooo interview start --runtime codex "<한 줄 goal>"
ooo interview list
```

| 옵션 | 내용 |
| --- | --- |
| `-o`, `--orchestrator` | Claude Code Max Plan으로 진행. API 키가 없어도 된다 |
| `--llm-backend codex` | 인터뷰 · 모호함 점수 · seed 생성에 쓸 백엔드 지정 |
| `--runtime codex` | seed 이후 *실행*을 맡을 런타임을 미리 지정 |

## seed

```bash
ooo seed <INTERVIEW_ID>        # 예: ooo seed interview_20260726_014233
```

## run

```bash
ooo run seed.yaml              # = ooo run workflow seed.yaml
```

| 옵션 | 내용 |
| --- | --- |
| `--dry-run` | 실행하지 않고 seed가 유효한지만 확인 |
| `--runtime codex` | 실행 런타임 교체 (claude · codex · opencode · gemini · copilot · hermes ⋯) |
| `--max-decomposition-depth 1` | 과제를 잘게 쪼개는 깊이 제한. `0`이면 쪼개지 않음. 실습장에선 **1 권장** |
| `--resume orch_abc123` | 중단된 실행을 이어서. 단계마다 ID 접두사가 다르다: `interview_…` / `orch_…` |
| `--mcp-config mcp.yaml` | 외부 MCP 서버의 도구를 붙여서 실행 |

## 지켜보기 — status · tui · job

```bash
ooo tui monitor                 # 대화형 화면
ooo tui open                    # 새 터미널로
ooo status health               # 설정 · DB · 런타임 · 자격 증명 점검
ooo status executions           # 최근 실행 목록 + 상태
ooo status run <RUN_ID>         # Run/Stage/Step 트리 (--json 도 가능)
ooo job status <JOB_ID>         # 백그라운드 job 확인
ooo job wait   <JOB_ID>         # 끝날 때까지 대기
ooo job result <JOB_ID>         # 결과 받기
```

`status run`은 실행 ID를 반드시 받는다. `executions` 목록에서 골라 넣는다.

## qa

```bash
ooo qa <산출물 경로> -q "<합격 기준 한 문장>" -t document --pass-threshold 0.8
```

| 옵션 | 내용 |
| --- | --- |
| `-q`, `--quality-bar` | PASS가 무엇인지 자연어로 |
| `-t`, `--artifact-type` | `code`(기본) · `document` · `test_output` · `api_response` · `screenshot` · `custom` |
| `--pass-threshold` | 통과 점수. 기본 `0.8`. 내부 초안 `0.6` · 외부 배포물 `0.9` |
| `-r`, `--reference` | 기존 산출물을 주면 톤 일치까지 본다 |

## auto

```bash
ooo auto "<한 줄 goal>"
ooo auto "<한 줄 goal>" --runtime codex
ooo auto --resume <id>
```

## 막힐 때 꺼내는 명령

| 구획 | 명령 | 하는 일 |
| --- | --- | --- |
| 복구 | `ooo resume` | MCP 연결이 끊긴 뒤 세션에 다시 붙기 |
| | `ooo cancel` | 멈춰 버린 실행, 주인 없는 실행 취소 |
| | `ooo cleanup` | 남아 있는 worktree · 브랜치 · 락 정리 |
| 실행 비교 | `ooo harness list` · `show` · `trace` | 실행 목록 · 한 실행의 요약 · 기록에서 문자열 찾기 |
| | `ooo harness diff` · `frontier` | 두 실행을 나란히 비교 · 지표로 줄 세우기 |
| 그 외 | `ooo detect [PATH]` | 이 프로젝트의 lint · build · test 명령을 찾아 `.ouroboros/mechanical.toml`에 적어 둔다 (AI 호출 1회) |
| | `ooo pm` | 가이드 인터뷰로 PRD 작성 |
| | `ooo setup` | 설정 마법사 |
