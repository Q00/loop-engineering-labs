#!/usr/bin/env python3
"""sleep_harvest.py: 지난 세션 기록에서 "다시 할 만한 일"을 캐낸다.

SkillOpt-Sleep의 앞 두 단계(harvest -> mine)를 작게 재현한 것이다.
실물은 `skillopt-sleep`이 ~/.claude/projects 의 transcript를 harvest해서
반복 과업을 mine한 뒤 replay -> held-out gate -> adopt로 이어간다.
여기서는 같은 재료(2강에서 본 그 세션 로그)로 앞 두 단계만 본다.

사용법:
    python3 sleep_harvest.py                     # 최근 72시간 세션 전부 (기본)
    python3 sleep_harvest.py --lookback-hours 168  # 최근 일주일
    python3 sleep_harvest.py --this-session      # 지금 세션 하나만
    python3 sleep_harvest.py --all               # 프로젝트를 가리지 않고 전부
    python3 sleep_harvest.py --log <경로>        # 특정 세션 로그 지정
    python3 sleep_harvest.py --top 5             # 반복 과업 상위 N개

기본이 72시간인 이유: 자는 동안 도는 루프는 "지금 이 대화"가 아니라 **지난 며칠의 일**을
재료로 삼는다. 실물 `skillopt-sleep`의 `--lookback-hours` 기본값도 72다. 덕분에 실습을
새 창에서 시작해도, 어제 다른 창에서 한 일이 그대로 잡힌다.
"이번 주에 세 번 이상 반복한 일"도 기억으로 찾을 게 아니라 `--lookback-hours 168`로 찾는다.

stdlib 전용. trace_read.py와 같은 폴더에 있어야 한다(로그 탐색을 공유한다).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from trace_read import find_log, scan_meta, since_from
except ImportError:
    sys.exit("trace_read.py를 같은 폴더에서 찾지 못했다 (스킬 폴더에 함께 복사돼야 한다).")


def logs_in_window(hours: float, all_projects: bool) -> list[str]:
    """최근 N시간 안에 쓰인 세션 로그들. 기본은 지금 폴더와 관련된 것만."""
    cutoff = time.time() - hours * 3600
    here = os.path.realpath(os.getcwd())
    out = []
    for path in glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl")):
        if os.path.getmtime(path) < cutoff:
            continue
        cwds, ncalls = scan_meta(path)
        if ncalls == 0:
            continue  # 빈 세션은 뺀다
        if all_projects:
            out.append(path)
            continue
        for c in cwds:
            c = os.path.realpath(c)
            if here == c or here.startswith(c + os.sep) or c.startswith(here + os.sep):
                out.append(path)
                break
    return sorted(out, key=os.path.getmtime)

GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

# 산출물로 볼 tool과 경로가 담긴 자리
WRITERS = {"Write": "file_path", "Edit": "file_path", "NotebookEdit": "notebook_path"}
DELEGATES = {"Task", "Agent"}
NOISE = re.compile(
    r"^\s*(<(command-|task-notification|local-command|system-reminder)"
    r"|Another Claude session sent a message|Base directory for this skill)"
)


def task_key(prompt: str) -> str:
    """위임 프롬프트를 묶을 키.

    경로를 그대로 두면 파일마다 다른 키가 되어 "같은 일을 반복했다"가 안 보인다.
    자리표시자로 바꾸면 대상만 다른 같은 작업이 하나로 묶인다. mine의 목적이 그것이다.
    """
    s = " ".join(prompt.split())
    s = re.sub(r"`?(?:~|/)[\w./~-]{3,}`?", "<경로>", s)
    s = re.sub(r"(?:<경로>[\s,·]*){2,}", "<경로> ", s)   # 경로 나열은 하나로
    s = re.sub(r"^(아래는|다음은)\s*", "", s)
    return s[:40] or prompt[:40]


def first_line(s: str, n: int = 76) -> str:
    line = next((x for x in s.splitlines() if x.strip()), "")
    line = " ".join(line.split())
    return line[:n] + ("…" if len(line) > n else "")


def main() -> None:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--log")
    ap.add_argument("--since", metavar="마커파일")
    ap.add_argument("--lookback-hours", type=float, default=72.0,
                    help="최근 N시간 안의 세션을 전부 (기본 72, 실물 CLI와 같다)")
    ap.add_argument("--this-session", action="store_true", help="지금 세션 하나만 본다")
    ap.add_argument("--all", action="store_true", help="프로젝트를 가리지 않는다")
    ap.add_argument("--top", type=int, default=5)
    a = ap.parse_args()

    since = since_from(a.since) if a.since else None
    if a.this_session or a.log or a.since:
        paths = [find_log(a.log, since)]
    else:
        paths = logs_in_window(a.lookback_hours, a.all)
        if not paths:
            sys.exit(
                f"최근 {a.lookback_hours:g}시간 안에 쓴 세션 로그가 없다.\n"
                "  기간을 늘리거나(--lookback-hours 168) 프로젝트 제한을 풀어라(--all)."
            )

    requests: list[str] = []
    delegated: list[str] = []
    touched: dict[str, int] = {}
    checks = 0

    for path in paths:
      with open(path, encoding="utf-8") as fh:
        for raw in fh:
            try:
                d = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if since:
                ts = d.get("timestamp")
                if not isinstance(ts, str) or ts < since:
                    continue
            msg = d.get("message") or {}
            content = msg.get("content")

            # 사람이 실제로 요청한 것 (슬래시 커맨드·시스템 블록은 뺀다)
            if msg.get("role") == "user":
                texts = []
                if isinstance(content, str):
                    texts = [content]
                elif isinstance(content, list):
                    texts = [i["text"] for i in content if isinstance(i, dict) and i.get("type") == "text"]
                for t in texts:
                    if t.strip() and not NOISE.match(t):
                        requests.append(first_line(t))

            if not isinstance(content, list):
                continue
            for item in content:
                if not (isinstance(item, dict) and item.get("type") == "tool_use"):
                    continue
                name = item.get("name", "?")
                inp = item.get("input") or {}
                if name in DELEGATES:
                    # 원본을 그대로 담는다. 먼저 자르면 긴 경로가 문장을 삼켜 그룹핑이 무너진다.
                    delegated.append(str(inp.get("prompt") or inp.get("description") or ""))
                key = WRITERS.get(name)
                if key and isinstance(inp.get(key), str):
                    base = os.path.basename(inp[key])
                    touched[base] = touched.get(base, 0) + 1
                if name == "Bash":
                    cmd = inp.get("command", "")
                    if re.search(r"\b(check|verify|grade|test|pytest)\w*\.py\b|--trace|loop_view", cmd):
                        checks += 1

    scope = f" ({a.since} 이후)" if a.since else ""
    if len(paths) == 1:
        print(f"{BOLD}harvest{RESET}  {paths[0]}{scope}")
    else:
        span = f"최근 {a.lookback_hours:g}시간" + ("" if not a.all else ", 전 프로젝트")
        print(f"{BOLD}harvest{RESET}  세션 {len(paths)}개 ({span})")
        for p in paths[-3:]:
            print(f"{DIM}  … {os.path.basename(p)[:8]}  {time.strftime('%m-%d %H:%M', time.localtime(os.path.getmtime(p)))}{RESET}")
    print(f"{DIM}요청 {len(requests)}건 · 위임 {len(delegated)}건 · 산출물 편집 {sum(touched.values())}회 · 검증 실행 {checks}회{RESET}\n")

    print(f"{BOLD}mine 1: 반복해서 손댄 산출물{RESET} {DIM}(여러 번 고쳤다면 그만큼 다시 하는 일이다){RESET}")
    ranked = sorted(touched.items(), key=lambda kv: kv[1], reverse=True)[: a.top]
    if not ranked:
        print("  (없음)")
    for f, n in ranked:
        bar = "█" * min(n, 24)
        print(f"  {CYAN}{f:<24}{RESET} {GREEN}{bar}{RESET} {n}회")

    if delegated:
        # 같은 과업을 여러 번 맡겼으면 묶어서 빈도로 보여준다. 그게 "반복 과업"의 신호다.
        groups: dict[str, int] = {}
        for p in delegated:
            key = task_key(p)
            groups[key] = groups.get(key, 0) + 1
        print(f"\n{BOLD}mine 2: 서브에이전트에 맡긴 과업{RESET} {DIM}(같은 과업은 묶었다){RESET}")
        for p, n in sorted(groups.items(), key=lambda kv: kv[1], reverse=True)[: a.top]:
            mark = f"{GREEN}{n}회{RESET}" if n > 1 else f"{DIM}1회{RESET}"
            print(f"  {YELLOW}-{RESET} {p}…  {mark}")

    if requests:
        print(f"\n{BOLD}mine 3: 사람이 직접 요청한 것{RESET}")
        for r in requests[: a.top]:
            print(f"  {DIM}-{RESET} {r}")

    print(f"\n{DIM}이 목록에서 '내일도 또 할 일'을 하나 고르면 그것이 replay 대상이다.{RESET}")


if __name__ == "__main__":
    main()
