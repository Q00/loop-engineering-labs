# Loop Engineering Labs

"모두를 위한 루프 엔지니어링" (AIFrenz 빌드캠프) 시리즈의 실습 자료 모음.

발표 자료의 실습(STEP) 슬라이드와 짝을 이루며, 폴더 번호는 발표 순서를 따른다.

| 폴더 | 발표 | 내용 |
|---|---|---|
| [`01-selfimprove-gate/`](01-selfimprove-gate/) | Talk 1 · 자기개선은 전부 루프다 | SkillOpt-Sleep 라이브 데모 — GATE가 유해한 편집을 거부하는 걸 결정적으로 재현 (API 키 불필요) |
| [`02-openwarden/`](02-openwarden/) | Talk 2 · OpenWarden | Warden 프로필 템플릿 채우기 + 5-상태 분류 연습 시나리오 |
| [`04-build-a-loop/`](04-build-a-loop/) | Talk 4 · 실습: 루프를 직접 만든다 | RUN→TRACE→JUDGE→EDIT→GATE 미니 루프 — 과제 파일 · 생성 프롬프트 · 기대 출력 · 레퍼런스 구현 |
| [`05-ouroboros/`](05-ouroboros/) | Talk 5 · 실습: Ouroboros 한 바퀴 | `ooo interview → seed → run → qa` 치트시트 + 실습용 goal 예시 |

## 준비물

- Python 3.10+ (04는 stdlib만 사용, 설치 없음)
- AI 코딩 도구 아무거나 (Claude Code · Copilot · Codex — 04 STEP 1과 02 데모에서 사용)
- Talk 5는 [Ouroboros](https://github.com/Q00/ouroboros) 설치 필요 (`ooo --version`으로 확인)

## 이 저장소의 Warden

Talk 2에서 배운 걸 이 저장소 자신에게 적용했다. [`agents/warden.md`](agents/warden.md)가
실습 자료가 발표 확정본에서 어긋나지 않는지 감시하는 프로필이다 — 돌리는 법도 그 안에 있다.

## 관련 저장소

- [Q00/ouroboros](https://github.com/Q00/ouroboros) — Agent OS: stop prompting, start specifying
- [Q00/OpenWarden](https://github.com/Q00/OpenWarden) — 정렬을 지키는 Warden 프로필
- [microsoft/SkillOpt](https://github.com/microsoft/SkillOpt) — Talk 1 데모가 사용하는 자기개선 루프

---
© 2026 Jaegyu Lee · jqyu.lee@gmail.com
