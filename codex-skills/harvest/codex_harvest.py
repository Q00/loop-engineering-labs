#!/usr/bin/env python3
"""Codex 세션 기록에서 반복 업무를 캔다. 읽기 전용.

~/.codex/sessions 와 ~/.codex/archived_sessions 의 rollout *.jsonl을 읽어
반복해서 손댄 산출물, 자주 실행한 명령, 사람이 직접 친 요청을 빈도순으로 보여준다.
세션 파일은 절대 수정하지 않는다.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path

ROOTS = (
    Path.home() / ".codex" / "sessions",
    Path.home() / ".codex" / "archived_sessions",
)

PATCH_FILE_RE = re.compile(r"\*\*\* (?:Update|Add) File: ([^\s\\\"]+)")
CMD_RE = re.compile(r"cmd:\s*\"((?:[^\"\\]|\\.){2,120})")
NOISE_HEAD = ("keep going", "계속", "고", "ㄱ")
NOISE_PREFIX = ("<", "# files mentioned", "[system")


def head(text: str, width: int = 46) -> str:
    t = " ".join(str(text).split())
    return t[:width] + ("…" if len(t) > width else "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lookback-hours", type=int, default=168)
    ap.add_argument("--root", action="append", type=Path, default=None)
    args = ap.parse_args()

    roots = tuple(args.root) if args.root else ROOTS
    cutoff = time.time() - args.lookback_hours * 3600
    paths = sorted(
        {p for r in roots if r.exists() for p in r.rglob("*.jsonl") if p.stat().st_mtime >= cutoff}
    )

    sessions = 0
    requests: Counter[str] = Counter()
    edits: Counter[str] = Counter()
    cmds: Counter[str] = Counter()
    delegations = 0
    edit_total = 0
    exec_total = 0

    for path in paths:
        sessions += 1
        try:
            for raw in path.open(encoding="utf-8"):
                try:
                    row = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                p = row.get("payload") or {}
                t, pt = row.get("type"), p.get("type")
                if t == "event_msg" and pt == "user_message":
                    msg = head(p.get("message") or "")
                    low = msg.lower()
                    if msg and low not in NOISE_HEAD and not low.startswith(NOISE_PREFIX):
                        requests[msg] += 1
                elif t == "event_msg" and pt == "sub_agent_activity":
                    delegations += 1
                elif t == "response_item" and pt == "custom_tool_call":
                    text = str(p.get("input") or "")
                    for f in PATCH_FILE_RE.findall(text):
                        edits[Path(f).name] += 1
                        edit_total += 1
                    for c in CMD_RE.findall(text):
                        exec_total += 1
                        toks = c.replace("\\\"", "\"").split()
                        if toks:
                            cmds[" ".join(toks[:2])] += 1
        except OSError:
            continue

    print(f"harvest  세션 {sessions}개 (최근 {args.lookback_hours}시간, Codex)")
    print(f"요청 {sum(requests.values())}건 · 위임 활동 {delegations}건 · "
          f"산출물 편집 {edit_total}회 · 명령 실행 {exec_total}회")

    print("\nmine 1: 반복해서 손댄 산출물 (여러 번 고쳤다면 그만큼 다시 하는 일이다)")
    for name, n in edits.most_common(7):
        print(f"  {name:<34} {n}회")
    if not edits:
        print("  (apply_patch 기록 없음)")

    print("\nmine 2: 자주 실행한 명령")
    for c, n in cmds.most_common(7):
        if n >= 2:
            print(f"  {c:<34} {n}회")

    print("\nmine 3: 사람이 직접 친 요청")
    for m, n in requests.most_common(7):
        mark = f" ({n}회)" if n > 1 else ""
        print(f"  - {m}{mark}")

    print("\n이 목록에서 '다음 주에도 또 할 일'을 하나 고르면 그것이 루프 후보다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
