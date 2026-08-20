# Pilot Round 6: cue 자체가 방언 표지일 때

> **정정 있음.** 이 문서의 cue 수치는 정렬을 쓰지 않는 판정 기준으로 계산됐다. 정정된 수치는 [지표 정정](../aihub_119_metric_correction/README.md)을 따르며, 정정 4에서 negation 결과와 대체·삭제 결론이 바뀐다.

[Round 5](../aihub_119_pilot_round5/README.md)는 방언 표지가 발화 어딘가에 있다는 사실만으로는 AICC critical span 손실이 늘지 않는다는 null을 냈다. 그 해석은 "방언 취약성이 방언 토큰에 국소적"이라는 것이었고, 그렇다면 검증 가능한 예측이 따라온다.

> AICC cue 단어 자체가 방언 표지 어절이면, 그 cue는 더 많이 손실되어야 한다.

Round 6은 그 예측을 직접 검정했다. 결과는 세 모델 모두에서 강한 양성이다.

사람 검수는 여전히 수행되지 않았다. 모든 수치는 자동 계산이며 gold가 아니다.

## 설계

[cue_bearing_split](../aihub_119_cue_bearing_split/README.md)

이런 사례는 무작위 표본에서 희귀하다. Round 4 홀드아웃에서는 93개 중 5개였다. 그래서 전체 라벨 229,497발화를 스캔해 표적 채굴했다.

- cue를 담은 방언 표지 어절: 829개
- 매칭용 비방언 cue 발생: 56,018개
- 구성된 쌍: 250

각 쌍은 **같은 화자가 같은 cue 카테고리를 두 번 발화**한 것이다. 한 번은 cue가 방언 표지 어절 위에, 한 번은 평범한 어절 위에 있다. 화자·녹음·cue 카테고리가 쌍 안에서 고정되므로, 남는 차이는 cue 단어의 방언 표지 여부뿐이다.

| Item | Value |
|---|---:|
| 쌍 | 250 |
| 화자 | 250 |
| 녹음 | 213 |
| 클립 | 500 (42.3분) |
| 코호트 | 부산 143 / 기타 경상 107 |
| cue 카테고리 | confirmation 220 / negation 30 |

## 결과

[cue_bearing_comparison](../aihub_119_cue_bearing_comparison/README.md)

| Model | cue가 방언 표지일 때 손실 | 아닐 때 | 차이 | 95% CI | permutation p | McNemar p | 불일치 쌍 |
|---|---:|---:|---:|---|---:|---:|---|
| medium | 0.488 | 0.092 | +0.396 | [0.324, 0.464] | <5e-05 | 1.3e-19 | 108 : 9 |
| large-v3 | 0.436 | 0.092 | +0.344 | [0.276, 0.412] | <5e-05 | 1.5e-16 | 96 : 10 |
| wav2vec2-ko | 0.872 | 0.524 | +0.348 | [0.272, 0.420] | <5e-05 | 1.9e-15 | 102 : 15 |

placebo(비방언 어절 오류율) 차이는 세 모델 모두 0을 포함한다: +0.008 [-0.016, 0.032], +0.004 [-0.020, 0.026], +0.016 [-0.016, 0.048]. 매칭은 깨끗하다.

불일치 쌍이 극단적으로 비대칭이다. Whisper `medium`에서는 방언 쪽만 cue를 잃은 쌍이 108개인 반면 평범한 쪽만 잃은 쌍은 9개다.

## 카테고리별: 사실상 confirmation 현상이다

| Model | confirmation (220쌍) | negation (30쌍) |
|---|---|---|
| medium | 0.550 vs 0.105 | 0.033 vs 0.000 |
| large-v3 | 0.495 vs 0.105 | 0.000 vs 0.000 |
| wav2vec2-ko | 0.914 vs 0.559 | 0.567 vs 0.267 |

Whisper 두 모델에서 negation은 양쪽 arm 모두 거의 손실이 없다. 30쌍뿐이기도 하다. 따라서 이 라운드의 효과는 **confirmation 표지에서 나온 것**으로 읽어야 하며, negation으로 일반화할 수 없다.

## Round 4·5·6을 합친 그림

세 라운드가 하나의 일관된 구조를 만든다.

