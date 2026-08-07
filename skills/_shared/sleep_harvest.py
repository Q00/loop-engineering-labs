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
    python3 sleep_harvest.py --top 8             # 각 mine의 상위 N개
    python3 sleep_harvest.py --json              # 기계가 읽을 형태로

기본이 72시간인 이유: 자는 동안 도는 루프는 "지금 이 대화"가 아니라 **지난 며칠의 일**을
재료로 삼는다. 실물 `skillopt-sleep`의 `--lookback-hours` 기본값도 72다. 덕분에 실습을
새 창에서 시작해도, 어제 다른 창에서 한 일이 그대로 잡힌다.
"이번 주에 세 번 이상 반복한 일"도 기억으로 찾을 게 아니라 `--lookback-hours 168`로 찾는다.

캐는 것은 여섯 갈래다. 코드 편집이 반복 업무의 한복판인 사람이 많으므로 그것부터 그대로 센다.
다만 거기서 멈추면 보고서·브라우저·데이터 조회처럼 파일을 안 남기는 일이 통째로 안 잡힌다.
    mine 1  반복해서 손댄 산출물        파일별 · 폴더별 · 종류별
    mine 2  서브에이전트에 맡긴 과업
    mine 3  사람이 직접 요청한 것        같은 요청은 묶어서 빈도로
    mine 4  도구로 시킨 일               브라우저·컴퓨터유즈·데이터·커뮤니케이션·웹·명령
    mine 5  반복해서 부른 스킬/커맨드
    mine 6  세션별 한 줄 요약            언제 무슨 일을 했는가

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


GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

# 산출물로 볼 tool과 경로가 담긴 자리
WRITERS = {"Write": "file_path", "Edit": "file_path", "NotebookEdit": "notebook_path"}
DELEGATES = {"Task", "Agent"}

# 파일 확장자 -> 일의 종류. 코드는 코드대로 세고, 그 밖의 산출물도 갈래를 나눠 센다.
KIND_BY_EXT = {
    "문서·보고서": {".md", ".txt", ".rst", ".docx", ".doc", ".pdf", ".pptx", ".key", ".tex"},
    "데이터·표": {".csv", ".tsv", ".xlsx", ".parquet", ".sql", ".ipynb"},
    "설정·인프라": {".yaml", ".yml", ".toml", ".ini", ".env", ".tf", ".dockerfile", ".conf"},
    "웹·디자인": {".html", ".css", ".scss", ".svg", ".excalidraw", ".fig"},
}
CODE_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".kt", ".rb",
            ".c", ".cc", ".cpp", ".h", ".swift", ".php", ".sh", ".zsh", ".lua", ".scala"}

# 도구 이름 -> 일의 갈래. MCP 도구는 이름에 서버명이 박혀 있어 부분 일치로 잡힌다.
TOOL_KINDS = (
    ("브라우저·컴퓨터 제어", ("playwright", "puppeteer", "browser", "computer_use",
                             "computer-use", "chrome", "selenium", "screenshot",
                             "click", "navigate", "keyboard", "mouse")),
    ("웹 조사", ("websearch", "webfetch", "tavily", "exa", "perplexity", "fetch_url",
                 "crawl", "scrape")),
    ("데이터 조회", ("clickhouse", "posthog", "bigquery", "snowflake", "mongo",
                     "postgres", "mysql", "redis", "run_query", "sql")),
    ("커뮤니케이션", ("slack", "gmail", "mail", "channeltalk", "linear", "jira",
                      "notion", "calendar", "discord", "teams")),
    ("디자인·문서 도구", ("figma", "canva", "drive", "docs", "sheets", "confluence")),
    ("저장소·배포", ("github", "gitlab", "vercel", "coolify", "docker", "kubectl", "aws")),
)

# 사람의 요청이 아닌 것 (시스템이 끼워 넣은 블록)
NOISE = re.compile(
    r"^\s*(<(task-notification|local-command|system-reminder)"
    r"|Another Claude session sent a message|Base directory for this skill"
    r"|\[Image[: ]|\[Request interrupted|\[Pasted text|\[제안|A session-scoped)"
)
CMD_NAME = re.compile(r"<command-name>\s*/?([\w:.-]+)\s*</command-name>")
CMD_BLOCK = re.compile(r"^\s*<command-")
# 업무가 아니라 대화 추임새. 빈도가 높아도 "반복 업무"가 아니다.
FILLER = re.compile(
    r"^(ㄱ+|ㅇ+|ok|okay|yes|no|go|continue|keep going|next|계속|계속해|진행|진행해|"
    r"응|어|네|아니|그래|맞아|좋아|이거|저거|그거|다시|해봐|해줘|"
    r"step\s*[\d<>수]+|[\d<>수]+\s*단계)[.!?~\s]*$",
    re.I)


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


