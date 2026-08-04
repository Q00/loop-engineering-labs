# pay-api 장애 Postmortem 초안

## 영향

- `p95_ms` 최고값은 **2500ms**로 2026-07-12 14:45에 관측됐다 (`metrics.jsonl`, 14:45 레코드).
- `err_rate_pct` 최고값은 **9.8%**로 14:40에 관측됐다 (`metrics.jsonl`, 14:40 레코드). 두 최고값의 시각은 다르다.
- 애플리케이션 로그에는 DB connection pool 고갈과 checkout timeout이 반복 기록됐다 (`app.log`: 7, 8, 9, 11, 12, 15행).

## 타임라인

- 14:05: `pay-api v2.3.1`이 `db_pool_size=10`으로 직접 배포됐다 (`app.log`: 3행; `deploys.log`: 2행).
- 14:21~14:44: `db connection pool exhausted` 및 checkout timeout 오류가 반복됐다 (`app.log`: 7~15행).
- 14:47: 온콜이 v2.3.0 롤백을 승인했다 (`app.log`: 16행).
- 14:52: v2.3.0 롤백이 완료되어 `db_pool_size=50`이 복원됐다 (`app.log`: 17행; `deploys.log`: 3행).

## 원인

v2.3.1 배포에서 `db_pool_size`가 기존 50에서 10으로 변경됐다. 직접 롤아웃된 이 설정 변경으로 DB connection pool이 고갈됐고, checkout timeout과 오류율·지연시간 상승으로 이어진 것으로 판단된다.

## 근거

- 지표: `loop2-work/metrics.jsonl`
- 애플리케이션 오류·배포·롤백: `loop2-work/app.log`
- 배포 이력: `loop2-work/deploys.log`
