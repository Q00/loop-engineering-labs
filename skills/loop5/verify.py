#!/usr/bin/env python3
"""verify.py: 장애 보고서를 RULES.md 규정대로 결정적으로 검문한다.

사용법: python3 verify.py <report.md> [데이터폴더]   (기본 데이터폴더: ./data)

LLM 없음. 인용은 원본 로그와 문자열 대조, 수치는 metrics.jsonl에서 직접 계산해 대조.
종료 코드: 위반 0건이면 0(PASS), 아니면 1(FAIL).
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

REQUIRED_SECTIONS = ["요약", "타임라인", "근본 원인", "재발 방지"]
HEDGES = [(r"아마(?!존)", "아마"), (r"추정", "추정"), (r"로 보인다", "로 보인다"), (r"것 같다", "것 같다")]
MIN_QUOTE_LEN = 15


def section_body(text: str, title: str) -> str | None:
    m = re.search(rf"(?ms)^## +{re.escape(title)}\s*$(.*?)(?=^## |\Z)", text)
    return m.group(1) if m else None


def needed_sources(report_text: str) -> list[str]:
    """보고서가 인용·대조 근거로 쓴 파일들."""
    needed = ["app.log"] if re.search(r"\[app\.log:\d+\]", report_text) else []
    if re.search(r"(p95 최고|오류율 최고)", report_text):
        needed.append("metrics.jsonl")
    return needed


def mentions(text: str, filename: str) -> bool:
    """규정 7의 '느슨한' 일치: 파일명 그대로, 또는 충분히 특징적인 어간(6자 이상)."""
    if filename in text:
        return True
    stem = os.path.splitext(filename)[0]
    return len(stem) >= 6 and stem in text


def trace_violations(report_text: str, marker: str) -> tuple[list[str], list[str]]:
    """규정 6·7(과정 검증): 2강의 그 세션 로그를 마커 이후로 잘라 본다.

    trace_read.py를 같은 폴더에서 불러 쓴다. 산출물만 보는 검문(규정 1~5)과 달리
    여기서는 '어떻게 썼는가'를 본다.
      규정 6 (tool call 기록): 인용한 원본을 이번 라운드에 실제로 열었는가. 행동을 본다.
      규정 7 (사고 요약): 그 원본이 사고에도 등장하는가. 자기 보고를 본다.
    (위반 목록, 안내 노트)를 돌려준다. 노트는 위반으로 세지 않는다.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    try:
        import trace_read
    except ImportError:
        return ["[규정6] trace_read.py를 찾지 못해 과정 검증을 건너뜀"], []

    try:
        since = trace_read.since_from(marker)
        log = trace_read.find_log(None, since)
        hits = trace_read.touched_files(trace_read.load_calls(log, since))
        thoughts, n_blocks = trace_read.load_thinking(log, since)
    except SystemExit as e:
        return [f"[규정6] 세션 로그를 읽지 못했다: {e}"], []

    needed = needed_sources(report_text)
    out: list[str] = []
    notes: list[str] = []

    for f in needed:
        if f not in hits:
            out.append(f"[규정6] {f}을 인용·대조했는데 이번 라운드에 연 기록이 없다 (2강의 그 세션 로그 기준)")

    # 규정 7: 사고 요약이 꺼져 있으면 위반이 아니라 건너뛴다 (재료가 없는 것과 어긴 것은 다르다)
    if not thoughts:
        why = "사고 요약이 꺼져 있다" if n_blocks else "이 구간에 사고 블록이 없다"
        notes.append(f"[규정7] 건너뜀: {why} (showThinkingSummaries: true + 새 세션)")
        return out, notes

    blob = "\n".join(thoughts)
    for f in needed:
        if not mentions(blob, f):
            out.append(f"[규정7] {f}을 근거로 썼는데 사고 요약에 등장하지 않는다 (사고 블록 {len(thoughts)}개 기준)")
    return out, notes


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("사용법: python3 verify.py <report.md> [데이터폴더] [--trace <마커파일>]")
    argv = [a for a in sys.argv[1:]]
    marker = None
    if "--trace" in argv:
        i = argv.index("--trace")
        if i + 1 >= len(argv):
            sys.exit("--trace 다음에 마커 파일 경로가 필요하다")
        marker = argv[i + 1]
        del argv[i : i + 2]
    text = open(argv[0], encoding="utf-8").read()
    data_dir = argv[1] if len(argv) > 1 else "data"
    log_lines = open(os.path.join(data_dir, "app.log"), encoding="utf-8").read().splitlines()
    metrics = [json.loads(l) for l in open(os.path.join(data_dir, "metrics.jsonl"), encoding="utf-8")]
    real_p95 = max(r["p95_ms"] for r in metrics)
    real_err = max(r["err_rate_pct"] for r in metrics)

    violations: list[str] = []

    # 규정 1: 필수 섹션 (빈 껍데기 불인정)
    for title in REQUIRED_SECTIONS:
        body = section_body(text, title)
        if body is None:
            violations.append(f"[규정1] 필수 섹션 없음: ## {title}")
        elif len(body.strip()) < 10:
            violations.append(f"[규정1] ## {title} 섹션이 비어 있음 (본문 10자 이상)")

    # 규정 2: 타임라인 시간순 (인라인 코드 인용 안의 타임스탬프는 제외)
    tl = re.sub(r"`[^`]*`", "", section_body(text, "타임라인") or "")
    times = re.findall(r"(?<![\d:])(\d{2}:\d{2})(?![\d:])", tl)
    if times and times != sorted(times):
        violations.append(f"[규정2] 타임라인이 시간순이 아님: {' → '.join(times)}")

    # 규정 3: 로그 인용 대조
    quotes = re.findall(r"`([^`]+)`\s*\[app\.log:(\d+)\]", text)
    if len(quotes) < 2:
        violations.append(f"[규정3] 로그 인용이 {len(quotes)}개 (2개 이상, `인용문` [app.log:N] 형식)")
    for quoted, n_str in quotes:
        n = int(n_str)
        if len(quoted) < MIN_QUOTE_LEN:
            violations.append(f"[규정3] 인용문이 {len(quoted)}자. {MIN_QUOTE_LEN}자 이상 복사해야 대조가 성립")
        elif not (1 <= n <= len(log_lines)):
            violations.append(f"[규정3] app.log:{n} (존재하지 않는 행, 로그는 {len(log_lines)}행)")
        elif quoted not in log_lines[n - 1]:
            violations.append(f"[규정3] app.log:{n} 대조 실패: 그 행에 `{quoted[:40]}` 없음")

    # 규정 4: 수치 실측 대조 (본문 어디에 나오든 전부 검사)
    m95_all = re.findall(r"p95 최고\s*([\d,]+)\s*ms", text)
    if not m95_all:
        violations.append("[규정4] 'p95 최고 Xms' 표기 없음")
    for m in m95_all:
        if int(m.replace(",", "")) != real_p95:
            violations.append(f"[규정4] p95 최고 {m}ms 주장, 실측은 {real_p95}ms")
    merr_all = re.findall(r"오류율 최고\s*([\d.]+)\s*%", text)
    if not merr_all:
        violations.append("[규정4] '오류율 최고 Y%' 표기 없음")
    for m in merr_all:
        if float(m) != real_err:
            violations.append(f"[규정4] 오류율 최고 {m}% 주장, 실측은 {real_err}%")

    # 규정 5: 헤지 금지
    for pat, label in HEDGES:
        if re.search(pat, text):
            violations.append(f"[규정5] 헤지 표현 발견: \"{label}\"")

    # 규정 6·7(선택): 과정 검증. --trace 마커를 주면 켜진다
    notes: list[str] = []
    if marker:
        more, notes = trace_violations(text, marker)
        violations += more

    header = "검문 7종, 산출물과 과정을 함께" if marker else "검문 5종, 검문관은 코드"
    print(f"{BOLD}verify.py: {header}{RESET}\n")
    for n in notes:
        print(f"  {DIM}-  {n}{RESET}")
    if notes:
        print()
    if violations:
        for v in violations:
            print(f"  {RED}X{RESET}  {v}")
        print(f"\n  {BOLD}{RED}FAIL{RESET}{BOLD}: 위반 {len(violations)}건{RESET}")
        sys.exit(1)
    print(f"  {GREEN}위반 0건{RESET}")
    print(f"\n  {BOLD}{GREEN}PASS{RESET}  {DIM}인용은 원본과 일치, 수치는 실측과 일치{RESET}")
    sys.exit(0)


if __name__ == "__main__":
    main()
