#!/usr/bin/env python3
"""check.py: 발표 슬라이드(LaTeX beamer)를 결정적으로 채점한다. LLM 없음, 취향 없음.

사용법: python3 check.py <outline.tex> [데이터폴더]   (기본 데이터폴더: ./data)
출력: 항목별 O/X + 총점. 실패 항목에는 고칠 방향 힌트 한 줄 (에이전트의 reflection 재료).
종료 코드: 5점이면 0, 아니면 1.

규칙은 "자연스럽게 쓰면 통과하는 것"이 아니라 "지시서에 명시해야만 나오는 것"으로 고른다.
그래야 v1이 낮게 시작하고 루프가 돌 여지가 생긴다.

수치는 **데이터 폴더에서 직접 계산**한다. 그래서 같은 채점기를 train과 held-out에
그대로 쓸 수 있다. 지시서에 값을 통째로 박아 넣으면(암기) train은 통과하지만
held-out에서는 다른 값이 나와 무너진다. 그 대비가 4강 게이트의 관찰 대상이다.
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


def facts_from(data_dir: str) -> list[tuple[str, str]]:
    """데이터에서 실측값을 뽑아 (정규식, 사람이 읽을 표기) 목록으로."""
    mpath = os.path.join(data_dir, "metrics.jsonl")
    if not os.path.exists(mpath):
        sys.exit(f"데이터 폴더에 metrics.jsonl이 없다: {data_dir}")
    rows = [json.loads(l) for l in open(mpath, encoding="utf-8")]
    p95 = max(r["p95_ms"] for r in rows)
    err = max(r["err_rate_pct"] for r in rows)

    # 복구 시각은 app.log에서 롤백이 **완료된** 줄을 찾는다.
    # (승인·논의 줄에도 rollback이 나오므로 complete까지 확인해야 정확하다)
    rollback = ""
    apath = os.path.join(data_dir, "app.log")
    if os.path.exists(apath):
        for line in open(apath, encoding="utf-8"):
            low = line.lower()
            if "rollback" in low and "complete" in low:
                m = re.search(r"T(\d{2}:\d{2})", line)
                if m:
                    rollback = m.group(1)
                    break

    p95_s = f"{p95:,}"
    out = [
        (rf"p95 최고 {p95_s.replace(',', ',?')}\s*ms", f"p95 최고 {p95}ms"),
        (rf"오류율 최고 {re.escape(str(err))}\s*\\?%", f"오류율 최고 {err}%"),
    ]
    if rollback:
        out.append((rf"복구 {re.escape(rollback)}", f"복구 {rollback}"))
    return out


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("사용법: python3 check.py <outline.tex> [데이터폴더]")
    text = open(sys.argv[1], encoding="utf-8").read()
    data_dir = sys.argv[2] if len(sys.argv) > 2 else "data"
    FACTS = facts_from(data_dir)

    # 슬라이드 분해: \begin{frame}...\end{frame} 기준
    # 프레임 제목은 \frametitle{} 또는 \begin{frame}[opts]{Title} 축약형 둘 다 인정한다.
    frame_opens = re.finditer(r"\\begin\{frame\}(?:\[[^\]]*\])?(?:\{([^}]*)\})?", text)
    slides = []  # (title, body)
    for m in frame_opens:
        end = text.find(r"\end{frame}", m.end())
        if end == -1:
            continue
        chunk = text[m.end():end]
        short_title = m.group(1)
        tm = re.search(r"\\frametitle\{([^}]*)\}", chunk)
        if tm:
            title = tm.group(1).strip()
            body = chunk[tm.end():]
        elif short_title is not None:
            title = short_title.strip()
            body = chunk
        else:
            title, body = "", chunk
        slides.append((title, body))

    missing_facts = [label for pat, label in FACTS if not re.search(pat, text)]
    next_steps = next((s for s in slides if "다음 단계" in s[0]), None)
    max_bullets = max((len(re.findall(r"\\item\b", b)) for _, b in slides), default=0)

    checks: list[tuple[str, bool, str]] = [
        (
            f"슬라이드 5~7장 (지금 {len(slides)}장)",
            5 <= len(slides) <= 7,
            "\\begin{frame}...\\end{frame} 기준 5~7장으로 나눠라",
        ),
        (
            "첫 슬라이드: \\frametitle에 '결론' + 본문 한 줄",
            bool(slides) and "결론" in slides[0][0] and len(re.sub(r"\\[a-zA-Z]+|\{|\}", "", slides[0][1]).strip()) >= 10,
            "첫 슬라이드 \\frametitle에 '결론'을 넣고 본문을 한 줄 요약으로 채워라",
        ),
        (
            f"핵심 지표 {len(FACTS)}종 표기 그대로"
            + (f" (빠짐: {', '.join(missing_facts)})" if missing_facts else ""),
            not missing_facts,
            "영향 수치를 이 데이터의 실측값으로, 표기 그대로 넣어라: "
            + " · ".join(label for _, label in FACTS),
        ),
        (
            "'다음 단계' 슬라이드 + 항목마다 담당",
            next_steps is not None and next_steps[1].count("담당") >= 2,
            "\\frametitle에 '다음 단계'를 넣은 슬라이드를 만들고 항목마다 '담당: <역할>'을 붙여라",
        ),
        (
            f"슬라이드당 불릿(\\item) 3개 이하 (최대 {max_bullets}개)",
            bool(slides) and max_bullets <= 3,
            "각 슬라이드의 \\item을 3개 이하로 줄여라. 발표 개요는 대본이 아니다",
        ),
    ]

    score = 0
    print(f"{BOLD}check.py: 규칙 5개, 채점자는 코드{RESET}\n")
    for label, ok, hint in checks:
        if ok:
            score += 1
            print(f"  {GREEN}O{RESET}  {label}")
        else:
            print(f"  {RED}X{RESET}  {label}  {DIM}힌트: {hint}{RESET}")
    print(f"\n  {BOLD}점수 {score}/5{RESET}")
    sys.exit(0 if score == 5 else 1)


if __name__ == "__main__":
    main()
