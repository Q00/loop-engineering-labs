#!/usr/bin/env python3
"""make_chart.py: 차트 노드. 데이터에서 그림 3종을 뽑는다.

**코드 노드다.** 판단이 없다. 같은 데이터면 같은 그림이 나온다.
그래서 이 노드에는 "예쁘게 해 달라"고 부탁할 대상이 없고, 검증할 것도 파일이 나왔는지뿐이다.
값을 지어내지 않는다. 축 범위도, 눈금도, 표시할 시각도 전부 데이터에서 계산한다.

  kpi.tex        결론 슬라이드용. 실측 수치 3종을 카드 세 장으로.
  timeline.tex   장애 개요용. app.log의 사건을 가로 축에.
  chart.tex      영향 범위용. p95와 오류율의 시간 변화.

그림이 필요한 장에만 만든다. 여섯 장 전부에 그림을 넣는 것은 디자인이 아니라 장식이다.

사용법:
    python3 make_chart.py [데이터폴더] [출력폴더]         # 3종 생성 (기본: data, .)
    python3 make_chart.py --check [데이터폴더] [출력폴더]  # 생성물이 손으로 고쳐졌는지 검사
"""
from __future__ import annotations

import json
import os
import re
import sys

GREEN = "\033[32m"
RED = "\033[31m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

# 타임라인에 올릴 사건. (로그에서 찾을 조건, 화면에 쓸 이름)
EVENTS = [
    (lambda s: "rollout complete" in s, "배포"),
    (lambda s: "error" in s, "첫 오류"),
    (lambda s: "paged" in s, "페이징"),
    (lambda s: "rollback" in s and "complete" in s, "복구"),
    (lambda s: "drain" in s or "requeue" in s, "재처리"),
]


def hhmm_to_min(hhmm_s: str) -> int:
    h, m = hhmm_s.split(":")
    return int(h) * 60 + int(m)


def hhmm(t: int) -> str:
    return f"{t // 60:02d}:{t % 60:02d}"


def read_metrics(data_dir: str) -> list[tuple[int, int, float]]:
    mpath = os.path.join(data_dir, "metrics.jsonl")
    if not os.path.exists(mpath):
        sys.exit(f"데이터 폴더에 metrics.jsonl이 없다: {data_dir}")
    rows = [json.loads(l) for l in open(mpath, encoding="utf-8")]
    return [(hhmm_to_min(r["ts"][11:16]), r["p95_ms"], r["err_rate_pct"]) for r in rows]


def read_events(data_dir: str) -> list[tuple[int, str]]:
    """app.log에서 사건 시각을 찾는다. 못 찾은 사건은 그냥 뺀다."""
    path = os.path.join(data_dir, "app.log")
    if not os.path.exists(path):
        return []
    lines = []
    for line in open(path, encoding="utf-8"):
        m = re.search(r"T(\d{2}:\d{2})", line)
        if m:
            lines.append((m.group(1), line.lower()))
    out: list[tuple[int, str]] = []
    for cond, name in EVENTS:
        for t, low in lines:
            if cond(low):
                out.append((hhmm_to_min(t), name))
                break
    return sorted(set(out))


def build_kpi(pts, evs) -> str:
    p95 = max(p for _, p, _ in pts)
    err = max(e for _, _, e in pts)
    rec = next((hhmm(t) for t, n in evs if n == "복구"), "-")
    cards = [("p95 최고", f"{p95}", "ms"), ("오류율 최고", f"{err}", r"\%"), ("복구", rec, "")]
    body = ""
    for i, (label, value, unit) in enumerate(cards):
        x = i * 3.9
        body += f"""
  \\node[kpicard] (c{i}) at ({x},0) {{}};
  \\node[font=\\scriptsize, text=mut, anchor=north west] at ([xshift=7pt,yshift=-7pt]c{i}.north west) {{{label}}};
  \\node[font=\\Huge\\bfseries, text=brand, anchor=west] at ([xshift=7pt,yshift=-5pt]c{i}.west) {{{value}\\,{{\\normalsize {unit}}}}};"""
    return f"""% kpi.tex: make_chart.py가 데이터에서 생성했다. 손으로 고치지 않는다.
\\begin{{tikzpicture}}[kpicard/.style={{rectangle, rounded corners=4pt, draw=brand!22, fill=brand!8,
    minimum width=3.5cm, minimum height=1.6cm, anchor=west}}]{body}
\\end{{tikzpicture}}
"""


def build_timeline(evs) -> str:
    if not evs:
        return "% timeline.tex: app.log에서 사건을 찾지 못했다\n"
    t0, t1 = evs[0][0], evs[-1][0]
    span = max(t1 - t0, 1)
    body = ""
    for t, name in evs:
        x = 11.0 * (t - t0) / span
        body += f"""
  \\fill[brand] ({x:.2f},0) circle (2.6pt);
  \\node[font=\\scriptsize\\bfseries, text=ink, anchor=south] at ({x:.2f},0.20) {{{name}}};
  \\node[font=\\tiny, text=mut, anchor=north] at ({x:.2f},-0.20) {{{hhmm(t)}}};"""
    return f"""% timeline.tex: make_chart.py가 app.log에서 생성했다. 손으로 고치지 않는다.
\\begin{{tikzpicture}}
  \\draw[wash, line width=2.6pt] (0,0) -- (11.0,0);{body}
\\end{{tikzpicture}}
"""


