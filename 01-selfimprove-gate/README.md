# SkillOpt 라이브 데모

발표 1(GATE가 안전벨트인 이유) 슬라이드를 청중 앞에서 **실물로** 돌리기 위한 세팅.

## 무엇을 보여주나

SkillOpt-Sleep의 검증 실험은 발표에서 설명한 self-evolution 루프를 그대로 재현한다:

```
Rollout → Reflect → Aggregate → Select → Update → GATE → (반복)
```

- held-out 점수가 밤(nightly)마다 오른다: **0.33 → 1.0**
- **GATE가 유해한 편집(regression)을 거부**한다 → `gate blocks harmful edit: True`
- 전부 `MockBackend`로 **결정적**으로 재현 (네트워크·API 키·GPU 전부 불필요)

즉, "LLM이 제안해도 결정적 held-out 점수가 거부권을 쥔다"는 발표의 핵심 메시지를 라이브로 증명한다.

## 준비 (1회)

```bash
git clone https://github.com/microsoft/SkillOpt
```

## 실행 (권장 · API 키 불필요)

```bash
SKILLOPT_DIR=./SkillOpt ./run-demo.sh                 # researcher persona, 2 nights
SKILLOPT_DIR=./SkillOpt ./run-demo.sh programmer 3    # 다른 persona, 3 nights
```

내부적으로는 아래 명령을 실행한다 (저장소 루트에서):

```bash
python3 -m skillopt_sleep.experiments.run_experiment \
    --persona researcher --nights 2 --assert-improves
```

- `skillopt_sleep`는 **third-party 의존성이 없다** (stdlib만). `pip install` 없이 시스템 `python3`(≥3.10)로 바로 실행.
- `--json`을 붙이면 밤별 trace가 JSON으로 나온다 (슬라이드/로그용).
- 결정적이라 리허설과 본 발표 결과가 100% 동일하다.

## (선택) 실제 API로 진짜 학습 루프 돌리기

Mock이 아니라 실제 최적화를 보여주고 싶다면, 가장 저렴한 경로는 SearchQA다.

```bash
cd SkillOpt
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[searchqa]'

export AZURE_OPENAI_ENDPOINT=https://api.openai.com/v1
export AZURE_OPENAI_API_KEY=sk-...            # 일반 OpenAI 키
export AZURE_OPENAI_AUTH_MODE=openai_compatible

python scripts/materialize_searchqa.py        # 공개 HF 데이터 다운로드
python scripts/train.py --config configs/searchqa/default.yaml \
    --num_epochs 1 --train_size 8 --batch_size 8 --limit 8 \
    --optimizer_backend openai_chat --target_backend openai_chat \
    --optimizer_model gpt-4o-mini --target_model gpt-4o-mini
```

- 필요한 것: **OpenAI 키 1개**. 위 축소 플래그로 수십~수백 회 호출, 몇 달러, 수 분.
- 주의: 기본 config(400 train × 4 epoch)는 훨씬 비싸다. 반드시 `--limit`/`--train_size`로 줄일 것.

## 파일

- `run-demo.sh`: 무-API Mock 데모 러너 (라이브용)
- `README.md`: 이 문서
