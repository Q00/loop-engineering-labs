#!/bin/bash
# 루프 코스 실습 스킬 설치: 이 폴더의 loopN을 ~/.claude/skills로 복사한다.
# _shared/*.py는 여러 강의가 공유하므로 각 스킬 폴더에 사본으로 넣는다
# (스킬은 자기 폴더 안의 파일을 경로로 참조하기 때문).
# 주의: 같은 이름의 기존 스킬(~/.claude/skills/loop2..5)은 덮어쓴다.
set -euo pipefail
cd "$(dirname "$0")"
for n in 2 3 4 5; do
  cp _shared/trace_read.py loop$n/trace_read.py
  rm -rf ~/.claude/skills/loop$n
  cp -R loop$n ~/.claude/skills/loop$n
  echo "installed: ~/.claude/skills/loop$n"
done
# 4.1강(그래프 실습)은 세션 로그를 쓰지 않는다. trace_read.py 없이 그대로 복사한다
rm -rf ~/.claude/skills/loop4-1
cp -R loop4-1 ~/.claude/skills/loop4-1
echo "installed: ~/.claude/skills/loop4-1"
# 4강은 세션 기록에서 반복 과업을 캐낸다(harvest·mine) + held-out 데이터로 게이트를 건다
cp _shared/sleep_harvest.py ~/.claude/skills/loop4/sleep_harvest.py
rm -rf ~/.claude/skills/loop4/heldout
cp -R data-heldout ~/.claude/skills/loop4/heldout
echo "loop4: sleep_harvest.py + heldout 데이터 추가"
# 오프라인 워크숍 스킬 3종: /harvest → /checklist → /myloop
for s in harvest checklist myloop; do
  rm -rf ~/.claude/skills/$s
  cp -R $s ~/.claude/skills/$s
  echo "installed: ~/.claude/skills/$s"
done
cp _shared/sleep_harvest.py _shared/trace_read.py ~/.claude/skills/harvest/
echo "harvest: sleep_harvest.py + trace_read.py 추가"
echo
echo "Claude Code를 다시 열고 /loop2 부터 /loop5 까지 실행한다."
echo "오프라인 워크숍은 /harvest → /checklist → /myloop 순서다."
