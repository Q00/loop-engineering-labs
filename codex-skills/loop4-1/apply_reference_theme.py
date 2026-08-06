#!/usr/bin/env python3
"""Deterministic fallback: replace the preamble and insert three chart commands."""
from __future__ import annotations

import re
import sys
from pathlib import Path


FIGURES = {
    "결론": "kpi.tex",
    "장애 개요": "timeline.tex",
    "영향 범위": "chart.tex",
}


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit("usage: apply_reference_theme.py SOURCE.tex THEME.tex OUTPUT.tex")
    source_path, theme_path, output_path = map(Path, sys.argv[1:])
    source = source_path.read_text(encoding="utf-8")
    theme = theme_path.read_text(encoding="utf-8").rstrip()
    marker = r"\begin{document}"
    if marker not in source:
        raise SystemExit(f"document 환경이 없다: {source_path}")
    body = marker + source.split(marker, 1)[1]

    for title, figure in FIGURES.items():
        pattern = rf"(\\frametitle\{{{re.escape(title)}\}}\s*\n)"
        insertion = rf"\noindent\input{{{figure}}}\par" + "\n"
        body, count = re.subn(
            pattern,
            lambda match: match.group(1) + insertion,
            body,
            count=1,
        )
        if count != 1:
            raise SystemExit(f"프레임 제목을 찾지 못했다: {title}")

    output_path.write_text(theme + "\n\n" + body, encoding="utf-8")
    print(f"reference fallback 생성: {output_path}")
    print("  프리앰블 교체 · 본문 원문 유지 · kpi/timeline/chart 명령 3줄 추가")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
