# Pilot Round 7: 피해의 실제 크기, 카테고리 일반화, cue 수준 코호트

[Round 6](../aihub_119_pilot_round6/README.md)은 세 가지를 남겼다. 손실이 실제 업무 피해인지 표기 차이인지 구분하지 않았고, 사실상 confirmation 단독 결과였으며, 코호트 분해를 하지 않았다. Round 7은 셋을 모두 처리했다.

사람 검수는 여전히 수행되지 않았다. 모든 수치는 자동 계산이며 gold가 아니다.

## 1. Round 6의 절반은 무해한 정규화였다

[cue_error_types](../aihub_119_cue_error_types/README.md)

Round 6은 "정답 cue 문자열이 hypothesis에 없으면 손실"로 셌다. 이건 AICC 관점에서 성격이 전혀 다른 둘을 합친 것이다.

- ASR이 같은 cue의 **표준형**을 썼다 → 의미 보존, 피해 아님.
- cue가 아예 사라졌다 → 실제 피해.

라벨에서 각 cue의 어절 쌍(방언형/표준형)을 복원해 셋으로 나눴다.

| Model | 방언 cue: 표면유지 / 정규화 / 소실 | 평범 cue: 유지 / 소실 |
|---|---|---|
| medium | 0.292 / 0.350 / 0.358 | 0.836 / 0.164 |
| large-v3 | 0.300 / 0.403 / 0.296 | 0.852 / 0.148 |
| wav2vec2-ko | 0.107 / 0.037 / 0.856 | 0.348 / 0.652 |

**실제 피해 격차**(소실만 계산):

| Model | Round 6 표면 격차 | Round 7 실제 피해 격차 | 95% CI |
|---|---:|---:|---|
| medium | +0.396 | +0.194 | [0.117, 0.268] |
| large-v3 | +0.344 | +0.148 | [0.075, 0.221] |
| wav2vec2-ko | +0.348 | +0.204 | [0.131, 0.277] |

결론은 유지되지만 크기는 절반이다. Round 6 수치를 그대로 인용하면 피해를 두 배로 부풀리게 된다.

여기서 처음으로 모델 품질 차이가 드러난다. `large-v3`는 `medium`보다 방언형을 표준형으로 더 자주 옮기고(0.403 대 0.350) 덜 잃는다(0.296 대 0.358). Round 4·6에서 두 모델이 구분되지 않았던 것과 달리, 오류의 **성격**에서는 갈린다.

주의: 평범 cue arm의 정규화율이 0.000인 것은 정의상 당연하다. 방언 표지가 없는 어절은 방언형과 표준형이 같다. 두 arm의 정규화율을 직접 비교해서는 안 된다.

## 2. negation에서도 성립한다

[negation_cue_split](../aihub_119_negation_cue_split/README.md), [negation_cue_comparison](../aihub_119_negation_cue_comparison/README.md), [negation_error_types](../aihub_119_negation_error_types/README.md)

Round 6은 negation 쌍이 30개뿐이었고 Whisper에서 양쪽 arm 모두 0에 가까웠다. 카테고리 쿼터를 넣어 negation만 185쌍(화자 185명, 녹음 156개, 370클립, 32.5분)으로 다시 만들었다.

| Model | 표면 손실 (방언 vs 평범) | 표면 격차 95% CI | McNemar p | 불일치 쌍 |
|---|---|---|---:|---|
| medium | 0.265 vs 0.038 | +0.227 [0.162, 0.292] | 3.3e-09 | 45 : 3 |
| large-v3 | 0.265 vs 0.032 | +0.232 [0.168, 0.303] | 2.0e-09 | 46 : 3 |
| wav2vec2-ko | 0.665 vs 0.389 | +0.276 [0.173, 0.373] | 8.4e-07 | 77 : 26 |

실제 피해 격차도 셋 다 0을 제외한다: +0.198 [0.121, 0.274], +0.181 [0.105, 0.258], +0.241 [0.143, 0.333]. placebo는 세 모델 모두 0을 포함한다(+0.014, +0.011, +0.032).

> Round 6의 "사실상 confirmation 결과"라는 한계는 해소됐다. negation의 무효과는 30쌍짜리 검정력 부족이었다.

두 카테고리의 실제 피해 격차가 놀랄 만큼 비슷하다. confirmation 0.148~0.204, negation 0.181~0.241. 모델과 카테고리를 가로질러 **대략 0.15~0.25** 구간에 모인다.

## 3. 부산 특화: cue 수준에서도 영점

Round 4는 발화 수준에서만 코호트를 봤다. cue 수준에서 다시 본다(실제 피해 기준, 방언 arm만).

| Model | confirmation 중심 split | negation split |
|---|---|---|
| medium | +0.105 [-0.015, 0.227] | +0.089 [-0.041, 0.217] |
| large-v3 | +0.014 [-0.101, 0.129] | +0.013 [-0.118, 0.141] |
| wav2vec2-ko | -0.050 [-0.134, 0.039] | -0.119 [-0.241, 0.007] |

