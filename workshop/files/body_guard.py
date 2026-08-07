#!/usr/bin/env python3
"""권한 검문: 서식 노드가 본문 텍스트를 건드렸는지 코드로 확인한다.

사용법: python body_guard.py report.md report.html
본문을 꺼내고, 마크다운 마커를 지우고, 줄 단위로 대조한다. 그게 전부다.
"""
import re
import sys
from pathlib import Path


def md_lines(path):
    lines = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        t = line.strip()
        t = re.sub(r"^#+ ", "", t)     # 헤딩 마커 제거
        t = re.sub(r"^[-*] ", "", t)   # 리스트 마커 제거
        t = t.replace("**", "")
        if t:
            lines.append(t)
    return lines


def html_text(path):
    h = Path(path).read_text(encoding="utf-8")
    h = re.sub(r"<style.*?</style>", " ", h, flags=re.S | re.I)
    h = re.sub(r"<script.*?</script>", " ", h, flags=re.S | re.I)
    h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", h)


def main():
    if len(sys.argv) != 3:
        print("usage: python body_guard.py report.md report.html", file=sys.stderr)
        sys.exit(2)
    md, html = sys.argv[1], sys.argv[2]
    text = html_text(html)
    lines = md_lines(md)
    bad = [ln for ln in lines if ln not in text]
    if bad:
        print("FAIL: 본문에서 사라지거나 바뀐 줄")
        for ln in bad:
            print("  " + ln)
        sys.exit(1)
    print(f"PASS: 본문 {len(lines)}줄 전부 그대로")


if __name__ == "__main__":
    main()
