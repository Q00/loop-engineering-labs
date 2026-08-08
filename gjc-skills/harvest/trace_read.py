#!/usr/bin/env python3
"""trace_read.py: 2강에서 본 그 세션 로그(tool call 기록)를 루프의 재료로 읽는다.

2강은 이 파일이 쌓이는 것을 관찰했고, 3·4·5강은 여기서 근거를 꺼내 쓴다.

사용법:
    python3 trace_read.py                      # 최근 tool call 12개
    python3 trace_read.py --tail 20            # 최근 20개
    python3 trace_read.py --touched            # 건드린 파일 목록
    python3 trace_read.py --thinking           # 그 구간의 사고 요약 (원본 사고가 아니라 요약본)
    python3 trace_read.py --read-check app.log # 그 파일을 실제로 읽었는지 판정 (종료코드 0/1)
    python3 trace_read.py --since mark.txt ... # 그 파일이 만들어진 뒤의 기록만 본다
    python3 trace_read.py --log <경로>         # 세션 로그 직접 지정

주의 두 가지:
1. 세션 로그는 세션 전체를 누적한다. 한 STEP의 행동만 보려면 시작 직전에
   `touch mark.txt`로 마커를 만들고 `--since mark.txt`를 붙인다.
   그러지 않으면 앞 STEP(또는 앞 강의)에서 읽은 기록이 섞인다.
2. **읽기 명령은 읽기 명령 자체로 시작해야 기록에 남는다.** 앞에 뭘 붙인
   `time grep …`·`LC_ALL=C grep …`·`xargs grep …`은 래퍼를 건너뛰고 인식하지만,
   그 밖의 형태(함수·별칭·스크립트 안에서 읽기)는 못 본다. 실제로 읽었는데
   "안 읽었다"가 나오면 이 경우다.
   한 Bash 호출 안에서 읽고 바로 검증하는 것은 대체로 된다(기록 flush가 0.05초
   수준이라 검문에 도달하기 전에 쓰인다). 다만 확실히 하려면 호출을 나눈다.

세션 로그를 못 찾으면 종료코드 2와 함께 이유를 출력한다 (강의장에서 원인을 바로 알 수 있게).
stdlib 전용.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

# 파일을 여는 성격의 tool과, 그 인자에서 경로가 나오는 자리
READERS = {"Read": ("file_path",), "read": ("path",), "Grep": ("path", "glob"), "search": ("paths", "pattern"), "Glob": ("path",), "find": ("paths",), "NotebookRead": ("notebook_path",)}

# Bash 안에서 "그 파일을 실제로 열었다"고 인정할 명령. python3 같은 실행기는 제외한다.
# 검문 스크립트를 돌리는 명령줄에 파일명이 있다고 읽은 것은 아니기 때문이다(자기 참조 방지).
READ_CMDS = {"cat", "head", "tail", "grep", "egrep", "rg", "less", "wc", "awk", "sed", "jq", "sort", "uniq", "diff", "nl"}

# 실제 명령 앞에 흔히 붙는 것들. 건너뛰고 다음 단어를 명령으로 본다.
# (`time grep …`, `LC_ALL=C grep …`을 "안 읽었다"로 판정하던 문제)
WRAPPERS = {"time", "env", "nice", "nohup", "sudo", "command", "xargs", "\\"}


def scan_meta(path: str, since_iso: str | None = None) -> tuple[set[str], int]:
    """로그를 훑어 (등장한 cwd 집합, since 이후 tool call 개수)를 빠르게 얻는다."""
    cwds: set[str] = set()
    n = 0
    try:
        with open(path, encoding="utf-8") as fh:
            for raw in fh:
                has_call = '"tool_use"' in raw or '"toolCall"' in raw
                if not has_call and '"cwd"' not in raw:
                    continue
                try:
                    d = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                c = d.get("cwd")
                if isinstance(c, str):
                    cwds.add(c)
                if has_call:
                    ts = d.get("timestamp")
                    if since_iso and (not isinstance(ts, str) or ts < since_iso):
                        continue
                    n += 1
    except OSError:
        pass
    return cwds, n


def find_log(explicit: str | None, since_iso: str | None = None) -> str:
    """세션 로그를 찾는다.

    폴더 이름만으로는 못 찾는다(세션 시작 폴더 기준이라 cd 후엔 어긋난다).
    mtime 최신 하나를 집는 것도 안 된다. 강사가 창을 두 개 열어 두면 남의 로그를
    집어서 "아무것도 안 읽었다"는 거짓 실패가 나온다. 무대에서 제일 고약한 실패다.

    그래서 이렇게 고른다.
      1. 로그에 기록된 cwd가 지금 작업 폴더와 겹치는 것만 후보로
      2. 그 후보 중 **마커(since) 이후 tool call이 가장 많은** 로그를 고른다
      3. cwd가 겹치는 게 없으면 tool call이 있는 최신 로그로 폴백하고 경고한다
    """
    if explicit:
        if not os.path.exists(explicit):
            sys.exit(f"지정한 세션 로그가 없다: {explicit}")
        return explicit
    files = sorted(
        glob.glob(os.path.expanduser("~/.gjc/agent/sessions/*/*.jsonl"))
        + glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl"))
        + glob.glob(os.path.expanduser("~/.codex/sessions/*/*.jsonl")),
        key=os.path.getmtime,
        reverse=True,
    )
    if not files:
        print("세션 로그를 찾지 못했다 (~/.gjc/agent/sessions, ~/.claude/projects, ~/.codex/sessions 모두 없음).", file=sys.stderr)
        print("Gajae Code(또는 Claude Code / Codex)로 대화를 한 번 한 뒤 다시 실행한다.", file=sys.stderr)
        sys.exit(2)

    here = os.path.realpath(os.getcwd())
    best: tuple[int, str] | None = None
    fallback = None
    for path in files[:20]:  # 최근 20개만 본다 (전수 스캔은 느리다)
        cwds, ncalls = scan_meta(path, since_iso)
        _, total = (cwds, ncalls) if since_iso is None else scan_meta(path)
        if total == 0:
            continue  # /clear만 한 빈 세션은 후보에서 뺀다
        if fallback is None:
            fallback = path
        matched = any(
            here == os.path.realpath(c)
            or here.startswith(os.path.realpath(c) + os.sep)
            or os.path.realpath(c).startswith(here + os.sep)
            for c in cwds
        )
        if matched and (best is None or ncalls > best[0]):
            best = (ncalls, path)
    if best:
        return best[1]
    if fallback:
        print(
            f"{DIM}(지금 폴더와 맞는 세션 로그를 못 찾아 최근 로그를 쓴다. "
            f"엉뚱하면 --log <경로>로 지정한다.){RESET}",
            file=sys.stderr,
        )
        return fallback
    return files[0]


def load_calls(path: str, since_iso: str | None = None) -> list[tuple[str, dict]]:
    """(tool 이름, input) 목록을 등장 순서대로. since_iso 이후 기록만 볼 수도 있다."""
    calls: list[tuple[str, dict]] = []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            try:
                d = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if since_iso:
                ts = d.get("timestamp")
                if not isinstance(ts, str) or ts < since_iso:
                    continue
            content = (d.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for item in content:
                if not isinstance(item, dict):
                    continue
                # Claude Code: {"type":"tool_use","name":..,"input":{..}}
                # Gajae Code:  {"type":"toolCall","name":..,"arguments":{..}}
                if item.get("type") in ("tool_use", "toolCall"):
                    inp = item.get("input") or item.get("arguments") or {}
                    calls.append((item.get("name", "?"), inp))
    return calls


def load_thinking(path: str, since_iso: str | None = None) -> tuple[list[str], int]:
    """(사고 요약 텍스트 목록, 사고 블록 총 개수)를 등장 순서대로.

    블록은 있는데 텍스트가 전부 비어 있으면 사고 요약이 꺼진 것이다
    (settings.json의 showThinkingSummaries). 그 구분이 필요해서 개수를 같이 돌려준다.
    돌려주는 것은 모델이 스스로 요약한 사고이지 원본 사고가 아니다.
    """
    texts: list[str] = []
    total = 0
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            if '"thinking"' not in raw:
                continue
            try:
                d = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if since_iso:
                ts = d.get("timestamp")
                if not isinstance(ts, str) or ts < since_iso:
                    continue
            content = (d.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for item in content:
                if isinstance(item, dict) and item.get("type") == "thinking":
                    total += 1
                    t = item.get("thinking") or ""
                    if t.strip():
                        texts.append(t)
    return texts, total


def since_from(marker: str) -> str:
    """마커 파일의 mtime을 세션 로그와 같은 형식(UTC ISO Z)으로."""
    if not os.path.exists(marker):
        sys.exit(f"마커 파일이 없다: {marker}  (STEP 시작 전에 `touch {marker}`)")
    import datetime as _dt

    t = _dt.datetime.fromtimestamp(os.path.getmtime(marker), _dt.timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def brief(name: str, inp: dict) -> str:
    for key in ("file_path", "path", "command", "pattern", "notebook_path", "prompt", "description"):
        val = inp.get(key)
        if isinstance(val, str) and val.strip():
            one = " ".join(val.split())
            return one[:64] + ("…" if len(one) > 64 else "")
    return ""


def touched_files(calls: list[tuple[str, dict]]) -> dict[str, list[str]]:
    """파일 이름 → 그 파일을 건드린 tool 이름들. Bash 명령 안의 경로도 훑는다."""
    hits: dict[str, list[str]] = {}
    for name, inp in calls:
        paths: list[str] = []
        for key in READERS.get(name, ()):
            v = inp.get(key)
            if isinstance(v, str) and v.strip():
                paths.append(v)
        if name in ("Bash", "bash"):
            # 파이프·연결자로 쪼갠 뒤, 읽기 명령으로 시작하는 구간의 인자만 인정
            for seg in re.split(r"\||;|&&|\n", inp.get("command", "")):
                words = seg.replace("(", " ").split()
                # 환경변수 대입과 래퍼(time·env 등)를 건너뛰고 실제 명령을 찾는다
                i = 0
                while i < len(words) and (
                    re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", words[i])
                    or os.path.basename(words[i]) in WRAPPERS
                ):
                    i += 1
                if i >= len(words):
                    continue
                head = os.path.basename(words[i])
                if head not in READ_CMDS:
                    continue
                for tok in words[i + 1 :]:
                    if "*" in tok or "?" in tok:  # glob 패턴은 실제 파일이 아니다
                        continue
                    m = re.search(r"([A-Za-z0-9][\w.-]*\.(?:log|jsonl|md|py|json|txt))\b", tok)
                    if m:
                        paths.append(m.group(1))
        for p in paths:
            base = os.path.basename(p.rstrip("/"))
            if not base or base.startswith("."):
                continue
            hits.setdefault(base, [])
            if name not in hits[base]:
                hits[base].append(name)
    return hits


def main() -> None:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--tail", type=int, default=12)
    ap.add_argument("--touched", action="store_true")
    ap.add_argument("--thinking", action="store_true")
    ap.add_argument("--read-check", metavar="파일명")
    ap.add_argument("--since", metavar="마커파일")
    ap.add_argument("--log")
    a = ap.parse_args()

    since = since_from(a.since) if a.since else None
    path = find_log(a.log, since)
    calls = load_calls(path, since)
    hits = touched_files(calls)

    scope = f" ({a.since} 이후)" if a.since else ""

    if a.read_check:
        target = os.path.basename(a.read_check)
        used = hits.get(target)
        print(f"{BOLD}과정 검증: {target}을 실제로 읽었는가{scope}{RESET}")
        if used:
            print(f"  {GREEN}읽었다{RESET}  {DIM}({' · '.join(used)}){RESET}")
            sys.exit(0)
        print(f"  {RED}{target}을 연 tool call이 없다{RESET}")
        sys.exit(1)

    if a.thinking:
        texts, total = load_thinking(path, since)
        print(f"{BOLD}사고 요약{scope}{RESET}  {DIM}{path}{RESET}")
        print(f"{DIM}사고 블록 {total}개 중 텍스트가 있는 것 {len(texts)}개{RESET}\n")
        if total and not texts:
            print(f"  {RED}사고 요약이 꺼져 있다{RESET}  {DIM}(사고 요약 설정을 켜야 한다. "
                  f"Claude Code면 ~/.claude/settings.json의 showThinkingSummaries: true){RESET}")
            return
        for t in texts:
            one = " ".join(t.split())
            print(f"  {CYAN}·{RESET} {one[:200]}{'…' if len(one) > 200 else ''}")
        return

    print(f"{BOLD}세션 로그{RESET}  {path}")
    print(f"{DIM}tool call {len(calls)}개 기록됨{scope}{RESET}\n")
    if not calls:
        print(f"{RED}이 구간에 기록이 없다.{RESET} 기록이 안 남은 게 아니라 보통 둘 중 하나다:")
        print("  1. 세션 로그를 잘못 골랐다 (위 경로가 지금 세션인지 확인, 아니면 --log <경로>)")
        print("  2. 마커를 만든 뒤로 tool call이 정말 없었다 (읽기와 판독을 한 명령에 묶지 않았는지 확인)\n")

    if a.touched:
        print(f"{BOLD}이번 세션에서 건드린 파일{RESET}")
        if not hits:
            print("  (없음)")
        width = min(max((len(f) for f in hits), default=8), 30)
        for f, tools in sorted(hits.items()):
            disp = f if len(f) <= width else f[: width - 1] + "…"
            print(f"  {CYAN}{disp:<{width}}{RESET} {DIM}{' · '.join(tools)}{RESET}")
        return

    print(f"{BOLD}최근 tool call {min(a.tail, len(calls))}개{RESET}")
    for name, inp in calls[-a.tail:]:
        disp = name if len(name) <= 12 else name[:11] + "…"
        print(f"  {CYAN}{disp:<12}{RESET} {DIM}{brief(name, inp)}{RESET}")


if __name__ == "__main__":
    main()
