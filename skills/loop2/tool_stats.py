#!/usr/bin/env python3
"""tool_stats.py: Claude Code 세션 로그(JSONL)에서 tool call을 집계해 터미널에 그린다.

사용법:
    python3 tool_stats.py            # 현재 폴더 프로젝트의 최신 세션
    python3 tool_stats.py <경로>     # 특정 세션 .jsonl 지정

stdlib 전용. 네트워크·설치 불필요.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from collections import Counter

GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def find_session(arg: str | None) -> str:
    if arg:
        return arg
    slug = re.sub(r"[^A-Za-z0-9]", "-", os.getcwd())
    proj = os.path.expanduser(os.path.join("~/.claude/projects", slug))
    files = glob.glob(os.path.join(proj, "*.jsonl"))
    if not files:  # 폴백: 전체 프로젝트에서 최신 세션
        files = glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl"))
    if not files:
        sys.exit("세션 로그(.jsonl)를 찾지 못했습니다. Claude Code로 대화를 한 번 한 뒤 다시 실행하세요.")
    return max(files, key=os.path.getmtime)


def brief_arg(tool_input: dict) -> str:
    for key in ("command", "file_path", "pattern", "prompt", "description", "skill", "url"):
        val = tool_input.get(key)
        if isinstance(val, str) and val.strip():
            one_line = " ".join(val.split())
            return one_line[:46] + ("…" if len(one_line) > 46 else "")
    return ""


def main() -> None:
    path = find_session(sys.argv[1] if len(sys.argv) > 1 else None)
    counts: Counter[str] = Counter()
    recent: list[tuple[str, str]] = []
    lines = 0
    out_tokens_by_msg: dict[str, int] = {}

    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            lines += 1
            try:
                d = json.loads(raw)
            except json.JSONDecodeError:
                continue
            msg = d.get("message") or {}
            usage = msg.get("usage") or {}
            if "output_tokens" in usage and msg.get("id"):
                out_tokens_by_msg[msg["id"]] = max(
                    out_tokens_by_msg.get(msg["id"], 0), usage["output_tokens"]
                )
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for item in content:
                if isinstance(item, dict) and item.get("type") == "tool_use":
                    name = item.get("name", "?")
                    counts[name] += 1
                    recent.append((name, brief_arg(item.get("input") or {})))

    total = sum(counts.values())
    size_kb = os.path.getsize(path) / 1024

    print(f"{BOLD}세션 로그{RESET}  {path}")
    print(f"{DIM}{lines:,}줄 · {size_kb:,.0f} KB (한 줄이 메시지 하나다){RESET}\n")

    print(f"{BOLD}tool call 집계: 총 {total}회{RESET}")
    if not counts:
        print("  (아직 tool call이 없습니다. Claude에게 파일을 하나 읽어 달라고 부탁해 보세요)")
    width = 34
    top = counts.most_common()
    peak = top[0][1] if top else 1
    for name, n in top:
        bar = "█" * max(1, round(n / peak * width))
        disp = name if len(name) <= 14 else name[:13] + "…"
        print(f"  {disp:<14} {GREEN}{bar}{RESET} {n}")

    if recent:
        print(f"\n{BOLD}최근 tool call 5개{RESET}")
        for name, arg in recent[-5:]:
            disp = name if len(name) <= 14 else name[:13] + "…"
            print(f"  {CYAN}{disp:<14}{RESET} {DIM}{arg}{RESET}")

    out_total = sum(out_tokens_by_msg.values())
    print(f"\n{BOLD}이 세션의 output tokens{RESET}  {YELLOW}{out_total:,}{RESET}"
          f"  {DIM}(루프가 한 바퀴 돌 때마다 이 숫자가 커진다. 루프 비용을 재는 눈금이다){RESET}")


if __name__ == "__main__":
    main()
