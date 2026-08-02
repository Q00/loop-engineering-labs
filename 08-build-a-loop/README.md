# Talk 8 실습 — 루프를 직접 만든다

프롬프트를 스스로 고치는 미니 루프 한 바퀴. `RUN → TRACE → JUDGE → EDIT → GATE`.

**사전 준비**: `python3 --version`이 3.10 이상이면 끝. 네트워크·API 키·GPU 모두 불필요.
LLM은 EDIT 자리에만 (원한다면) 들어간다. 나머지는 결정적으로 돈다 — 같은 입력이면 늘 같은 점수.

## 이 폴더에 있는 것

| 파일 | 쓰임 |
| --- | --- |
| `tasks.json` | 과제 10개. train 6 / held-out 4 |
| `prompt.txt` | 오늘 손댈 유일한 파일. 규칙 한 줄에 하나 |
| `PROMPT.md` | STEP 1에서 AI 코딩 도구에 붙여 넣을 영어 프롬프트 전문 |
| `solution/` | 강사 참조용 레퍼런스 구현. **실습 중에는 열지 않는다** |

---

## STEP 0 · 재료 두 개

작업 폴더를 만들고 `tasks.json`과 `prompt.txt`를 복사해 온다.

```bash
mkdir -p ~/miniloop-lab
cd ~/miniloop-lab
python3 --version   # 3.10+ OK
```

과제는 지저분한 제목을 슬러그로 바꾸는 일이다. held-out 4개가 왜 따로 있는지는 STEP 4에서 몸으로 느끼게 된다. 지금은 "고칠 때 안 볼 문제"라고만 알아 두면 된다.

## STEP 1 · 하네스 만들기 (에이전트에게)

`PROMPT.md`의 프롬프트를 AI 코딩 도구에 그대로 넣어 `miniloop.py`를 받는다.
Claude Code · GitHub Copilot · Codex — 어느 도구든 된다.

나온 코드에서 가장 먼저 볼 것은 하나다: **GATE가 train이 아니라 held-out으로 판정하는가.**

## STEP 2 · 첫 바퀴, 기준 점수

```bash
python3 miniloop.py run
```

기대 출력:

```
{"split": "train", "score": 0.333, "passed": 2, "total": 6}
```

```bash
wc -l trace.jsonl        # -> 6  (run 1회 기준)
```

> 0.333이 아니면: 규칙을 파일 줄 순서로 적용한 구현 — STEP 1 프롬프트를 다시 넣어 고정 순서로 고치게 한다.
> `wc -l`이 12면: `run`을 두 번 돌린 것 (`trace.jsonl`은 append).

## STEP 3 · 실패 기록을 읽고 프롬프트 고치기

```bash
python3 miniloop.py trace
```

기대 출력 — **실패 4건** (t1 / t3 / t4 / t6):

```
t1  "  The Great Escape  "   expected great-escape        got the-great-escape
t3  "A Tale of Two Cities"   expected tale-two-cities     got a-tale-of-two-cities
t4  "RUN the LOOP"           expected run-loop            got run-the-loop
t6  "  Gate of the Day "     expected gate-day            got gate-of-the-day
```

출력 형식은 구현마다 다르다. 내용(실패 4건과 원인)만 같으면 된다.

실패 넷의 공통점: 남으면 안 되는 낱말이 `the` · `a` · `of`. 여기가 EDIT 자리다.
직접 고쳐도 되고, 위 네 줄을 그대로 에이전트에게 붙여 넣고 *"어떤 규칙 한 줄을 더하면 되는지 답하라"*고 시켜도 된다.

```bash
cp prompt.txt prompt.better.txt
echo "drop-stopwords" >> prompt.better.txt
```

## STEP 4 · 나빠지는 수정은 기각된다

```bash
python3 miniloop.py gate --candidate prompt.better.txt
```

기대 출력 — **채택, 0.25 → 1.0**:

```
{"verdict": "accept", "current": 0.25, "candidate": 1.0}
```

이번엔 일부러 나빠지는 수정을 만든다. 방금 채택된 프롬프트에서 `collapse-spaces` 한 줄을 뺀다:

```bash
grep -v collapse-spaces prompt.txt > prompt.worse.txt
python3 miniloop.py gate --candidate prompt.worse.txt
```

기대 출력 — **기각, 1.0 대 0.25**:

```
{"verdict": "reject", "current": 1.0, "candidate": 0.25}
```

> 판정이 기대와 다르면: `gate`가 train을 채점하는 구현 — 아래 검토 기준 2를 확인한다.

## STEP 5 · 결정적 최종 게이트

STEP 4에서 게이트가 채택하면서 `prompt.txt`를 이미 덮어썼다. 첫 줄에서 원본 네 줄로 되돌리고 `trace.jsonl`도 지운다. 검사 자체가 재현 가능해야 한다:

```bash
printf 'lowercase\nstrip-punct\ncollapse-spaces\nhyphenate\n' > prompt.txt
rm -f trace.jsonl && python3 miniloop.py run >/dev/null && \
python3 miniloop.py gate --candidate prompt.better.txt | grep -q '"accept"' && \
python3 miniloop.py gate --candidate prompt.worse.txt  | grep -q '"reject"' && \
echo "LAB PASSED" || echo "LAB FAILED"
```

기대 출력:

```
LAB PASSED
```

---

## 검토 기준 세 개

에이전트가 만들어 준 `miniloop.py`를 받아들이기 전에 이 셋만 확인한다.

1. **규칙 적용 순서가 파일 순서와 무관하게 고정되어 있는가.**
   `prompt.txt`의 줄 순서를 뒤집어도 `run` 점수가 `0.333`으로 같아야 한다.
2. **`gate`가 held-out만 채점하는가.** train을 쓰지 않고, `trace.jsonl`에도 쓰지 않는다.
3. **같은 입력이면 같은 점수가 나오는가.** 타임스탬프·난수·네트워크가 끼어들면 안 된다.
