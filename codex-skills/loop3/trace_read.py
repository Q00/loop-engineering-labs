#!/usr/bin/env python3
"""Read the explicit Codex lab trace used by the loop3 experiment."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path


FILE_RE = re.compile(r"[A-Za-z0-9][\w.-]*\.(?:jsonl|log|md|py|json|txt)\b")


def parse_time(value: str) -> float | None:
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def since_time(marker: str) -> float:
    try:
        return os.stat(marker).st_mtime
    except OSError:
        raise SystemExit(f"마커 파일이 없다: {marker}  (STEP 시작 전에 touch {marker})")


def load_events(path: Path, since: float | None) -> list[dict]:
    events: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        raise SystemExit(f"Codex 실습 로그가 없다: {path}")
    for raw in lines:
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        timestamp = parse_time(event.get("ts", ""))
        if since is not None and (timestamp is None or timestamp < since):
            continue
        events.append(event)
    return events


def touched(events: list[dict]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for event in events:
        target = str(event.get("target", ""))
        names = {match.group(0) for match in FILE_RE.finditer(target)}
        for name in names:
            tools = result.setdefault(name, [])
            tool = str(event.get("tool", "?"))
            if tool not in tools:
                tools.append(tool)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", default="loop3-work/codex-tool-calls.jsonl")
    parser.add_argument("--since", metavar="MARKER")
    parser.add_argument("--tail", type=int, default=12)
    parser.add_argument("--touched", action="store_true")
    parser.add_argument("--read-check", metavar="FILE")
    args = parser.parse_args()

    log_path = Path(args.log)
    if not log_path.exists():
        print(f"Codex 실습 로그가 없다: {log_path}", file=sys.stderr)
        return 2
    since = since_time(args.since) if args.since else None
    events = load_events(log_path, since)
    scope = f" ({args.since} 이후)" if args.since else ""

    if args.read_check:
        target = Path(args.read_check).name
        matches = [e for e in events if target in str(e.get("target", ""))]
        print(f"과정 검증: {target}을 실제로 다뤘는가{scope}")
        if matches:
            for event in matches:
                print(f"  읽었다 · {event.get('tool')} · {event.get('purpose')}")
            return 0
        print(f"  {target}을 대상으로 한 tool call이 없다")
        return 1

    print(f"Codex 실습 로그: {log_path}{scope}")
    print(f"tool call {len(events)}개 기록됨")
    if not events:
        print("이 구간에 기록이 없다. 마커·로그 경로·실습 실행 여부를 확인한다.")
        return 0

    if args.touched:
        print("\n이번 구간의 대상 파일")
        for name, tools in sorted(touched(events).items()):
            print(f"  {name}: {' · '.join(tools)}")
        return 0

    print(f"\n최근 tool call {min(args.tail, len(events))}개")
    for event in events[-args.tail :]:
        print(
            f"  {event.get('tool', '?'):<14} "
            f"{event.get('purpose', '')} → {event.get('target', '')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