1. **Round 4**: 방언 표지 어절의 오류율은 비방언 어절의 약 4배다. 화자 분리 홀드아웃에서도, 세 아키텍처에서도 유지된다.
2. **Round 5**: 그런데 방언 표지가 발화 어딘가에 있다는 사실은 AICC critical span 손실을 늘리지 않는다. 취약성이 발화 전체로 번지지 않는다.
3. **Round 6**: cue 단어 자체가 방언 표지이면 손실이 급증한다. 세 모델 모두 차이의 CI가 0을 제외하고 McNemar p가 1e-15 이하다.

> 즉 방언 ASR 피해는 확산형이 아니라 **국소 명중형**이다. 방언형이 업무상 중요한 토큰 위에 올라앉을 때만 실제 손상이 발생한다.

이 서사는 WER 개선 논문과 다르다. 평가 대상이 "방언 발화 전반"이 아니라 "방언형과 업무 cue의 교집합"으로 좁혀지고, 그 교집합이 실제로 위험 구간임을 데이터로 보였기 때문이다.

## 이번 라운드에서 말할 수 있게 된 claim

> 같은 화자가 같은 종류의 AICC cue를 방언형으로 말할 때와 표준형으로 말할 때를 비교하면, 방언형 cue의 손실률이 유의하게 높다. Whisper `medium` 0.488 대 0.092, `large-v3` 0.436 대 0.092, 한국어 wav2vec2 0.872 대 0.524이며, 세 모델 모두 placebo 검정을 통과한다.

> Round 5의 null과 함께 읽으면, 방언 ASR 취약성은 발화 전체를 저하시키는 방식이 아니라 방언 토큰에 국소적으로 발생하며, 그 토큰이 업무 cue와 겹칠 때 AICC 손상으로 이어진다.

## 아직 말하면 안 되는 claim

- 이 효과가 negation·amount·date_time·intent_cue로 일반화된다. 검정된 것은 사실상 confirmation이다. negation은 30쌍뿐이고 Whisper에서 양쪽 다 0에 가깝다.
- 모델 간 절대 손실률 비교. wav2vec2의 높은 값은 CTC 정서법·학습 도메인 차이가 크다.
- 방언형 cue 사용이 무작위 배정이다. 화자가 특정 맥락에서 방언형을 고를 수 있고, 그 맥락 효과는 통제되지 않았다.
- cue 손실률이 실제 AICC 업무 실패율이다. weak label이며 사람 검수 전이다.
- 부산 특화 효과. 이 라운드는 코호트별로 분해하지 않았고, Round 4에서 코호트 차이는 영점이었다.

## 다음 작업

1. 코호트별(부산/기타 경상) 분해로 Round 4의 영점이 cue 수준에서도 유지되는지 확인.
2. negation 쌍을 수백 단위로 확대해 confirmation 외 카테고리에서도 성립하는지 검정.
3. 방언형 cue의 오류 유형 분류: 표준형으로 정규화됐는가, 다른 단어로 대체됐는가, 누락됐는가. AICC 관점에서 세 경우의 위험도가 다르다.
4. 16행 audio review 사람 검수. 이제 남은 유일한 사람 작업이다.

## 재현 명령

```bash
uv run scripts/build_cue_bearing_dialect_split.py \
  data/raw/aihub_gyeongsang_119 \
  research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz \
  --output-dir research/experiments/runs/aihub_119_cue_bearing_split

D=research/experiments/runs/aihub_119_cue_bearing_split
V=../japko/whisper_proto/.venv/bin/python
$V scripts/run_wav2vec2_korean_pilot_asr.py $D/asr_input_manifest.local.jsonl $D/wav2vec2_korean.local.jsonl
$V scripts/run_faster_whisper_pilot_asr.py $D/asr_input_manifest.local.jsonl $D/faster_whisper_medium.local.jsonl medium
$V scripts/run_faster_whisper_pilot_asr.py $D/asr_input_manifest.local.jsonl $D/faster_whisper_large_v3.local.jsonl large-v3

uv run scripts/compare_cue_bearing_pairs.py $D \
  --output-dir research/experiments/runs/aihub_119_cue_bearing_comparison
```
