#!/usr/bin/env python3
"""held-out 장애 데이터 생성기 (강사 전용). 난수 없음, 언제 돌려도 같은 파일.

**이 파일은 heldout/ 폴더 안에 두지 않는다.** 실습 중 replay 에이전트가 데이터 폴더를
훑다가 이 주석을 읽으면 "이건 train과 일부러 다르게 만든 held-out"임을 알아채고,
지시서에 없는 검증을 스스로 덧붙인다(실측 확인). 그러면 게이트가 무엇을 잡았는지 흐려진다.
데이터를 다시 만들 때만 lab에서 실행한다: `cd lab/data-heldout && python3 ../skills/_shared/heldout_gen.py`

가상 시나리오 (2026-08-14, search-api):
  10:40 v4.1.0 배포 (cache_ttl 300초 -> 5초로 잘못 내림)
  10:55 캐시 미스 폭증, 백엔드 부하 상승 시작
  11:15 오류율 최고 4.2%
  11:20 p95 최고 1800ms
  11:28 v4.0.9 롤백
  11:45 완전 회복
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

START = datetime(2026, 8, 14, 9, 0)
STEPS = 73  # 09:00 ~ 15:00, 5분 간격

INCIDENT = {
    "10:55": (420, 0.9, 880),
    "11:00": (760, 1.8, 845),
    "11:05": (1180, 2.9, 810),
    "11:10": (1520, 3.7, 780),
    "11:15": (1740, 4.2, 762),
    "11:20": (1800, 4.0, 771),
    "11:25": (1610, 3.3, 795),
    "11:30": (640, 1.2, 840),
    "11:35": (300, 0.5, 872),
    "11:40": (210, 0.3, 889),
}


def baseline(i: int) -> tuple[int, float, int]:
    p95 = 120 + (i * 5) % 18       # 120~137ms
    err = 0.1 + (i % 2) * 0.1      # 0.1~0.2%
    rps = 870 + (i * 13) % 40      # 870~909
    return p95, round(err, 1), rps


def main() -> None:
    rows = []
    for i in range(STEPS):
        ts = START + timedelta(minutes=5 * i)
        p95, err, rps = INCIDENT.get(ts.strftime("%H:%M"), baseline(i))
        rows.append(
            {
                "ts": ts.strftime("2026-08-14T%H:%M:00+09:00"),
                "service": "search-api",
                "p95_ms": p95,
                "err_rate_pct": err,
                "rps": rps,
            }
        )
    with open("metrics.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"metrics.jsonl: {len(rows)} rows")


if __name__ == "__main__":
    main()
