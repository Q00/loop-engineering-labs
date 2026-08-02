# 실습 스킬 (`/loop2`부터 `/loop5`까지)

본편 2-5강의 실습은 **Claude Code 스킬**로 돌아간다. 수강생이 만드는 코드는 없다.
스킬을 설치하면 Claude Code가 진행자가 되어, 관찰할 것을 순서대로 보여 준다.

## 설치

```bash
bash skills/install.sh
```

`~/.claude/skills/`의 `loop2`부터 `loop5`까지 복사된다. **같은 이름의 기존 스킬은 덮어쓴다.**
Claude Code를 다시 열고 `/loop2`처럼 실행한다.

## 다섯 개의 실습

| 스킬 | 주제 | 무엇을 눈으로 보는가 |
|---|---|---|
| `/loop2` | 툴콜 로깅 | 방금 한 작업의 tool call이 세션 로그에 실시간으로 쌓이는 것 |
| `/loop3` | GEPA식 지시서 진화 | 부실한 지시서를 피드백으로 고쳐 재실행하면 점수가 오르는 것 |
| `/loop4` | SkillOpt-Sleep | 어제 한 일에서 스킬을 캐내(harvest·mine) held-out 게이트를 통과한 것만 채택. 산출물은 beamer 소스다 |
| `/loop4-1` | graph engineering | 채점 5/5인데 못생긴 보고서에 차트를 붙이고 디자인을 입히는 동안, 디자인 노드가 본문을 못 건드리게 코드가 막는 것. 렌더 검문이 미달을 내면 그래프 안에서 루프가 한 바퀴 더 돈다 |
| `/loop5` | VPRM식 검문 루프 | 보고서를 코드 검문기가 PASS시킬 때까지 수렴, 환각이 검문에 걸리는 것 |

소재는 한 줄기다. 가짜 장애(pay-api, 2026-07-12) 하나를 다섯 실습이 이어서 다룬다.

## 재료

- `_shared/trace_read.py` — 세션 로그(`~/.claude/projects/*/*.jsonl`) 판독기. 2강이 관찰한 그 기록을 3·4·5강이 근거로 읽는다.
- `_shared/sleep_harvest.py` — 4강의 harvest·mine.
- `data-heldout/` — 4강 게이트용, 한 번도 안 본 장애(search-api).
- 각 스킬 폴더의 `data/` — 공통 장애 데이터.
- `loop4-1/sample/outline.tex` — 4강이 만든 발표 슬라이드 소스. 4.1강의 시작 재료라 4강을 안 돌려도 된다.
- `loop4-1/make_chart.py` — 차트 노드. 데이터에서 그림 3종(kpi · timeline · chart)을 뽑는다. `--check`로 생성물이 손으로 고쳐졌는지 본다.
- `loop4-1/render_check.py` — 렌더된 픽셀을 보는 검문. 디자인 루프의 종료 조건이다.
- `loop4-1/body_guard.py` · `design_checklist.md` — 권한 경계와 디자인 채점표.

## 준비물

- Python 3.10+ (stdlib만 사용, 설치 없음)
- `xelatex` + `pgfplots` (4.1강만. `which xelatex`로 확인한다. 없으면 4.1강 STEP 2에서 멈춘다)
- Pillow (4.1강의 `render_check.py`가 쓴다: `pip install pillow`)
- `pdftoppm` · `pdfinfo` (poppler. 4.1강에서 렌더를 픽셀로 검사한다)
- Claude Code (세션 로그를 재료로 쓰므로 이 실습들은 Claude Code 전용이다)

### 5강만의 추가 준비

5강 규정 7은 **사고 요약**을 재료로 쓴다. 기본으로 꺼져 있어서 켜야 한다.

```jsonc
// ~/.claude/settings.json
{ "showThinkingSummaries": true }
```

**켠 뒤에 연 세션부터** 적용된다. 켜지 않아도 규정 7은 위반이 아니라 건너뛰기로
처리되니 실습 자체는 굴러간다.

## 알아 둘 것

- **서브에이전트에 위임하면 안 된다.** 자식 세션의 tool call은 부모 세션 로그에 안 남아서,
  기록을 읽는 STEP들이 "(없음)"만 보고한다. 창을 여러 개 띄우는 것은 괜찮고,
  그때는 창마다 작업 폴더를 다르게 쓴다.
- **읽기 명령은 읽기 명령으로 시작해야 기록에 남는다.** `grep ...`은 잡히고,
  함수나 스크립트 안에서 읽으면 판독기가 못 본다.
