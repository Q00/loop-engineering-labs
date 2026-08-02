#!/usr/bin/env python3
"""miniloop.py - RUN / TRACE / JUDGE / EDIT / GATE 미니 자기개선 루프.

강사 참조용 레퍼런스 구현. stdlib only, Python 3.10+.
LLM도 네트워크도 쓰지 않는다. 같은 입력이면 늘 같은 점수가 나온다.

    python3 miniloop.py run
    python3 miniloop.py trace
    python3 miniloop.py gate --candidate prompt.better.txt
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

TASKS = Path("tasks.json")
PROMPT = Path("prompt.txt")
TRACE = Path("trace.jsonl")

STOPWORDS = {"the", "a", "an", "of"}


# ---------------------------------------------------------------- rules
def _lowercase(s: str) -> str:
    return s.lower()


def _strip_punct(s: str) -> str:
    return "".join(c for c in s if c.isalnum() or c.isspace())


def _drop_stopwords(s: str) -> str:
    # 공백은 그대로 두고, 낱말 전체가 불용어일 때만 지운다.
    parts = re.split(r"(\s+)", s)
    return "".join("" if p and not p.isspace() and p in STOPWORDS else p for p in parts)


def _collapse_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _hyphenate(s: str) -> str:
    return s.replace(" ", "-")


# 파일에 적힌 순서와 무관하게 늘 이 순서로 적용한다.
RULE_ORDER = [
    ("lowercase", _lowercase),
    ("strip-punct", _strip_punct),
    ("drop-stopwords", _drop_stopwords),
    ("collapse-spaces", _collapse_spaces),
    ("hyphenate", _hyphenate),
]
KNOWN = {name for name, _ in RULE_ORDER}


def load_rules(path: Path) -> set[str]:
    enabled: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        name = raw.strip()
        if not name:
            continue
        if name not in KNOWN:
            print(f"unknown rule: {name}", file=sys.stderr)
            sys.exit(2)
        enabled.add(name)
    return enabled


def apply_rules(text: str, enabled: set[str]) -> str:
    for name, fn in RULE_ORDER:
        if name in enabled:
            text = fn(text)
    return text


# ---------------------------------------------------------------- scoring
def load_split(split: str) -> list[tuple[str, str, str]]:
    data = json.loads(TASKS.read_text(encoding="utf-8"))
    prefix = "t" if split == "train" else "h"
    return [
        (f"{prefix}{i}", inp, exp)
        for i, (inp, exp) in enumerate(data[split], start=1)
    ]


def score(split: str, prompt_path: Path) -> tuple[float, int, int, list[dict]]:
    enabled = load_rules(prompt_path)
    rows = []
    for case_id, inp, exp in load_split(split):
        out = apply_rules(inp, enabled)
        rows.append(
            {
                "case_id": case_id,
                "input": inp,
                "expected": exp,
                "output": out,
                "passed": out == exp,
            }
        )
    passed = sum(r["passed"] for r in rows)
    total = len(rows)
    return round(passed / total, 3), passed, total, rows


# ---------------------------------------------------------------- commands
def next_run_id() -> str:
    n = 0
    if TRACE.exists():
        for line in TRACE.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rid = json.loads(line)["run_id"]
            n = max(n, int(rid.lstrip("r")))
    return f"r{n + 1}"


def cmd_run() -> int:
    s, passed, total, rows = score("train", PROMPT)
    run_id = next_run_id()
    with TRACE.open("a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps({"run_id": run_id, **r}, ensure_ascii=False) + "\n")
    print(json.dumps({"split": "train", "score": s, "passed": passed, "total": total}))
    return 0


def cmd_trace() -> int:
    if not TRACE.exists():
        print("no trace.jsonl - run first", file=sys.stderr)
        return 1
    records = [
        json.loads(line)
        for line in TRACE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not records:
        print("no trace.jsonl - run first", file=sys.stderr)
        return 1
    latest = records[-1]["run_id"]
    for r in records:
        if r["run_id"] == latest and not r["passed"]:
            print(
                f'{r["case_id"]:<4}{json.dumps(r["input"]):<28}'
                f'expected {r["expected"]:<22}got {r["output"]}'
            )
    return 0


def cmd_gate(candidate: Path) -> int:
    cur, *_ = score("heldout", PROMPT)
    cand, *_ = score("heldout", candidate)
    accept = cand > cur
    print(
        json.dumps(
            {
                "verdict": "accept" if accept else "reject",
                "current": cur,
                "candidate": cand,
            }
        )
    )
    if accept:
        shutil.copyfile(candidate, PROMPT)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run")
    sub.add_parser("trace")
    g = sub.add_parser("gate")
    g.add_argument("--candidate", required=True, type=Path)

    args = ap.parse_args()
    if args.cmd == "run":
        return cmd_run()
    if args.cmd == "trace":
        return cmd_trace()
    return cmd_gate(args.candidate)


if __name__ == "__main__":
    sys.exit(main())