def normalize(text: str) -> str:
    """같은 일을 한 문장으로 묶기 위한 정규화.

    경로·숫자·따옴표 안 이름을 자리표시자로 바꾼다. 대상만 다른 같은 작업이 하나로 묶인다.
    **자르지 않는다.** 예전에는 앞 40자를 키로 썼는데, 그러면 서두가 같은 다른 일이
    한 덩어리가 되어 "무엇을 반복했는가"가 흐려졌다. 자르는 건 인쇄할 때만 한다.
    """
    s = " ".join(text.split())
    s = re.sub(r"`?(?:~|\.{0,2}/)[\w./~@-]{3,}`?", "<경로>", s)
    s = re.sub(r"(?:<경로>[\s,·]*){2,}", "<경로> ", s)
    s = re.sub(r"\b\d[\d,._-]*\b", "<수>", s)
    s = re.sub(r"^(아래는|다음은|자|그럼|이제)\s*", "", s)
    return s.strip()


def file_kind(name: str) -> str:
    ext = os.path.splitext(name)[1].lower()
    if ext in CODE_EXT:
        return "코드"
    for kind, exts in KIND_BY_EXT.items():
        if ext in exts:
            return kind
    return "기타"


def tool_kind(name: str) -> str | None:
    low = name.lower()
    for kind, needles in TOOL_KINDS:
        if any(n in low for n in needles):
            return kind
    return None


def clip(s: str, n: int) -> str:
    return s[:n] + ("…" if len(s) > n else "")


def first_line(s: str, n: int = 90) -> str:
    line = next((x for x in s.splitlines() if x.strip()), "")
    return clip(" ".join(line.split()), n)


def bar(n: int, top: int, width: int = 24) -> str:
    """최대값에 비례한 막대. 상한으로 자르면 1위와 5위가 같아 보인다."""
    if top <= 0:
        return ""
    return "\u2588" * max(1, round(n / top * width))


def bash_head(cmd: str) -> str | None:
    """Bash 명령의 머리 낱말. `cd x && git status`는 git으로 센다."""
    parts = re.split(r"&&|\||;", cmd)
    for part in parts:
        toks = part.strip().split()
        if not toks:
            continue
        head = os.path.basename(toks[0])
        if head in ("cd", "export", "source", "sudo", "time", "env"):
            continue
        if re.fullmatch(r"[\w.-]{2,}", head):
            return head
    return None


def mcp_server(name: str) -> str | None:
    """`mcp__slack-agent__slack_post_message` -> `slack-agent`."""
    if not name.startswith("mcp__"):
        return None
    rest = name[5:]
    return rest.split("__", 1)[0] or None


def bump(d: dict, k, n: int = 1) -> None:
    d[k] = d.get(k, 0) + n


def rank(d: dict, top: int) -> list:
    return sorted(d.items(), key=lambda kv: (-kv[1], str(kv[0])))[:top]


def scan(path: str, since: str | None) -> dict:
    """세션 하나에서 캘 것을 전부 캔다. 한 번만 읽는다."""
    s = {
        "path": path,
        "mtime": os.path.getmtime(path),
        "requests": [],        # (정규화, 원문 한 줄)
        "delegated": [],
        "touched": {},         # basename -> 횟수
        "dirs": {},            # 상위 폴더 -> 횟수
        "kinds": {},           # 일의 종류 -> 횟수
        "tools": {},           # 도구 이름 -> 횟수
        "toolkinds": {},       # 도구 갈래 -> 횟수
        "commands": {},        # /스킬 이름 -> 횟수
        "bash": {},            # 명령 머리 낱말 -> 횟수
        "servers": {},         # MCP 서버 -> 횟수
        "checks": 0,
    }
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

            if msg.get("role") == "user":
                texts = []
                if isinstance(content, str):
                    texts = [content]
                elif isinstance(content, list):
                    texts = [i["text"] for i in content
                             if isinstance(i, dict) and i.get("type") == "text"]
                for t in texts:
                    for m in CMD_NAME.finditer(t):
                        bump(s["commands"], m.group(1))
                    if not t.strip() or NOISE.match(t) or CMD_BLOCK.match(t):
                        continue
                    # 표시는 원문을 한 줄로 편 것. 첫 줄만 쓰면 "이거"처럼 무의미한
                    # 서두가 뒤의 본문을 가린다. 묶기는 정규화한 전문으로 한다.
                    flat = " ".join(t.split())
                    if len(flat) < 8 or FILLER.match(flat):
                        continue
                    s["requests"].append((normalize(t), flat))

            if not isinstance(content, list):
                continue
            for item in content:
                if not (isinstance(item, dict) and item.get("type") == "tool_use"):
                    continue
                name = item.get("name", "?")
                inp = item.get("input") or {}
                bump(s["tools"], name)
                kind = tool_kind(name)
                if kind:
                    bump(s["toolkinds"], kind)
                srv = mcp_server(name)
                if srv:
                    bump(s["servers"], srv)
                if name in DELEGATES:
                    # 원본을 그대로 담는다. 먼저 자르면 긴 경로가 문장을 삼켜 그룹핑이 무너진다.
                    s["delegated"].append(
                        str(inp.get("prompt") or inp.get("description") or ""))
                key = WRITERS.get(name)
                if key and isinstance(inp.get(key), str):
                    full = inp[key]
                    base = os.path.basename(full)
                    bump(s["touched"], base)
                    bump(s["kinds"], file_kind(base))
                    parent = os.path.basename(os.path.dirname(full))
                    grand = os.path.basename(os.path.dirname(os.path.dirname(full)))
                    if parent:
                        bump(s["dirs"], os.path.join(grand, parent) if grand else parent)
                if name in ("Skill", "SlashCommand"):
                    nm = inp.get("skill") or inp.get("command") or ""
                    if isinstance(nm, str) and nm.strip():
                        bump(s["commands"], nm.strip().lstrip("/").split()[0])
                if name == "Bash":
                    cmd = inp.get("command", "")
                    head = bash_head(cmd)
                    if head:
                        bump(s["bash"], head)
                    if re.search(r"\b(check|verify|grade|test|pytest)\w*\.py\b"
                                 r"|--trace|loop_view", cmd):
                        s["checks"] += 1
    return s


