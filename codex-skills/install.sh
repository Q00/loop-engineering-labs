#!/bin/bash
# Codex용 워크숍 스킬 설치: harvest·checklist·myloop을 ~/.codex/skills로 복사한다.
# 주의: 같은 이름의 기존 스킬은 덮어쓴다.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p ~/.codex/skills
for s in harvest checklist myloop; do
  rm -rf ~/.codex/skills/$s
  cp -R $s ~/.codex/skills/$s
  echo "installed: ~/.codex/skills/$s"
done
echo
echo "Codex를 다시 열고 /harvest → /checklist → /myloop 순서로 진행한다."
