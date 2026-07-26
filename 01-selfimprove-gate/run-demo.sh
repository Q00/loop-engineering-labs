#!/usr/bin/env bash
# =====================================================================
#  SkillOpt-Sleep 라이브 데모 러너 (API 키 불필요 · 결정적)
#  발표 1(GATE가 안전벨트인 이유) 슬라이드와 직접 연결되는 데모.
#
#  이 데모가 보여주는 것:
#    - Rollout → Reflect → ... → GATE 로 도는 self-evolution 루프
#    - held-out 점수가 밤마다(nightly) 오르는 것 (0.33 → 1.0)
#    - GATE 가 유해한 편집(regression)을 거부하는 것
#  전부 MockBackend 로 결정적으로 재현 (네트워크·API 키 0).
# =====================================================================
set -euo pipefail

# SkillOpt 저장소 위치 (필요시 SKILLOPT_DIR 환경변수로 덮어쓰기)
SKILLOPT_DIR="${SKILLOPT_DIR:-./SkillOpt}"

if [[ ! -d "$SKILLOPT_DIR/skillopt_sleep" ]]; then
  echo "ERROR: SkillOpt 를 찾을 수 없습니다: $SKILLOPT_DIR" >&2
  echo "       SKILLOPT_DIR 환경변수로 경로를 지정하세요." >&2
  exit 1
fi

PERSONA="${1:-researcher}"   # researcher | programmer
NIGHTS="${2:-2}"             # 밤(반복) 횟수

echo "==================================================================="
echo "  SkillOpt-Sleep 데모  ·  persona=$PERSONA  ·  nights=$NIGHTS  ·  backend=mock"
echo "  (API 키 없음 · 결정적 · 발표 1의 GATE 슬라이드 실물 시연)"
echo "==================================================================="
echo

cd "$SKILLOPT_DIR"
python3 -m skillopt_sleep.experiments.run_experiment \
  --persona "$PERSONA" \
  --nights "$NIGHTS" \
  --assert-improves

echo
echo "-------------------------------------------------------------------"
echo "  해석: held-out 점수가 올랐고(lift>0), GATE 가 유해 편집을 막았으면 PASS."
echo "  변형:  ./run-demo.sh programmer 3      (다른 persona / 더 많은 밤)"
echo "         SKILLOPT_DIR=/path ./run-demo.sh  (저장소 경로 덮어쓰기)"
echo "-------------------------------------------------------------------"