def merge(sessions: list[dict]) -> dict:
    m = {"requests": [], "delegated": [], "touched": {}, "dirs": {}, "kinds": {},
         "tools": {}, "toolkinds": {}, "commands": {}, "bash": {},
         "servers": {}, "checks": 0}
    for s in sessions:
        m["requests"] += s["requests"]
        m["delegated"] += s["delegated"]
        m["checks"] += s["checks"]
        for f in ("touched", "dirs", "kinds", "tools", "toolkinds", "commands",
                  "bash", "servers"):
            for k, v in s[f].items():
                bump(m[f], k, v)
    return m


def digest(s: dict) -> str:
    """세션 하나를 한 줄로. '언제 무슨 일을 했는가'를 사람이 알아보게 만든다."""
    when = time.strftime("%m-%d %H:%M", time.localtime(s["mtime"]))
    head = s["requests"][0][1] if s["requests"] else "(사람 요청 없음)"
    head = " ".join(head.split())
    bits = []
    if s["kinds"]:
        bits.append(" ".join("%s %d" % (k, n) for k, n in rank(s["kinds"], 3)))
    if s["toolkinds"]:
        bits.append(" ".join("%s %d" % (k, n) for k, n in rank(s["toolkinds"], 2)))
    if s["delegated"]:
        bits.append("위임 %d" % len(s["delegated"]))
    tail = ("  " + DIM + " · ".join(bits) + RESET) if bits else ""
    return "  %s%s%s  %s%s" % (DIM, when, RESET, clip(head, 62), tail)


