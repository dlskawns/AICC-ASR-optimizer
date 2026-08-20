# Pilot Round 3: 라벨 채굴 규칙 수정과 비-Whisper 한국어 baseline

[Round 2](../aihub_119_pilot_round2/README.md)에서 두 가지 미해결 리스크를 남겼다. 하나는 critical-span 라벨의 21.6%가 substring 채굴 아티팩트라는 것, 다른 하나는 실험이 Whisper 계열 하나에만 의존한다는 것이다. Round 3은 둘 다 처리했다.

사람 검수는 여전히 수행되지 않았다. 모든 수치는 자동 계산이며 gold가 아니다.

## 1. 채굴 규칙을 어절 경계 기준으로 교체

원인은 [build_weak_semantic_preannotations.py:185](../../../../scripts/build_weak_semantic_preannotations.py#L185)의 `cue in transcript`와 [같은 파일 62행](../../../../scripts/build_weak_semantic_preannotations.py#L62)의 금액 정규식이다. 둘 다 어절 경계를 보지 않는다.

- 업무 cue가 일반 활용형 동사 내부에서 채굴됐다.
- 금액 정규식이 어절 경계를 넘어 매칭돼, 명사+조사 뒤에 화폐 단위로 시작하는 단어가 오면 없는 금액이 생겼다.

새 규칙([scripts/remine_critical_spans.py](../../../../scripts/remine_critical_spans.py))은 세 가지를 강제한다.

1. 모든 cue는 어절을 시작해야 한다.
2. cue마다 `exact`(단독 어절이어야 함)와 `prefix`(활용 가능) 모드를 명시한다. 단음절 부정·확인 표지는 `exact`다.
3. 금액은 토큰 단위로 매칭한다. 숫자 어절 + 단위 어절, 또는 한 어절 내부 숫자+단위만 인정한다.

결과:

| Rule | Spans | Phantom labels | Phantom rate |
|---|---:|---:|---:|
| 기존 substring | 74 | 16 | 0.216 |
| 신규 어절 경계 | 56 | 1 | 0.018 |

카테고리별로는 intent_cue가 15 → 5, confirmation이 17 → 10으로 줄었다. negation 17개와 date_time 13개는 그대로다. 남은 phantom 1건은 숫자 나열형이라 어느 경로로도 판정되지 않는 기존 알려진 케이스다.

교차 검증: 재채굴 라벨로 preservation 분석을 다시 돌린 결과가 기존 라벨 + 다운스트림 phantom 필터 결과와 거의 같다(medium strict loss 0.091 vs 0.103, large-v3 0.073 vs 0.069). 상류 수정과 하류 필터가 같은 답을 내므로 두 구현이 서로를 검증한다.

## 2. 비-Whisper 한국어 baseline 추가

`kresnik/wav2vec2-large-xlsr-korean`(Zeroth-Korean 기반 XLSR 파인튜닝)을 세 번째 baseline으로 추가했다. 50클립 총 27.4초로 Whisper large-v3의 292초보다 훨씬 빠르다.

**중요 제약: 모델 간 절대 오류율은 비교 대상이 아니다.** wav2vec2는 CTC 모델이라 띄어쓰기·정서법이 Whisper와 다르고, 읽기 음성 위주로 학습돼 자유 발화 방언에서 표면 일치율이 구조적으로 낮다. 비교 가능한 것은 각 모델 내부의 방언 대 비방언 대조뿐이다.

| Measure | medium | large-v3 | wav2vec2-ko |
|---|---:|---:|---:|
| 방언 단위 오류율 | 0.455 | 0.409 | 0.818 |
| 비방언 단위 오류율 | 0.172 | 0.161 | 0.611 |
| 차이 | 0.283 | 0.248 | 0.207 |
| 차이 95% CI | [0.169, 0.394] | [0.130, 0.367] | [0.088, 0.320] |
| 비율 | 2.64x | 2.54x | 1.34x |
| utterance 층화 MH OR | 4.10 [2.19, 7.70] | 3.31 [1.82, 6.04] | 2.53 [1.30, 4.92] |
| within-utterance permutation p | <5.0e-05 | <5.0e-05 | 1.65e-03 |
| 발화 구성으로 설명되는 몫 | 14% | 13% | 19% |
| 부산 − 기타 경상 | 0.033 [-0.197, 0.263] | 0.006 [-0.219, 0.223] | 0.011 [-0.187, 0.200]

핵심: 아키텍처가 완전히 다르고 절대 성능도 훨씬 낮은 모델에서도 방언 격차는 재현된다. 세 모델 모두 차이의 CI가 0을 제외하고, 발화 내부 permutation에서도 유의하다.

부산 대 기타 경상 차이는 세 모델 모두 0을 포함한다. 이제 세 번 독립적으로 확인됐다.

## 3. 재채굴 라벨 기준 critical-span 보존

| Measure | medium | large-v3 | wav2vec2-ko |
|---|---:|---:|---:|
| scorable spans | 55 | 55 | 55 |
| strict loss rate | 0.091 [0.018, 0.190] | 0.073 [0.000, 0.167] | 0.509 [0.353, 0.655] |
| inclusive loss rate | 0.109 | 0.073 | 0.655 |
| amount 손실 | 0/10 | 0/10 | 9/10 |

wav2vec2의 amount 9/10은 실제 의미 손상이라기보다 출력 형식 문제에 가깝다. CTC 출력이 수사를 정서법대로 쓰지 않아 숫자 파싱이 실패한다. 즉 amount 지표는 아키텍처 민감도가 높고, 모델 간 비교에 그대로 쓰면 안 된다.

## 이번 라운드에서 말할 수 있게 된 claim

> 경상 방언 표지 어절의 ASR 취약성은 Whisper 계열 고유 현상이 아니다. Whisper `medium`, Whisper `large-v3`, 그리고 한국어 특화 wav2vec2 CTC 모델 세 가지 모두에서, 발화 클러스터링과 발화 내부 permutation을 적용한 뒤에도 방언 단위 오류율이 비방언 단위보다 유의하게 높다.

> 부산 방언이 기타 경상 방언보다 어렵다는 근거는 세 모델 어디에서도 나오지 않는다.

> 자유 대화 코퍼스에서 AICC critical span을 substring으로 채굴하면 21.6%가 유령 라벨이 된다. 어절 경계와 cue별 exact/prefix 모드를 강제하면 1.8%로 떨어진다.

## 아직 말하면 안 되는 claim

- 모델 간 절대 오류율 비교. wav2vec2의 높은 오류율은 상당 부분 출력 형식과 학습 도메인 차이다.
- wav2vec2가 Whisper보다 방언에 강하다/약하다. 비율이 1.34x로 낮은 것은 비방언 오류율 자체가 이미 0.611로 높아서 생기는 천장 효과일 수 있다.
- critical-span 손실률이 실제 AICC 업무 실패율이다. 라벨은 여전히 weak이고 사람 검수 전이다.
- 방언 표지 span이 일반 span보다 더 많이 손실된다. 재채굴 후에도 dialect-marked span은 4개뿐으로 underpowered다.

## 남은 리스크

가장 약한 고리는 그대로다. 방언 표지와 AICC 손상을 잇는 span이 4개뿐이라 이 pilot에서는 그 연결을 측정할 수 없다. 이것은 규칙을 고쳐서 해결되는 문제가 아니라 표본 크기 문제이므로, speaker-independent 확장이 필요하다.

## 재현 명령

```bash
uv run scripts/remine_critical_spans.py \
  research/experiments/runs/aihub_119_pilot_review_packet/pilot_candidate_annotations.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_critical_span_remine

../japko/whisper_proto/.venv/bin/python -c "
from huggingface_hub import snapshot_download
print(snapshot_download('kresnik/wav2vec2-large-xlsr-korean'))
"

../japko/whisper_proto/.venv/bin/python scripts/run_wav2vec2_korean_pilot_asr.py \
  research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/wav2vec2_korean.local.jsonl

uv run scripts/run_dialect_significance_tests.py \
  research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_medium.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_large_v3.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/wav2vec2_korean.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_dialect_significance
```
