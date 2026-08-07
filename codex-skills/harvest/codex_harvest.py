#!/usr/bin/env python3
"""Codex 세션 기록에서 반복 업무를 캔다. 읽기 전용.

~/.codex/sessions 와 ~/.codex/archived_sessions 의 rollout *.jsonl을 읽어
반복해서 손댄 산출물, 도구로 시킨 일, 사람이 직접 친 요청을 빈도순으로 보여준다.
세션 파일은 절대 수정하지 않는다.

캐는 것은 여섯 갈래다. 코드 편집이 반복 업무의 한복판인 사람이 많으므로 그것부터 그대로 센다.
다만 거기서 멈추면 보고서·브라우저·데이터 조회처럼 파일을 안 남기는 일이 통째로 안 잡힌다.
    mine 1  반복해서 손댄 산출물        파일별 · 폴더별 · 종류별
    mine 2  서브에이전트에 맡긴 과업
    mine 3  사람이 직접 요청한 것        같은 요청은 묶어서 빈도로
    mine 4  도구로 시킨 일               브라우저·데이터·웹·커뮤니케이션·자주 친 명령
    mine 5  반복해서 부른 스킬/커맨드
    mine 6  세션별 한 줄 요약            언제 무슨 일을 했는가
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import Counter
from pathlib import Path

ROOTS = (
    Path.home() / ".codex" / "sessions",
    Path.home() / ".codex" / "archived_sessions",
)

PATCH_FILE_RE = re.compile(r"\*\*\* (?:Update|Add) File: ([^\s\\\"]+)")
CMD_RE = re.compile(r"cmd:\s*\"((?:[^\"\\]|\\.){2,400})")
CMD_NAME = re.compile(r"<command-name>\s*/?([\w:.-]+)\s*</command-name>")
# 슬래시 커맨드. `/Users/...` 같은 경로가 아니어야 한다(뒤에 / 가 오면 경로다).
SLASH = re.compile(r"^\s*/([a-zA-Z][\w:.-]{1,})(?![\w/])")

NOISE_PREFIX = ("<", "# files mentioned", "[system", "[image", "[request interrupted")
# 업무가 아니라 대화 추임새. 빈도가 높아도 "반복 업무"가 아니다.
FILLER = re.compile(
    r"^(ㄱ+|ㅇ+|ok|okay|yes|no|go|continue|keep going|next|계속|계속해|진행|진행해|"
    r"응|어|네|아니|그래|맞아|좋아|이거|저거|그거|다시|해봐|해줘|"
    r"step\s*\d+|\d+\s*단계)[.!?~\s]*$", re.I)

# 파일 확장자 -> 일의 종류. 코드는 코드대로 세고, 그 밖의 산출물도 갈래를 나눠 센다.
KIND_BY_EXT = {
    "문서·보고서": {".md", ".txt", ".rst", ".docx", ".doc", ".pdf", ".pptx", ".key", ".tex"},
    "데이터·표": {".csv", ".tsv", ".xlsx", ".parquet", ".sql", ".ipynb"},
    "설정·인프라": {".yaml", ".yml", ".toml", ".ini", ".env", ".tf", ".dockerfile", ".conf"},
    "웹·디자인": {".html", ".css", ".scss", ".svg", ".excalidraw", ".fig"},
}
CODE_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".kt", ".rb",
            ".c", ".cc", ".cpp", ".h", ".swift", ".php", ".sh", ".zsh", ".lua", ".scala"}

# 명령어 -> 일의 갈래. Codex는 대부분의 일을 셸로 시키므로 여기서 갈래가 갈린다.
CMD_KINDS = (
    ("브라우저·컴퓨터 제어", ("playwright", "puppeteer", "chromedriver", "selenium",
                             "osascript", "screencapture", "cliclick", "open -a")),
    ("웹 조사", ("curl ", "wget ", "httpie", "lynx ")),
    ("데이터 조회", ("psql", "mysql", "clickhouse", "bq ", "duckdb", "sqlite3", "mongo")),
    ("커뮤니케이션", ("slack", "sendmail", "gh issue", "gh pr comment")),
    ("저장소·배포", ("git ", "gh ", "docker", "kubectl", "terraform", "vercel",
                     "gcloud", "aws ")),
    ("테스트·검증", ("pytest", "jest", "vitest", "npm test", "go test", "cargo test",
                     "ruff", "mypy", "eslint")),
)

GREEN, CYAN, YELLOW, MAGENTA = "\033[32m", "\033[36m", "\033[33m", "\033[35m"
DIM, BOLD, RESET = "\033[2m", "\033[1m", "\033[0m"


def clip(s: str, n: int) -> str:
    s = " ".join(str(s).split())
    return s[:n] + ("…" if len(s) > n else "")


def bar(n: int, top: int, width: int = 24) -> str:
    """최대값에 비례한 막대. 상한으로 자르면 1위와 5위가 같아 보인다."""
    return "█" * max(1, round(n / top * width)) if top > 0 else ""


def file_kind(name: str) -> str:
    ext = os.path.splitext(name)[1].lower()
    if ext in CODE_EXT:
        return "코드"
    for kind, exts in KIND_BY_EXT.items():
        if ext in exts:
            return kind
    return "기타"


def cmd_kind(cmd: str) -> str | None:
    low = cmd.lower()
    for kind, needles in CMD_KINDS:
        if any(n in low for n in needles):
            return kind
    return None


def cmd_head(cmd: str) -> str | None:
    """명령의 머리 낱말. `cd x && git status`는 git으로 센다."""
    for part in re.split(r"&&|\||;", cmd):
        toks = part.strip().split()
        if not toks:
            continue
        head = os.path.basename(toks[0])
        if head in ("cd", "export", "source", "sudo", "time", "env"):
            continue
        if re.fullmatch(r"[\w.-]{2,}", head):
            return head
    return None


def normalize(text: str) -> str:
    """같은 일을 한 문장으로 묶기 위한 정규화. **자르지 않는다.**

    앞 N자를 키로 쓰면 서두가 같은 다른 일이 한 덩어리가 되어
    "무엇을 반복했는가"가 흐려진다. 자르는 건 인쇄할 때만 한다.
    """
    s = " ".join(str(text).split())
    s = re.sub(r"`?(?:~|\.{0,2}/)[\w./~@-]{3,}`?", "<경로>", s)
    s = re.sub(r"(?:<경로>[\s,·]*){2,}", "<경로> ", s)
    s = re.sub(r"\b\d[\d,._-]*\b", "<수>", s)
    return s.strip()


def lineage_root(meta: dict, parent_of: dict) -> str:
    """이 rollout이 속한 대화 계보의 뿌리 id.

    Codex는 fork와 서브에이전트 스레드에 부모의 대화 기록을 통째로 복사해 새 rollout으로
    남기고, **복사하면서 timestamp까지 새로 찍는다.** 그래서 시각으로는 중복이 안 걸린다.
    한 번 친 요청이 계보 파일 수만큼 부풀어 "22회 반복"으로 보이는 것이 그 탓이다.
    계보의 뿌리까지 거슬러 올라가, 같은 뿌리 안에서는 같은 요청을 한 번만 센다.
    """
    cur = meta.get("id") or ""
    seen_ids = set()
    while cur in parent_of and parent_of[cur] and cur not in seen_ids:
        seen_ids.add(cur)
        cur = parent_of[cur]
    return cur


def read_meta(path: Path) -> dict:
    """첫 줄의 session_meta만 읽는다. 없으면 빈 것으로 본다."""
    try:
        with path.open(encoding="utf-8") as fh:
            for raw in fh:
                try:
                    row = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if row.get("type") == "session_meta":
                    return row.get("payload") or {}
                return {}
    except OSError:
        pass
    return {}


def meta_parent(meta: dict) -> str | None:
    src = meta.get("source")
    if isinstance(src, dict):
        spawn = (src.get("subagent") or {}).get("thread_spawn") or {}
        if spawn.get("parent_thread_id"):
            return spawn["parent_thread_id"]
    return meta.get("forked_from_id") or meta.get("parent_thread_id")


def scan(path: Path, seen: set, root: str) -> dict:
    """세션 하나를 캔다.

    `seen`은 중복을 걷어내는 자리다. 도구 호출은 (시각, 종류, 내용)으로,
    사람의 요청과 커맨드는 (계보 뿌리, 내용)으로 한 번만 센다.
    """
    s = {"path": path, "mtime": path.stat().st_mtime,
         "requests": [], "delegated": [], "edits": Counter(), "dirs": Counter(),
         "kinds": Counter(), "cmds": Counter(), "cmdkinds": Counter(),
         "commands": Counter(), "exec_total": 0, "edit_total": 0}
    for raw in path.open(encoding="utf-8"):
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        p = row.get("payload") or {}
        t, pt = row.get("type"), p.get("type")
        body = p.get("message") or p.get("arguments") or p.get("input") or ""
        mark = (row.get("timestamp"), pt, p.get("name"), hash(str(body)))
        if mark in seen:
            continue
        seen.add(mark)

        if t == "event_msg" and pt == "user_message":
            msg = " ".join(str(p.get("message") or "").split())
            if ("req", root, msg) in seen:
                continue
            seen.add(("req", root, msg))
            for m in CMD_NAME.finditer(msg):
                s["commands"][m.group(1)] += 1
            m = SLASH.match(msg)
            if m:
                s["commands"][m.group(1)] += 1
            low = msg.lower()
            if (not msg or low.startswith(NOISE_PREFIX)
                    or len(msg) < 8 or FILLER.match(msg)):
                continue
            s["requests"].append((normalize(msg), msg))

        elif t == "event_msg" and pt == "sub_agent_activity":
            s["delegated"].append("")

        elif pt in ("function_call", "custom_tool_call"):
            name = p.get("name")
            text = str(p.get("arguments") or p.get("input") or "")
            if name == "spawn_agent":
                s["delegated"].append(text)
            for f in PATCH_FILE_RE.findall(text):
                base = os.path.basename(f)
                s["edits"][base] += 1
                s["kinds"][file_kind(base)] += 1
                s["edit_total"] += 1
                parent = os.path.basename(os.path.dirname(f))
                grand = os.path.basename(os.path.dirname(os.path.dirname(f)))
                if parent:
                    s["dirs"][os.path.join(grand, parent) if grand else parent] += 1
            for c in CMD_RE.findall(text):
                c = c.replace('\\"', '"')
                s["exec_total"] += 1
                head = cmd_head(c)
                if head:
                    s["cmds"][head] += 1
                kind = cmd_kind(c)
                if kind:
                    s["cmdkinds"][kind] += 1
    return s


def digest(s: dict) -> str:
    """세션 하나를 한 줄로. '언제 무슨 일을 했는가'를 사람이 알아보게 만든다."""
    when = time.strftime("%m-%d %H:%M", time.localtime(s["mtime"]))
    head = s["requests"][0][1] if s["requests"] else "(사람 요청 없음)"
    bits = []
    if s["kinds"]:
        bits.append(" ".join("%s %d" % kv for kv in s["kinds"].most_common(3)))
    if s["cmdkinds"]:
        bits.append(" ".join("%s %d" % kv for kv in s["cmdkinds"].most_common(2)))
    if s["delegated"]:
        bits.append("위임 %d" % len(s["delegated"]))
    tail = ("  " + DIM + " · ".join(bits) + RESET) if bits else ""
    return "  %s%s%s  %s%s" % (DIM, when, RESET, clip(head, 62), tail)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lookback-hours", type=int, default=168)
    ap.add_argument("--root", action="append", type=Path, default=None)
    ap.add_argument("--top", type=int, default=8)
    args = ap.parse_args()

    roots = tuple(args.root) if args.root else ROOTS
    cutoff = time.time() - args.lookback_hours * 3600
    paths = sorted({p for r in roots if r.exists() for p in r.rglob("*.jsonl")
                    if p.stat().st_mtime >= cutoff})

    # 계보를 먼저 그린다. 자식이 부모보다 먼저 나올 수 있어 두 번에 나눠 읽는다.
    metas = {p: read_meta(p) for p in paths}
    parent_of = {}
    for m in metas.values():
        if m.get("id"):
            parent_of[m["id"]] = meta_parent(m)

    # 이름이 생성 시각이라 정렬하면 원본이 먼저 온다. 복사본은 뒤에서 걷힌다.
    seen: set = set()
    sessions = []
    for path in paths:
        root = lineage_root(metas.get(path) or {}, parent_of) or str(path)
        try:
            s = scan(path, seen, root)
        except OSError:
            continue
        if s["requests"] or s["edit_total"] or s["exec_total"]:
            sessions.append(s)

    if not sessions:
        print(f"최근 {args.lookback_hours}시간 안에 쓴 Codex 세션이 없다. "
              f"기간을 늘려라 (--lookback-hours 336).")
        return 0

    edits, dirs, kinds = Counter(), Counter(), Counter()
    cmds, cmdkinds, commands = Counter(), Counter(), Counter()
    requests: dict[str, list] = {}
    tasks: Counter[str] = Counter()
    edit_total = exec_total = deleg = 0
    for s in sessions:
        edits += s["edits"]
        dirs += s["dirs"]
        kinds += s["kinds"]
        cmds += s["cmds"]
        cmdkinds += s["cmdkinds"]
        commands += s["commands"]
        edit_total += s["edit_total"]
        exec_total += s["exec_total"]
        deleg += len(s["delegated"])
        for norm, shown in s["requests"]:
            requests.setdefault(norm, []).append(shown)
        for d in s["delegated"]:
            if d.strip():
                tasks[normalize(d)] += 1

    print(f"{BOLD}harvest{RESET}  세션 {len(sessions)}개 "
          f"(최근 {args.lookback_hours}시간, Codex)")
    print(f"{DIM}요청 {sum(len(v) for v in requests.values())}건 · 위임 {deleg}건 · "
          f"산출물 편집 {edit_total}회 · 명령 실행 {exec_total}회{RESET}")

    if kinds:
        print(f"\n{BOLD}무엇을 만들었나{RESET} {DIM}(편집한 파일의 종류){RESET}")
        hi = kinds.most_common(1)[0][1]
        for k, n in kinds.most_common(9):
            print(f"  {CYAN}{k:<14}{RESET} {GREEN}{bar(n, hi)}{RESET} {n}회")

    print(f"\n{BOLD}mine 1: 반복해서 손댄 산출물{RESET} "
          f"{DIM}(여러 번 고쳤다면 그만큼 다시 하는 일이다){RESET}")
    top = edits.most_common(args.top)
    if not top:
        print("  (apply_patch 기록 없음)")
    hi = top[0][1] if top else 0
    for name, n in top:
        print(f"  {CYAN}{clip(name, 28):<28}{RESET} {GREEN}{bar(n, hi)}{RESET} "
              f"{n}회 {DIM}{file_kind(name)}{RESET}")
    if dirs:
        line = "  ".join(f"{d} {n}" for d, n in dirs.most_common(6))
        print(f"  {DIM}자주 손댄 폴더: {line}{RESET}")

    if tasks:
        print(f"\n{BOLD}mine 2: 서브에이전트에 맡긴 과업{RESET} {DIM}(같은 과업은 묶었다){RESET}")
        for p, n in tasks.most_common(args.top):
            mark = f"{GREEN}{n}회{RESET}" if n > 1 else f"{DIM}1회{RESET}"
            print(f"  {YELLOW}-{RESET} {clip(p, 84)}  {mark}")

    if requests:
        print(f"\n{BOLD}mine 3: 사람이 직접 요청한 것{RESET} {DIM}(같은 요청은 묶었다){RESET}")
        ranked = sorted(requests.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        for _, shown in ranked[: args.top]:
            n = len(shown)
            mark = f"{GREEN}{n}회{RESET}" if n > 1 else f"{DIM}1회{RESET}"
            print(f"  {DIM}-{RESET} {clip(shown[0], 84)}  {mark}")

    if cmdkinds or cmds:
        print(f"\n{BOLD}mine 4: 도구로 시킨 일{RESET} "
              f"{DIM}(파일을 안 남기는 반복 — 브라우저·데이터·웹·명령){RESET}")
        for k, n in cmdkinds.most_common(args.top):
            print(f"  {MAGENTA}{k:<18}{RESET} {n:>4}회")
        if cmds:
            line = "  ".join(f"{c} {n}" for c, n in cmds.most_common(8))
            print(f"  {MAGENTA}{'자주 친 명령':<18}{RESET} {DIM}{line}{RESET}")

    if commands:
        print(f"\n{BOLD}mine 5: 반복해서 부른 스킬·커맨드{RESET}")
        for c, n in commands.most_common(args.top):
            mark = f"{GREEN}{n}회{RESET}" if n > 1 else f"{DIM}1회{RESET}"
            print(f"  {YELLOW}/{c}{RESET}  {mark}")

    if len(sessions) > 1:
        print(f"\n{BOLD}mine 6: 세션별로 무슨 일을 했나{RESET} {DIM}(최근 순){RESET}")
        for s in sorted(sessions, key=lambda x: -x["mtime"])[:12]:
            print(digest(s))

    print(f"\n{DIM}이 목록에서 '다음 주에도 또 할 일'을 하나 고르면 그것이 루프 후보다.{RESET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
