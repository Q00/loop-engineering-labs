#!/usr/bin/env python3
"""Harvest recurring work from explicit Codex lab JSONL traces.

This is deliberately not a Codex internal-transcript reader. It only reads
codex-tool-calls.jsonl files produced by the loop labs in the selected root.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path


FILE_RE = re.compile(r"[A-Za-z0-9][\w.-]*\.(?:jsonl|log|md|py|tex|json|txt)\b")


def parse_time(value: object) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def task_key(value: str) -> str:
    text = " ".join(value.split()).lower()
    text = re.sub(r"\b[rv]\d+\b", "<round>", text)
    text = re.sub(r"\d+", "<n>", text)
    return text[:72] or "(목적 없음)"


def find_logs(root: Path, explicit: list[str], excluded: set[Path]) -> list[Path]:
    if explicit:
        candidates = [Path(item).expanduser().resolve() for item in explicit]
    else:
        candidates = list(root.rglob("codex-tool-calls.jsonl"))
        candidates.extend(root.rglob("*-bootstrap.jsonl"))
    found: list[Path] = []
    for path in candidates:
        resolved = path.resolve()
        if resolved in excluded or ".git" in resolved.parts or not resolved.is_file():
            continue
        if resolved not in found:
            found.append(resolved)
    return sorted(found)


def load_events(paths: list[Path], cutoff: float) -> list[tuple[Path, dict]]:
    events: list[tuple[Path, dict]] = []
    for path in paths:
        for raw in path.read_text(encoding="utf-8").splitlines():
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            timestamp = parse_time(event.get("ts"))
            if timestamp is None or timestamp < cutoff:
                continue
            events.append((path, event))
    return events


def bar(value: int, peak: int, width: int = 20) -> str:
    return "█" * max(1, round(value / max(peak, 1) * width))


def show_counter(title: str, counter: Counter[str], top: int) -> None:
    print(f"\n{title}")
    rows = counter.most_common(top)
    if not rows:
        print("  (아직 관찰된 항목이 없다)")
        return
    peak = rows[0][1]
    for label, count in rows:
        print(f"  {label[:72]:<72} {bar(count, peak)} {count}회")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="명시적 실습 trace를 찾을 루트")
    parser.add_argument("--lookback-hours", type=float, default=72.0)
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--log", action="append", default=[], help="특정 JSONL만 읽기")
    parser.add_argument("--exclude", action="append", default=[], help="집계에서 뺄 JSONL")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    excluded = {Path(item).expanduser().resolve() for item in args.exclude}
    paths = find_logs(root, args.log, excluded)
    cutoff = time.time() - args.lookback_hours * 3600
    events = load_events(paths, cutoff)

    print(
        f"harvest  명시적 Codex 실습 trace {len(paths)}개 · "
        f"최근 {args.lookback_hours:g}시간 tool call {len(events)}개"
    )
    print("  원천: Codex 내부 로그가 아니라 각 loop 실습이 기록한 codex-tool-calls.jsonl")
    for path in paths:
        count = sum(1 for event_path, _ in events if event_path == path)
        if count:
            print(f"  - {path.relative_to(root) if path.is_relative_to(root) else path}: {count}개")

    if not events:
        print("\n관찰할 기록이 없다. 먼저 loop2 또는 loop3를 실행하거나 기간을 늘린다.")
        return 0

    tools: Counter[str] = Counter()
    purposes: Counter[str] = Counter()
    outputs: Counter[str] = Counter()
    delegated: Counter[str] = Counter()
    checks = 0

    for _, event in events:
        tool = str(event.get("tool", "?"))
        purpose = str(event.get("purpose", ""))
        target = str(event.get("target", ""))
        tools[tool] += 1
        purposes[task_key(purpose)] += 1

        if tool == "apply_patch":
            names = FILE_RE.findall(target)
            outputs[Path(names[-1]).name if names else target[:72]] += 1
        if "agent" in tool.lower() or "replay" in purpose.lower():
            delegated[task_key(purpose)] += 1
        if re.search(r"\b(check|verify|grade|test)\w*\.py\b", target, re.I) or "채점" in purpose:
            checks += 1

    print(
        f"\n요약  도구 {sum(tools.values())}회 · 산출물 편집 {sum(outputs.values())}회 · "
        f"위임/replay {sum(delegated.values())}회 · 검증 {checks}회"
    )
    show_counter("mine 1: 반복된 작업 목적", purposes, args.top)
    show_counter("mine 2: 반복해서 편집한 산출물", outputs, args.top)
    show_counter("mine 3: 서브에이전트 replay 후보", delegated, args.top)
    print("\n이 목록에서 '내일도 또 할 일'을 하나 고르면 replay 후보가 된다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
