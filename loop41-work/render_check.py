#!/usr/bin/env python3
"""render_check.py: 육안 노드를 코드로. **디자인 루프의 종료 조건**이다.

check.py가 글자를 보고 body_guard.py가 권한을 본다면, 이건 **렌더된 픽셀**을 본다.
"보기 좋은가"는 판정하지 못한다. 판정하는 것은 넷뿐이다.

  1. 화면비    16:9인가 (4:3이면 아직 기본 beamer다)          <- 픽셀
  2. 넘침      페이지 밖으로 삐져나간 잉크가 있는가 (가장자리 침범) <- 픽셀
  3. 빈 슬라이드 아무것도 없는 페이지가 있는가 (기본 1% 미만)      <- 픽셀
  4. 그림      필요한 장에 그림 3종이 들어갔는가                  <- 소스(.tex)

4번만 소스를 본다. pgfplots 차트는 벡터라 픽셀로는 글자와 구분되지 않기 때문이다.
이 검문은 "그림이 들어갔다"까지만 보고, 그 그림이 맞는지는 안 본다.
그림이 데이터와 일치하는지는 make_chart.py --check 가 따로 본다.

그림 3종을 요구하는 이유: 하나만 요구하면 한 바퀴에 끝나서 루프가 안 보인다.
여섯 장 전부를 요구하지 않는 이유: 설명되지 않는 장의 그림은 디자인이 아니라 장식이다.

3번의 기준이 왜 1%인지는 실측으로 정했다. 같은 보고서의 before/after를 재 보니
잉크 비율이 1.5% 대 1.8%였다. **잉크는 예쁨을 거의 구분하지 못한다.**
그래서 이 항목은 "여백이 많다"가 아니라 "페이지가 통째로 비었다"만 잡도록 낮춰 두었다.
구분해 주는 것은 1·2·4번이다. 검문을 만들 때는 그 검문에 판별력이 있는지를
이렇게 두 산출물을 재서 확인해야 한다. 그게 없으면 통과 여부가 우연이 된다.

이 넷이 전부 통과할 때까지 디자인 노드를 다시 돌린다. 그게 그래프 안의 루프다.
통과했다고 예쁜 것은 아니다. **하한선이다.** 그 위는 사람이 본다.

사용법: python3 render_check.py <파일.pdf> [소스.tex] [--min-ink 1.0]
종료 코드: 전부 통과면 0, 아니면 1.
"""
from __future__ import annotations

import glob
import os
import re
import subprocess
import sys
import tempfile

GREEN = "\033[32m"
RED = "\033[31m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

EDGE_FRAC = 0.02  # 가장자리 2%를 여백으로 본다


def pdf_size(path: str) -> tuple[float, float]:
    out = subprocess.run(["pdfinfo", path], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.startswith("Page size:"):
            parts = line.split()
            return float(parts[2]), float(parts[4])
    sys.exit("pdfinfo로 페이지 크기를 읽지 못했다")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("사용법: python3 render_check.py <파일.pdf> [소스.tex] [--min-ink 1.0]")
    min_ink = 1.0
    if "--min-ink" in sys.argv:
        i = sys.argv.index("--min-ink")
        min_ink = float(sys.argv[i + 1])
        del sys.argv[i : i + 2]
    args = sys.argv[1:]
    pdf = args[0]
    tex = args[1] if len(args) > 1 else None
    if not os.path.exists(pdf):
        sys.exit(f"파일이 없다: {pdf}")

    try:
        from PIL import Image
    except ImportError:
        sys.exit("Pillow가 필요하다: pip install pillow")

    w, h = pdf_size(pdf)
    ratio = w / h

    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-png", "-r", "50", pdf, os.path.join(tmp, "p")], check=True)
        pages = sorted(glob.glob(os.path.join(tmp, "p*.png")))
        inks: list[float] = []
        bleeds: list[int] = []
        for p in pages:
            im = Image.open(p).convert("L")
            px = im.load()
            W, H = im.size
            dark = 0
            for y in range(0, H, 2):          # 2픽셀 간격 표본. 비율만 보면 충분하다
                for x in range(0, W, 2):
                    if px[x, y] < 200:
                        dark += 1
            inks.append(100.0 * dark / ((W // 2) * (H // 2)))
            ew, eh = int(W * EDGE_FRAC), int(H * EDGE_FRAC)
            edge = 0
            for y in range(0, H, 3):
                for x in range(0, W, 3):
                    if (x < ew or x > W - ew or y < eh or y > H - eh) and px[x, y] < 200:
                        edge += 1
            bleeds.append(edge)

    # 그림 검사만 소스를 본다 (벡터 차트는 픽셀로 글자와 구분되지 않는다)
    fig_src = open(tex, encoding="utf-8").read() if tex and os.path.exists(tex) else ""
    want_figs = ["kpi", "timeline", "chart"]
    got = [f for f in want_figs if re.search(rf"\\input\{{[^}}]*{f}\.tex\}}", fig_src)]
    has_figure = len(got) == len(want_figs)
    missing = [f for f in want_figs if f not in got]
    fig_label = f"그림 3종 ({len(got)}/3 들어감" + (
        f", 빠짐: {', '.join(m + '.tex' for m in missing)})" if missing else ")")

    worst = min(inks) if inks else 0.0
    worst_page = inks.index(worst) + 1 if inks else 0
    bleed_pages = [i + 1 for i, b in enumerate(bleeds) if b > 40]

    checks = [
        (f"화면비 16:9 (지금 {ratio:.2f}:1)", abs(ratio - 16 / 9) < 0.08,
         "프리앰블에 aspectratio=169을 준다"),
        (f"가장자리 침범 없음 (의심 {len(bleed_pages)}장{': ' + str(bleed_pages) if bleed_pages else ''})",
         not bleed_pages, "그 쪽 내용이 페이지 밖으로 나갔다. 폰트 크기나 그림 높이를 줄인다"),
        (f"빈 페이지 없음 (최저 잉크 {worst:.1f}% @ {worst_page}p, 기준 {min_ink}%)", worst >= min_ink,
         f"{worst_page}쪽에 아무것도 렌더되지 않았다. 그 프레임을 확인한다"),
        (fig_label, has_figure,
         "make_chart.py로 만든 kpi.tex(결론) · timeline.tex(장애 개요) · chart.tex(영향 범위)를 각 장에 \\input 한다"),
    ]

    print(f"{BOLD}render_check.py: 렌더된 픽셀을 본다 ({len(inks)}쪽){RESET}\n")
    ok_all = True
    for label, ok, hint in checks:
        if ok:
            print(f"  {GREEN}O{RESET}  {label}")
        else:
            ok_all = False
            print(f"  {RED}X{RESET}  {label}  {DIM}힌트: {hint}{RESET}")
    print(f"\n  {DIM}쪽별 잉크: {' '.join(f'{i:.0f}%' for i in inks)}{RESET}")
    if ok_all:
        print(f"\n  {BOLD}{GREEN}통과{RESET}  {DIM}하한선을 넘었다. 예쁜지는 사람이 본다{RESET}")
        sys.exit(0)
    print(f"\n  {BOLD}{RED}미달{RESET}{BOLD}: 디자인 노드로 되돌아간다{RESET}")
    sys.exit(1)


if __name__ == "__main__":
    main()
