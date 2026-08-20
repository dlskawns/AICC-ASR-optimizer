# Pilot Round 5: 방언 표지가 AICC critical span 손실을 늘리는가

Round 2~4는 방언 표지와 AICC 손상의 연결을 **span 표면 겹침**으로 재려 했고, 세 번 다 실패했다. 표본을 50 → 300발화로 6배 늘려도 겹치는 span은 4개에서 5개로만 늘었다. 원인이 표본 크기가 아니라 설계였다.

Round 5는 질문을 발화 수준으로 바꾸고, 화자 내 짝지음으로 답했다.

사람 검수는 여전히 수행되지 않았다. 모든 수치는 자동 계산이며 gold가 아니다.

## 설계

[dialect_control_pairs](../aihub_119_dialect_control_pairs/README.md)

각 쌍은 **같은 녹음의 같은 화자**다.

- case: 방언 표지 어절과 critical span을 모두 가진 홀드아웃 발화.
- control: 같은 화자의 방언 표지가 **0개**이면서 critical span은 가진 발화, 어절 길이로 매칭.

화자·마이크·세션·주제가 쌍 안에서 고정되므로, 남는 체계적 차이는 방언 표지 유무뿐이다.

| Item | Value |
|---|---:|
| 쌍 | 63 |
| 화자 | 63 |
| 녹음 | 56 |
| 코호트 | 부산 33 / 기타 경상 30 |
| 평균 어절 수 (case / control) | 10.71 / 10.57 |
| 평균 길이 차 | -0.14 |
| scorable span (case / control) | 93 / 88 |
| 대조군 클립 | 5.67분 |

검정은 세 가지다: 쌍 단위 bootstrap, 쌍 내부 arm swap permutation, McNemar. 그리고 **placebo**로 비방언 어절 오류율을 같이 본다. 매칭이 제대로 됐다면 placebo는 두 arm에서 비슷해야 한다.

## 결과: 세 모델 모두 영점

[dialect_control_comparison](../aihub_119_dialect_control_comparison/README.md)

| Model | 방언 arm 손실 | 대조 arm 손실 | 차이 | 95% CI | permutation p | McNemar p |
|---|---:|---:|---:|---|---:|---:|
| medium | 0.108 | 0.080 | +0.028 | [-0.056, 0.114] | 0.554 | 0.773 |
| large-v3 | 0.118 | 0.136 | -0.018 | [-0.102, 0.066] | 0.704 | 0.773 |
| wav2vec2-ko | 0.398 | 0.375 | +0.023 | [-0.151, 0.198] | 0.811 | 0.850 |

placebo(비방언 어절 오류율) 차이도 세 모델 모두 0을 포함한다: +0.014 [-0.029, 0.058], -0.026 [-0.068, 0.018], +0.019 [-0.032, 0.071]. 매칭은 깨끗하다.

불일치 쌍도 대칭이다: medium 7 대 5, large-v3 5 대 7, wav2vec2 15 대 13. 부호가 모델마다 뒤집힌다.

## 해석

> 방언 표지 어절 자체의 ASR 오류율은 비방언 어절의 4배지만(Round 4), 그 취약성이 같은 발화 안의 AICC critical span 손실로는 번지지 않는다. 같은 화자의 방언 발화와 비방언 발화를 비교하면 critical span 손실률이 구분되지 않는다.

즉 방언 취약성은 **국소적**이다. 방언 표지 토큰에서 발생하고 거기 머문다. 발화 전체를 무너뜨리는 방식이 아니다.

이는 프로젝트 초기 가설을 좁힌다. "부산/경상 방언이 AICC 업무를 망친다"는 서사는 이 데이터로 지지되지 않는다. 지지되는 것은 "방언 표지 어절 자체가 체계적으로 불안정하다"까지다.

## 검정력 한계

이것은 "차이 없음"이 아니라 "탐지되지 않음"이다.

- CI 폭: medium 0.170, large-v3 0.168, wav2vec2 0.349.
- 즉 대략 0.10 이상의 손실률 차이라면 잡혔겠지만, 그보다 작은 효과는 63쌍으로 배제할 수 없다.
- span 수가 arm당 90개 내외로 적다. 쌍을 수백 단위로 늘리면 결론이 바뀔 여지가 있다.

## 남은 교란

- 방언 사용은 무작위 배정이 아니다. 화자가 더 어렵거나 격의 없는 대목에서 방언을 쓴다면, 짝지음은 "누가 말하는가"만 통제하고 "무엇을 말하기로 했는가"는 통제하지 못한다.
- 길이 매칭은 어절 수 기준이며 음향 길이나 발화 속도는 맞추지 않았다.
- control span 88개도 negation·confirmation에 쏠려 있다. amount는 양쪽 arm 모두 거의 없다.
- 라벨은 weak이며 사람 검수 전이다.

## 이번 라운드에서 말할 수 있게 된 claim

> 화자 내 짝지음 설계에서, 방언 표지를 포함한 발화는 같은 화자의 방언 없는 발화보다 AICC critical span을 더 많이 잃지 않는다. 세 baseline 모두 차이의 95% CI가 0을 포함하고 부호가 일치하지 않으며, placebo 검정도 통과한다.

## 아직 말하면 안 되는 claim

- 방언이 AICC 업무에 영향이 없다. 검정력이 0.10 수준까지만 미친다.
- 이 결과가 실제 contact-center 조건으로 일반화된다. 코퍼스는 자유 대화다.
- critical span 손실률이 실제 업무 실패율이다. weak label이다.

## 다음 작업

1. AICC 카테고리 균형(amount·date_time 포함) 대조 쌍을 별도로 채굴해 재검정.
2. 쌍 수를 수백 단위로 확대해 검정력을 0.05 수준으로 끌어올리기.
3. 방언 표지 어절 자체가 critical span인 경우만 모으는 표적 채굴. 현재 93개 중 5개뿐이라 별도 설계가 필요하다.
4. 16행 audio review 사람 검수(미착수).

## 재현 명령

```bash
uv run scripts/build_dialect_control_pairs.py \
  research/experiments/runs/aihub_119_speaker_independent_split/asr_input_manifest.local.jsonl \
  research/experiments/runs/aihub_119_holdout_critical_spans/remined_annotations.local.jsonl \
  research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz \
  --output-dir research/experiments/runs/aihub_119_dialect_control_pairs

D=research/experiments/runs/aihub_119_dialect_control_pairs
V=../japko/whisper_proto/.venv/bin/python
$V scripts/run_wav2vec2_korean_pilot_asr.py $D/asr_input_manifest.local.jsonl $D/wav2vec2_korean.local.jsonl
$V scripts/run_faster_whisper_pilot_asr.py $D/asr_input_manifest.local.jsonl $D/faster_whisper_medium.local.jsonl medium
$V scripts/run_faster_whisper_pilot_asr.py $D/asr_input_manifest.local.jsonl $D/faster_whisper_large_v3.local.jsonl large-v3

uv run scripts/compare_dialect_control_pairs.py $D/pair_manifest.jsonl \
  --case-dir research/experiments/runs/aihub_119_speaker_independent_split \
  --case-annotations research/experiments/runs/aihub_119_holdout_critical_spans/remined_annotations.local.jsonl \
  --control-dir $D \
  --output-dir research/experiments/runs/aihub_119_dialect_control_comparison
```
