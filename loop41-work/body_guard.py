#!/usr/bin/env python3
"""body_guard.py: 디자인 노드가 권한 경계를 지켰는지 코드로 확인한다.

디자인 노드의 계약은 두 줄이다.

  1. **지우거나 고치지 않는다.** 원본 본문의 줄이 순서 그대로 전부 남아 있어야 한다.
  2. **새 문장을 쓰지 않는다.** 줄을 더해도 되지만, 더한 줄에 한글이 있으면 안 된다.
     그림을 넣고 배치를 잡는 것은 LaTeX 명령이지 문장이 아니다.

그래서 차트를 끼워 넣는 것은 통과하고, "약 2.5초"로 고치거나 요약을 덧붙이는 것은 걸린다.
권한은 "아무것도 하지 마라"가 아니라 **무엇은 되고 무엇은 안 되는가**다.

사용법: python3 body_guard.py <원본.tex> <스타일본.tex>
종료 코드: 계약을 지켰으면 0, 어겼으면 1.
"""
from __future__ import annotations

import difflib
import re
import sys

GREEN = "\033[32m"
RED = "\033[31m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

HANGUL = re.compile(r"[가-힣]")


def strip_comments(text: str) -> str:
    """LaTeX 주석을 지운다. 주석 안의 \\begin{document}에 속아 본문을 잘못 잡는 것을 막는다."""
    out = []
    for line in text.splitlines():
        m = re.search(r"(?<!\\)%", line)
        out.append(line[: m.start()] if m else line)
    return "\n".join(out)


def body(path: str) -> list[str]:
    """document 환경 안쪽을 줄 목록으로. 들여쓰기와 빈 줄은 비교에서 뺀다."""
    try:
        text = strip_comments(open(path, encoding="utf-8").read())
    except OSError as e:
        sys.exit(f"파일을 열 수 없다: {path} ({e})")
    m = re.search(r"\\begin\{document\}(.*)\\end\{document\}", text, re.S)
    if not m:
        sys.exit(f"{path}에 document 환경이 없다")
    return [ln.strip() for ln in m.group(1).splitlines() if ln.strip()]


def short(s: str, n: int = 92) -> str:
    one = " ".join(s.split())
    return one[:n] + ("…" if len(one) > n else "")


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("사용법: python3 body_guard.py <원본.tex> <스타일본.tex>")
    src, dst = sys.argv[1], sys.argv[2]
    a, b = body(src), body(dst)

    removed: list[str] = []   # 지웠거나 고친 줄
    added_text: list[str] = []  # 새로 쓴 문장
    added_cmd: list[str] = []   # 그림·배치 명령 (허용)
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op in ("delete", "replace"):
            removed += a[i1:i2]
        if op in ("insert", "replace"):
            for ln in b[j1:j2]:
                (added_text if HANGUL.search(ln) else added_cmd).append(ln)

    print(f"{BOLD}body_guard.py: 디자인 노드가 계약을 지켰는가{RESET}")
    print(f"{DIM}{src} ({len(a)}줄)  vs  {dst} ({len(b)}줄){RESET}\n")

    if not removed and not added_text:
        print(f"  {GREEN}O{RESET}  원본 본문 {len(a)}줄이 순서 그대로 남아 있다")
        if added_cmd:
            print(f"  {GREEN}O{RESET}  더해진 {len(added_cmd)}줄은 전부 명령이다 {DIM}(새 문장 없음){RESET}")
            for ln in added_cmd[:4]:
                print(f"       {DIM}+ {short(ln)}{RESET}")
        else:
            print(f"  {GREEN}O{RESET}  더해진 줄 없음 {DIM}(프리앰블만 바뀌었다){RESET}")
        print(f"\n  {BOLD}{GREEN}권한 경계 지켜짐{RESET}")
        sys.exit(0)

    if removed:
        print(f"  {RED}X{RESET}  원본 본문 {len(removed)}줄이 지워졌거나 바뀌었다")
        for ln in removed[:4]:
            print(f"       {RED}- {short(ln)}{RESET}")
    if added_text:
        print(f"  {RED}X{RESET}  한글이 든 줄 {len(added_text)}개가 새로 쓰였다 {DIM}(디자인 노드는 문장을 쓰지 않는다){RESET}")
        for ln in added_text[:4]:
            print(f"       {GREEN}+ {short(ln)}{RESET}")
    print(f"\n  {BOLD}{RED}권한 경계 위반{RESET}{BOLD}: 지우지 말 것, 새 문장을 쓰지 말 것{RESET}")
    sys.exit(1)


if __name__ == "__main__":
    main()
