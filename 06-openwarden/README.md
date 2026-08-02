# Warden 프로필 실습

발표 2(OpenWarden: 루프를 감시하는 루프)와 짝을 이루는 실습.

슬라이드에서 본 것은 두 가지였다. **모든 작업을 5-상태로 찍는 Classify**(슬라이드 5),
그리고 **그 Warden의 실체는 마크다운 파일 한 장**(슬라이드 9)이라는 것.
여기서는 그 둘을 각각 손으로 해본다.

## 무엇을 하나

| | 하는 일 | 걸리는 시간 |
|---|---|---|
| 1 | 진짜 Warden 프로필(`Q00/OpenWarden`)을 열어 구조를 본다 | 5분 |
| 2 | 가상 시나리오 4개를 5-상태로 분류하고 답을 맞춰본다 | 15분 |
| 3 | 같은 시나리오를 AI 도구에 시켜 내 판정과 비교한다 | 10분 |
| 4 | **이 레포의 진짜 이슈**를 warden으로 분류한다 | 10분 |
| 5 | 내 레포용 프로필을 템플릿에 채운다 | 20분 |

발표 중 라이브 데모로는 1–3을 압축해 **5–7분**에 돌린다.

## 준비물

- AI 코딩 도구 아무거나 (Claude Code · Copilot · Codex — 프로필을 시스템 프롬프트에
  넣고 프롬프트를 던질 수 있으면 무엇이든 된다)
- `git`
- **GitHub 토큰이나 봇 계정은 필요 없다.** 실습은 분류 연습까지만 하고
  실제 레포에 댓글을 달지 않는다.

## 순서

### 1. 진짜 프로필을 본다

```bash
git clone https://github.com/Q00/OpenWarden
cd OpenWarden
wc -l profiles/warden.md
grep -n "^##" profiles/warden.md
```

세 곳만 본다.

- `## Classification vocabulary` — 슬라이드 5의 다섯 상태
- `## Operating rules` — 마지막 줄이 금지 목록
- `## Runbook` → `### 6. Report for human re-entry` — 출력 형식

이게 Warden의 전부다. 모델도 파인튜닝도 서버도 없다.

### 2. 분류해본다

[`scenarios.md`](scenarios.md)를 연다. 가상 정본 이슈 하나와 시나리오 네 개가 있다.

- **정답을 먼저 보지 않는다.** 먼저 찍고 나서 편다.
- 찍을 때마다 **정본의 어느 줄이 근거인지** 적는다. 지목할 줄이 없으면
  그 판정은 근거가 없는 것이다.
- 특히 `drifting`과 `misaligned`를 가르는 데 시간을 쓴다. 슬라이드 5에서
  둘만 구분하면 된다고 한 지점이다.

### 3. AI에게 같은 걸 시킨다

분류 과제 파일을 만든다 ([`scenarios.md`](scenarios.md)의 정본과 시나리오를 그대로 옮긴 것):

```bash
cat > /tmp/warden-task.txt <<'EOF'
정본(SSOT) — 이슈 #412:

#412 — Meta SSOT: 결제 리트라이 재설계 시퀀싱 (#380–#411)
현재 단계: 1단계(계측)만 진행 중.
트랙 A. 계측(#381 정본) / B. 정책(#396 정본) / C. 저장소(#404 정본)
게이트: 트랙 B 착수 조건은 트랙 A 계측 배포 후 실패율 baseline 2주치가 #412 본문에 기록되는 것.
기본 동작(default) 변경은 게이트 통과 전까지 금지.
받아들이지 않기로 한 방향: 결제 게이트웨이 교체.
시작하지 말 것: 트랙 C는 트랙 B 정책 확정 후.
#412 자체는 시퀀싱 문서다. 여기에 직접 구현 PR을 붙이지 않는다. 구현은 각 트랙의 정본 이슈로 라우팅한다.

분류할 항목 — 이슈 #421 "리트라이 관측을 신뢰할 수 있게 만들기":
트랙 A의 계측이 부족하다는 지적. 새 대시보드 스펙, 새 지표 이름 체계, 알림 임계값 표가 붙어 있다.
앞으로 리트라이 관련 작업 현황은 이 이슈에서 관리하자고 제안한다. #412는 언급만 하고 링크는 없다.

이 항목 하나를 분류하라. 출력은 세 줄로만:
1) 상태: (aligned/needs-review/drifting/misaligned/blocked 중 하나)
2) 근거: 정본에서 인용한 한 줄
3) 다음 행동: 권한 안에서 할 수 있는 것 하나
EOF
```

프로필을 **시스템 프롬프트로** 넣고 돌린다. OpenWarden 저장소 루트에서 (Claude Code 기준):

```bash
claude -p --append-system-prompt "$(cat profiles/warden.md)" \
       "$(cat /tmp/warden-task.txt)" < /dev/null
```

`< /dev/null`을 빠뜨리면 stdin 경고가 뜬다. 결과는 같다.

**두 번 돌려본다.** 리허설에서는 같은 입력에 `drifting`과 `misaligned`가
번갈아 나왔다. 판정은 흔들렸지만 다음 행동은 두 번 다 "댓글로 라우팅 제안"이었다.
이게 왜 그래도 괜찮은지가 실습의 핵심이다.

### 4. 진짜 이슈를 분류한다

연습은 가상이었다. 이제 **이 저장소의 실제 이슈**로 같은 걸 한다.

- 정본: [이슈 #1 — Labs SSOT](https://github.com/Q00/loop-engineering-labs/issues/1)
- 분류 대상: [열린 이슈들](https://github.com/Q00/loop-engineering-labs/issues) (#1 제외)

먼저 눈으로 분류한다 — 이슈마다 5-상태 하나 + **정본 #1의 어느 줄이 근거인지**.
그다음 이 레포의 warden([`agents/warden.md`](../agents/warden.md))에게 같은 걸 시켜
내 판정과 비교한다. 명령은 그 파일의 "돌리는 법"에 있다:

```bash
git clone https://github.com/Q00/loop-engineering-labs
cd loop-engineering-labs
# agents/warden.md의 "돌리는 법 (사람이 직접)" 블록을 그대로 실행
```

warden의 출력은 리뷰 노트까지다. **댓글을 달지는 사람이 결정한다** —
슬라이드 8의 핸드셰이크(인간이 결정, 에이전트가 집행)를 여기서 직접 해보는 것이다.

### 5. 내 프로필을 쓴다

[`warden-profile-template.md`](warden-profile-template.md)의 `<<...>>`를 채운다.
순서는 슬라이드 9 오른쪽 그대로다.

1. 정본으로 삼을 이슈 **하나**를 정한다 — 이걸 못 정하면 나머지는 못 쓴다
2. 허용 / 금지를 표로 적는다 — merge · force-push는 금지 쪽
3. 깨어날 시점을 정한다 — 이벤트와 주기, 둘 다
4. 감시 루프를 글로 쓴다 — 무엇을 보고, 무엇을 달지
5. **멈춤 조건**을 쓴다 — 판단이 갈리는 상황을 상황으로 적는다

## 파일

- `README.md` — 이 문서
- `warden-profile-template.md` — 빈칸 채우기 프로필 템플릿
- `scenarios.md` — 5-상태 분류 연습 (가상 시나리오 4개 + 정답·해설)

## 출처

- [Q00/OpenWarden](https://github.com/Q00/OpenWarden) — `profiles/warden.md`,
  `examples/issue-961-case-study.md`
- [Q00/ouroboros#961](https://github.com/Q00/ouroboros/issues/961) — 실제 정본 이슈.
  시나리오는 여기 기록된 패턴을 변형한 **가상 예시**다.