def main() -> None:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--log")
    ap.add_argument("--since", metavar="마커파일")
    ap.add_argument("--lookback-hours", type=float, default=72.0,
                    help="최근 N시간 안의 세션을 전부 (기본 72, 실물 CLI와 같다)")
    ap.add_argument("--this-session", action="store_true", help="지금 세션 하나만 본다")
    ap.add_argument("--all", action="store_true", help="프로젝트를 가리지 않는다")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--json", action="store_true", help="기계가 읽을 형태로 낸다")
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

    sessions = [scan(p, since) for p in paths]
    m = merge(sessions)

    # 같은 요청은 묶는다. 예전에는 앞에서 5개를 그냥 잘라 보여줘 "잦은 것"이 아니었다.
    req_groups: dict[str, list] = {}
    for norm, shown in m["requests"]:
        req_groups.setdefault(norm, []).append(shown)
    req_ranked = sorted(req_groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    task_groups: dict[str, int] = {}
    for p in m["delegated"]:
        bump(task_groups, normalize(p))

    if a.json:
        print(json.dumps({
            "sessions": [{"path": s["path"], "mtime": s["mtime"],
                          "first_request": s["requests"][0][1] if s["requests"] else "",
                          "kinds": s["kinds"], "toolkinds": s["toolkinds"],
                          "delegated": len(s["delegated"])} for s in sessions],
            "touched": m["touched"], "dirs": m["dirs"], "kinds": m["kinds"],
            "toolkinds": m["toolkinds"], "tools": m["tools"],
            "commands": m["commands"], "bash": m["bash"],
            "servers": m["servers"],
            "requests": [{"text": v[0], "count": len(v)} for _, v in req_ranked],
            "delegated": [{"text": k, "count": n} for k, n in
                          sorted(task_groups.items(), key=lambda kv: -kv[1])],
        }, ensure_ascii=False, indent=1))
        return

    scope = f" ({a.since} 이후)" if a.since else ""
    if len(paths) == 1:
        print(f"{BOLD}harvest{RESET}  {paths[0]}{scope}")
    else:
        span = f"최근 {a.lookback_hours:g}시간" + ("" if not a.all else ", 전 프로젝트")
        print(f"{BOLD}harvest{RESET}  세션 {len(paths)}개 ({span})")
    print(f"{DIM}요청 {len(m['requests'])}건 · 위임 {len(m['delegated'])}건 · "
          f"산출물 편집 {sum(m['touched'].values())}회 · "
          f"도구 호출 {sum(m['tools'].values())}회 · 검증 실행 {m['checks']}회{RESET}")

    if m["kinds"]:
        print(f"\n{BOLD}무엇을 만들었나{RESET} {DIM}(편집한 파일의 종류){RESET}")
        rows = rank(m["kinds"], 9)
        hi = rows[0][1]
        for k, n in rows:
            print(f"  {CYAN}{k:<14}{RESET} {GREEN}{bar(n, hi)}{RESET} {n}회")

    print(f"\n{BOLD}mine 1: 반복해서 손댄 산출물{RESET} "
          f"{DIM}(여러 번 고쳤다면 그만큼 다시 하는 일이다){RESET}")
    ranked = rank(m["touched"], a.top)
    if not ranked:
        print("  (없음)")
    hi = ranked[0][1] if ranked else 0
    for f, n in ranked:
        print(f"  {CYAN}{clip(f, 28):<28}{RESET} {GREEN}{bar(n, hi)}{RESET} "
              f"{n}회 {DIM}{file_kind(f)}{RESET}")

    if m["dirs"]:
        line = "  ".join(f"{d} {n}" for d, n in rank(m["dirs"], 6))
        print(f"  {DIM}자주 손댄 폴더: {line}{RESET}")

    if task_groups:
        print(f"\n{BOLD}mine 2: 서브에이전트에 맡긴 과업{RESET} {DIM}(같은 과업은 묶었다){RESET}")
        for p, n in sorted(task_groups.items(), key=lambda kv: -kv[1])[: a.top]:
            mark = f"{GREEN}{n}회{RESET}" if n > 1 else f"{DIM}1회{RESET}"
            print(f"  {YELLOW}-{RESET} {clip(p, 84)}  {mark}")

    if req_ranked:
        print(f"\n{BOLD}mine 3: 사람이 직접 요청한 것{RESET} {DIM}(같은 요청은 묶었다){RESET}")
        for _, shown in req_ranked[: a.top]:
            n = len(shown)
            mark = f"{GREEN}{n}회{RESET}" if n > 1 else f"{DIM}1회{RESET}"
            print(f"  {DIM}-{RESET} {clip(shown[0], 84)}  {mark}")

    if m["toolkinds"] or m["servers"] or m["bash"]:
        print(f"\n{BOLD}mine 4: 도구로 시킨 일{RESET} "
              f"{DIM}(파일을 안 남기는 반복 — 브라우저·데이터·커뮤니케이션·웹·명령){RESET}")
    for k, n in rank(m["toolkinds"], a.top):
        names = [t for t in m["tools"] if tool_kind(t) == k]
        top_names = ", ".join(clip(t, 30) for t, _ in
                              rank({t: m["tools"][t] for t in names}, 3))
        print(f"  {MAGENTA}{k:<18}{RESET} {n:>4}회  {DIM}{top_names}{RESET}")
    if m["servers"]:
        line = "  ".join(f"{s} {n}" for s, n in rank(m["servers"], 6))
        print(f"  {MAGENTA}{'붙여 쓴 MCP 서버':<18}{RESET} {DIM}{line}{RESET}")
    if m["bash"]:
        line = "  ".join(f"{c} {n}" for c, n in rank(m["bash"], 8))
        print(f"  {MAGENTA}{'자주 친 명령':<18}{RESET} {DIM}{line}{RESET}")

    if m["commands"]:
        print(f"\n{BOLD}mine 5: 반복해서 부른 스킬·커맨드{RESET}")
        for c, n in rank(m["commands"], a.top):
            mark = f"{GREEN}{n}회{RESET}" if n > 1 else f"{DIM}1회{RESET}"
            print(f"  {YELLOW}/{c}{RESET}  {mark}")

    if len(sessions) > 1:
        print(f"\n{BOLD}mine 6: 세션별로 무슨 일을 했나{RESET} {DIM}(최근 순){RESET}")
        for s in sorted(sessions, key=lambda x: -x["mtime"])[:12]:
            print(digest(s))

    print(f"\n{DIM}이 목록에서 '내일도 또 할 일'을 하나 고르면 그것이 replay 대상이다.{RESET}")


if __name__ == "__main__":
    main()