여섯 검정 모두 0을 포함하고 부호가 갈린다. 부산 특화 주장은 발화 수준과 cue 수준 양쪽에서 기각된다.

## 지금까지의 전체 그림

| Round | 질문 | 답 |
|---|---|---|
| 4 | 방언 표지 어절이 더 틀리는가 | 그렇다. 약 4배, 화자 분리 홀드아웃·세 아키텍처에서 유지 |
| 5 | 방언 발화면 AICC cue를 더 잃는가 | 아니다. 발화 수준에서는 영점 |
| 6 | cue 자체가 방언형이면 어떤가 | 손실 급증 |
| 7 | 그 손실이 실제 피해인가 | 절반은 무해한 표준형 정규화, 나머지 절반은 실제 소실. 격차 0.15~0.25 |

> 방언 ASR 피해는 확산형이 아니라 국소 명중형이며, 그 명중의 절반은 표준형 정규화로 흡수된다. 논문이 겨눠야 할 표적은 "방언 발화 전반의 WER"이 아니라 "업무 cue 위에 올라앉은 방언형이 표준형으로 흡수되지 못하고 소실되는 경우"다.

## 이번 라운드에서 말할 수 있게 된 claim

> 업무 cue가 방언 표지 어절일 때 cue 소실률이 유의하게 높다. Whisper `medium` 기준 실제 피해 격차는 confirmation 중심 split에서 +0.194 [0.117, 0.268], negation split에서 +0.198 [0.121, 0.274]이며, 세 baseline·두 카테고리 여섯 조합 모두 CI가 0을 제외하고 placebo를 통과한다.

> 방언 cue 오류의 상당 부분은 표준형 정규화이며 이는 의미를 보존한다. Whisper에서 방언 cue의 35~40%가 여기 해당한다. 따라서 표면 문자열 일치 기준 손실률은 AICC 피해를 약 2배 과대평가한다.

> 부산 방언이 기타 경상 방언보다 어렵다는 근거는 발화 수준과 cue 수준 어디에도 없다. 여섯 검정 모두 영점이다.

## 아직 말하면 안 되는 claim

- amount·date_time·intent_cue로의 일반화. 이 코퍼스에서 이 카테고리들은 방언 표지 어절에 거의 실리지 않아 검정 자체가 불가능하다.
- 모델 간 절대 손실률 비교. wav2vec2의 값은 CTC 정서법·학습 도메인 차이가 크다.
- 소실이 대체인지 누락인지. 이번 분류는 "표준형도 없다"까지만 판정한다.
- cue 손실률이 실제 AICC 업무 실패율이다. weak label이며 사람 검수 전이다.
- 방언형 cue 사용이 무작위 배정이다. 화자가 맥락에 따라 방언형을 고르는 효과는 통제되지 않았다.

## 다음 작업

1. cue 소실을 대체와 누락으로 재분류. 대체는 오인식 위험, 누락은 정보 손실로 AICC 대응이 다르다.
2. 소실된 cue가 실제로 어떤 표면으로 바뀌었는지 수집해 방언형 오류 패턴 사전 구축.
3. 표준형 정규화율이 모델별로 다른 이유 분석. large-v3가 medium보다 잘 흡수하는 것이 학습 데이터 때문인지 디코딩 때문인지.
4. 16행 audio review 사람 검수. 남은 유일한 사람 작업이다.

## 재현 명령

```bash
uv run scripts/classify_cue_error_types.py \
  research/experiments/runs/aihub_119_cue_bearing_split \
  --output-dir research/experiments/runs/aihub_119_cue_error_types

uv run scripts/build_cue_bearing_dialect_split.py \
  data/raw/aihub_gyeongsang_119 \
  research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz \
  --output-dir research/experiments/runs/aihub_119_negation_cue_split \
  --category negation --max-pairs 300

D=research/experiments/runs/aihub_119_negation_cue_split
V=../japko/whisper_proto/.venv/bin/python
$V scripts/run_wav2vec2_korean_pilot_asr.py $D/asr_input_manifest.local.jsonl $D/wav2vec2_korean.local.jsonl
$V scripts/run_faster_whisper_pilot_asr.py $D/asr_input_manifest.local.jsonl $D/faster_whisper_medium.local.jsonl medium
$V scripts/run_faster_whisper_pilot_asr.py $D/asr_input_manifest.local.jsonl $D/faster_whisper_large_v3.local.jsonl large-v3

uv run scripts/compare_cue_bearing_pairs.py $D --output-dir research/experiments/runs/aihub_119_negation_cue_comparison
uv run scripts/classify_cue_error_types.py $D --output-dir research/experiments/runs/aihub_119_negation_error_types
```
