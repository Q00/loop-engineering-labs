#!/bin/bash
# 가재코드(Gajae Code)용 워크숍 스킬 설치: harvest·checklist·myloop을
# ~/.gjc/agent/skills 로 복사한다.
# 주의: 같은 이름의 기존 스킬은 덮어쓴다.
#
# 이 폴더의 Python 헬퍼(sleep_harvest.py·trace_read.py)는 가재코드 세션 로그
# (~/.gjc/agent/sessions/*/*.jsonl)의 JSONL 스키마(toolCall/arguments/소문자 도구명)와
# Claude Code(~/.claude/projects)·Codex(~/.codex/sessions) 양식을 모두 인식한다.
set -euo pipefail
cd "$(dirname "$0")"
DEST="${GJC_SKILLS_DIR:-$HOME/.gjc/agent/skills}"
mkdir -p "$DEST"
for s in harvest checklist myloop; do
  rm -rf "$DEST/$s"
  cp -R "$s" "$DEST/$s"
  echo "installed: $DEST/$s"
done
echo
echo "가재코드를 다시 열고 /harvest → /checklist → /myloop 순서로 진행한다."
