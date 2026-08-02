# solution/ — 강사 참조용

**수강생용이 아닙니다.** 실습의 절반은 `PROMPT.md`를 에이전트에 넣어 `miniloop.py`를 직접 받아 보는 데 있습니다. 이 폴더를 먼저 열면 STEP 1이 사라집니다.

`miniloop.py`는 `PROMPT.md` 스펙을 그대로 구현한 레퍼런스입니다. 쓰임은 둘입니다.

- 수강생이 만든 하네스가 이상한 숫자를 낼 때 **정답 숫자**를 대조한다
- 실습장에서 STEP 1이 막힌 사람에게 마지막 수단으로 건넨다

## 검증된 출력

`tasks.json` · `prompt.txt`를 같은 폴더에 두고 실행한 결과입니다. 덱(Talk 8)의 수치와 전부 일치합니다.

```
$ python3 miniloop.py run
{"split": "train", "score": 0.333, "passed": 2, "total": 6}

$ wc -l trace.jsonl
       6 trace.jsonl

$ python3 miniloop.py trace
t1  "  The Great Escape  "      expected great-escape          got the-great-escape
t3  "A Tale of Two Cities"      expected tale-two-cities       got a-tale-of-two-cities
t4  "RUN the LOOP"              expected run-loop              got run-the-loop
t6  "  Gate of the Day "        expected gate-day              got gate-of-the-day

$ cp prompt.txt prompt.better.txt && echo "drop-stopwords" >> prompt.better.txt
$ python3 miniloop.py gate --candidate prompt.better.txt
{"verdict": "accept", "current": 0.25, "candidate": 1.0}

$ grep -v collapse-spaces prompt.txt > prompt.worse.txt
$ python3 miniloop.py gate --candidate prompt.worse.txt
{"verdict": "reject", "current": 1.0, "candidate": 0.25}

$ (STEP 5 원라이너)
LAB PASSED
```

## 구현 메모 — 수강생 코드를 볼 때 짚을 곳

- **규칙 순서**는 `RULE_ORDER` 리스트가 고정한다. `prompt.txt`의 줄 순서는 "어떤 규칙을 켤지"만 정한다. 줄 순서를 뒤집어도 `run`은 `0.333`.
- **`drop-stopwords`는 `collapse-spaces`보다 먼저** 온다. 이 순서가 `0.25 → 1.0`을 만든다. 반대로 두면 불용어를 지운 자리의 공백이 그대로 하이픈이 되어 held-out이 무너진다 — STEP 4의 `prompt.worse.txt`가 정확히 그 상황(`--loop---loops-`)이다.
- **`gate`는 heldout만** 읽고 `trace.jsonl`에 한 줄도 쓰지 않는다.
- **`run_id`는 `r1`, `r2`...** 로 증가한다. 타임스탬프를 쓰지 않아 `trace.jsonl`이 재현 가능하다.
- **모르는 규칙 이름은 exit 2.** 빈 줄은 무시한다(파일 끝 개행 때문).
