#!/usr/bin/env python3
"""Deterministic completion gate for the evidence-first postmortem workflow."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


WORK_DIR = Path(__file__).parent
DRAFT = WORK_DIR / "draft.md"
METRICS = WORK_DIR / "metrics.jsonl"
APP_LOG = WORK_DIR / "app.log"
DEPLOYS = WORK_DIR / "deploys.log"


def fail(check: str, detail: str, failures: list[str]) -> None:
    failures.append(f"{check}: {detail}")


def main() -> int:
    failures: list[str] = []
    draft = DRAFT.read_text(encoding="utf-8")
    metrics = [
        json.loads(line)
        for line in METRICS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    app_lines = APP_LOG.read_text(encoding="utf-8").splitlines()
    deploy_lines = DEPLOYS.read_text(encoding="utf-8").splitlines()

    p95 = max(metrics, key=lambda row: row["p95_ms"])
    error_rate = max(metrics, key=lambda row: row["err_rate_pct"])

    if f"**{p95['p95_ms']}ms**" not in draft or "14:45" not in draft:
        fail("metric_p95", "2500ms at 14:45 is missing or incorrect", failures)
    if f"**{error_rate['err_rate_pct']}%**" not in draft or "14:40" not in draft:
        fail("metric_error_rate", "9.8% at 14:40 is missing or incorrect", failures)
    if "두 최고값의 시각은 다르다" not in draft:
        fail("metric_timestamps", "the two maxima must remain distinct", failures)

    for heading in ("영향", "타임라인", "원인", "근거"):
        if f"## {heading}" not in draft:
            fail("structure", f"missing section: {heading}", failures)

    for claim in (
        "v2.3.1",
        "db_pool_size=10",
        "connection pool exhausted",
        "v2.3.0 롤백",
    ):
        if claim not in draft:
            fail("causal_chain", f"missing claim: {claim}", failures)

    citation_pattern = re.compile(r"`(app\.log|deploys\.log)`:([^`\n]+?)행")
    for filename, citation in citation_pattern.findall(draft):
        source = app_lines if filename == "app.log" else deploy_lines
        for line_number in map(int, re.findall(r"\d+", citation)):
            if not 1 <= line_number <= len(source):
                fail("source_citations", f"{filename}:{line_number} does not exist", failures)

    if failures:
        print("FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("PASS")
    print("- metric maxima match metrics.jsonl")
    print("- cited app.log and deploys.log rows exist")
    print("- causal chain and required sections are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
