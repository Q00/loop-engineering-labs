#!/usr/bin/env python3
"""Reference harness for the loop workshop. 강사 참조용 — 실습 중에는 열지 않는다.

수강 환경에서는 이 파일을 배포하지 않고, PROMPT.md를 AI 코딩 도구에 넣어
같은 명세의 miniloop.py를 생성하게 한다. 이 구현은 기대 출력 검증용 정본.
"""
import json
import re
import sys
from pathlib import Path

# 규칙 적용 순서는 prompt.txt의 줄 순서와 무관하게 이 순서로 고정한다.
ORDER = ["strip-checkbox", "drop-urgency", "assignee-first", "collapse-spaces"]

URGENCY = ("ASAP", "급함", "빨리")


def apply_rule(name, s):
    if name == "strip-checkbox":
        t = s.lstrip()
        for marker in ("[ ]", "[x]", "[X]"):
            if t.startswith(marker):
                return t[len(marker):]
        return s
    if name == "drop-urgency":
        s = s.replace("!", "")
        parts = s.split(" ")
        parts = [p for p in parts if p not in URGENCY]
        return " ".join(parts)
    if name == "assignee-first":
        m = re.search(r"@\S+", s)
        if not m:
            return s
        rest = s[: m.start()] + s[m.end():]
        return m.group(0) + " " + rest
    if name == "collapse-spaces":
        return re.sub(r" +", " ", s).strip()
    return s


def load_rules(path):
    lines = [ln.strip() for ln in Path(path).read_text(encoding="utf-8").splitlines()]
    wanted = {ln for ln in lines if ln}
    return [r for r in ORDER if r in wanted]


def transform(s, rules):
    for r in rules:
        s = apply_rule(r, s)
    return s


def load_tasks(split):
    tasks = json.loads(Path("tasks.json").read_text(encoding="utf-8"))
    return [t for t in tasks if t["split"] == split]


def score(split, rules, write_trace=False):
    tasks = load_tasks(split)
    passed = 0
    for t in tasks:
        got = transform(t["input"], rules)
        ok = got == t["expected"]
        passed += ok
        if write_trace:
            with open("trace.jsonl", "a", encoding="utf-8") as f:
                rec = {"id": t["id"], "input": t["input"],
                       "expected": t["expected"], "got": got, "pass": ok}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return passed, len(tasks)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"

    if cmd == "run":
        rules = load_rules("prompt.txt")
        p, n = score("train", rules, write_trace=True)
        print(json.dumps({"split": "train", "score": round(p / n, 3),
                          "passed": p, "total": n}))

    elif cmd == "trace":
        last = {}
        for line in Path("trace.jsonl").read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            last[rec["id"]] = rec  # 마지막 run 기준
        for rec in last.values():
            if not rec["pass"]:
                print(f'{rec["id"]}  입력={rec["input"]!r}  '
                      f'기대={rec["expected"]!r}  실제={rec["got"]!r}')

    elif cmd == "gate":
        cand_path = sys.argv[sys.argv.index("--candidate") + 1]
        cur_p, n = score("heldout", load_rules("prompt.txt"))
        cand_p, _ = score("heldout", load_rules(cand_path))
        cur, cand = round(cur_p / n, 3), round(cand_p / n, 3)
        verdict = "accept" if cand > cur else "reject"
        if verdict == "accept":
            Path("prompt.txt").write_text(
                Path(cand_path).read_text(encoding="utf-8"), encoding="utf-8")
        print(json.dumps({"verdict": verdict, "current": cur, "candidate": cand}))

    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