def build_chart(pts, evs) -> str:
    p95_max = max(p for _, p, _ in pts)
    err_max = max(e for _, _, e in pts)
    t0, t1 = pts[0][0], pts[-1][0]
    ticks = list(range(t0 - t0 % 60 + (60 if t0 % 60 else 0), t1 + 1, 60))
    tick_labels = ",".join(hhmm(t) for t in ticks)
    p95_coords = " ".join(f"({t},{p})" for t, p, _ in pts)
    err_coords = " ".join(f"({t},{e})" for t, _, e in pts)

    vlines = ""
    for at, name in [(t, n) for t, n in evs if n in ("배포", "복구")]:
        vlines += (
            f"\n    \\draw[mark_, dashed] (axis cs:{at},0) -- (axis cs:{at},{p95_max});"
            f"\n    \\node[mark_, font=\\tiny, anchor=south west, rotate=90]"
            f" at (axis cs:{at},{int(p95_max * 0.10)}) {{{name} {hhmm(at)}}};"
        )

    return f"""% chart.tex: make_chart.py가 metrics.jsonl에서 생성했다. 손으로 고치지 않는다.
% 실측 최댓값: p95 {p95_max}ms, 오류율 {err_max}%
\\begin{{tikzpicture}}
\\begin{{axis}}[
  width=\\linewidth, height=2.75cm, scale only axis,
  xmin={t0}, xmax={t1}, ymin=0, ymax={int(p95_max * 1.12)},
  xtick={{{",".join(str(t) for t in ticks)}}}, xticklabels={{{tick_labels}}},
  ytick={{0,{p95_max // 2},{p95_max}}},
  axis y line*=left, axis x line*=bottom,
  ylabel={{p95 (ms)}}, y label style={{font=\\scriptsize, at={{(0.02,1.02)}}, anchor=south west, rotate=-90}},
  tick label style={{font=\\tiny}},
  every axis plot/.append style={{line width=1.1pt}},
]
\\addplot[brand, mark=none] coordinates {{{p95_coords}}};{vlines}
\\end{{axis}}
\\begin{{axis}}[
  width=\\linewidth, height=2.75cm, scale only axis,
  xmin={t0}, xmax={t1}, ymin=0, ymax={err_max * 1.12:.2f},
  axis y line*=right, axis x line=none, xtick=\\empty,
  ytick={{0,{err_max / 2:.1f},{err_max}}},
  ylabel={{오류율 (\\%)}}, y label style={{font=\\scriptsize, at={{(0.98,1.02)}}, anchor=south east, rotate=-90}},
  tick label style={{font=\\tiny}},
]
\\addplot[warn, dashed, mark=none, line width=1pt] coordinates {{{err_coords}}};
\\end{{axis}}
\\end{{tikzpicture}}
"""


def main() -> None:
    argv = sys.argv[1:]
    check = "--check" in argv
    if check:
        argv.remove("--check")
    data_dir = argv[0] if argv else "data"
    out_dir = argv[1] if len(argv) > 1 else "."

    pts = read_metrics(data_dir)
    evs = read_events(data_dir)
    want = {
        "kpi.tex": build_kpi(pts, evs),
        "timeline.tex": build_timeline(evs),
        "chart.tex": build_chart(pts, evs),
    }

    if check:
        # 생성물을 손으로 고쳤는지 본다. 코드 노드의 산출물은 데이터에서만 나와야 한다.
        print(f"{BOLD}make_chart.py --check: 생성물이 데이터와 일치하는가{RESET}\n")
        bad = 0
        for name, text in want.items():
            path = os.path.join(out_dir, name)
            if not os.path.exists(path):
                print(f"  {RED}X{RESET}  {name} 없음  {DIM}힌트: make_chart.py를 먼저 돌린다{RESET}")
                bad += 1
            elif open(path, encoding="utf-8").read() != text:
                print(f"  {RED}X{RESET}  {name} 손으로 고쳐졌다  {DIM}힌트: 다시 생성한다{RESET}")
                bad += 1
            else:
                print(f"  {GREEN}O{RESET}  {name}")
        print(f"\n  {BOLD}{RED if bad else GREEN}{'미달' if bad else '통과'}{RESET}")
        sys.exit(1 if bad else 0)

    for name, text in want.items():
        open(os.path.join(out_dir, name), "w", encoding="utf-8").write(text)
    p95 = max(p for _, p, _ in pts)
    err = max(e for _, _, e in pts)
    print("차트 노드: kpi.tex · timeline.tex · chart.tex 생성")
    print(f"  데이터 {len(pts)}점, 사건 {len(evs)}개 ({' '.join(n for _, n in evs)})")
    print(f"  실측: p95 최고 {p95}ms · 오류율 최고 {err}%")
    print("색 이름 brand · warn · mut · ink · wash · mark_ 는 프리앰블에서 정의한다. 디자인 노드의 몫이다.")


if __name__ == "__main__":
    main()
