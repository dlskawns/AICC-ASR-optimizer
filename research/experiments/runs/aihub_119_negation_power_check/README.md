# negation 미결 해소 시도: 결판나지 않는다

[현재 결과](../aihub_119_current_results/README.md) 3절에 남아 있던 유일한 애매한 진술을 정리하려 했다. negation cue에서 `medium`의 격차가 +0.077, permutation p=0.084로 걸쳐 있었고, 이것이 실제 영점인지 검정력 부족인지 알 수 없었다.

쌍을 185개에서 290개로 늘려 다시 검정했다. **결론: 이 코퍼스로는 결판나지 않는다.**

## 무엇을 했나

기존 negation split은 화자당 1쌍으로 제한해 185쌍이었다. 제한을 화자당 최대 4쌍으로 풀어 290쌍(화자 185명, 녹음 156개, 580클립, 50.3분)을 만들었다.

화자당 여러 쌍을 쓰면 쌍이 서로 독립이 아니므로, 통계를 먼저 바꿨다.

- bootstrap을 쌍 재표집에서 **화자 재표집**으로 교체.
- arm-swap permutation도 **화자 단위**로 교체. 한 화자의 모든 쌍이 함께 뒤집힌다.
- McNemar는 쌍 독립을 가정하므로 화자당 1쌍일 때만 읽으라는 주석을 결과에 넣었다.

회귀 검증: 화자당 1쌍인 기존 데이터에서 새 코드가 기존 수치를 그대로 재현했다(+0.077 / +0.098 / +0.175).

## 결과

| 쌍 수 | Model | 방언 arm | 평범 arm | 격차 95% CI | permutation p | placebo |
|---|---|---:|---:|---|---:|---|
| 185 | medium | 0.251 | 0.175 | +0.077 [-0.005, 0.158] | 0.084 | +0.011 [-0.027, 0.048] |
| 185 | large-v3 | 0.235 | 0.137 | +0.098 [0.022, 0.175] | 0.018 | +0.021 [-0.016, 0.058] |
| 185 | wav2vec2-ko | 0.678 | 0.503 | +0.175 [0.071, 0.279] | 0.0015 | +0.033 [-0.005, 0.073] |
| 290 | medium | 0.249 | 0.178 | +0.071 [0.003, 0.142] | 0.060 | +0.017 [-0.013, 0.047] |
| 290 | large-v3 | 0.231 | 0.121 | +0.110 [0.045, 0.176] | 0.0017 | **+0.034 [0.005, 0.064]** |
| 290 | wav2vec2-ko | 0.673 | 0.498 | +0.174 [0.085, 0.260] | 0.0002 | +0.022 [-0.011, 0.055] |

## 왜 결판나지 않았나

**첫째, medium은 두 검정이 엇갈린다.** 290쌍에서 bootstrap CI는 [0.003, 0.142]로 0을 아슬아슬하게 제외하지만 permutation p는 0.060으로 유의하지 않다. 두 검정이 갈릴 때는 쌍 구조를 조건부로 정확히 다루는 permutation을 따르는 것이 옳다. 즉 여전히 유의하지 않다.

p는 0.084에서 0.060으로 움직였을 뿐이다. 표본을 1.57배 늘려 이 정도라면, 유의성 확보에는 대략 네 배 규모, 1,100쌍 이상이 필요하다.

**둘째, 그 규모는 이 코퍼스에 없다.** 깨끗한 매칭(화자당 1쌍)의 상한이 185쌍이다. 그 이상은 같은 화자를 반복해서 쓰는 것뿐이고, 그러면 다음 문제가 생긴다.

**셋째, 쌍을 늘리자 매칭 품질이 떨어졌다.** 290쌍에서 large-v3의 placebo가 +0.034 [0.005, 0.064]로 0을 제외한다. placebo는 두 arm의 비방언 어절 오류율 차이이고, 이것이 0을 벗어나면 두 arm이 방언 표지 외의 무언가에서도 다르다는 뜻이다. 즉 large-v3의 290쌍 결과는 신뢰할 수 없다.

화자당 쌍 분포는 1쌍 122명, 2쌍 32명, 3쌍 20명, 4쌍 11명이다. 추가된 쌍은 이미 등장한 화자에게서 나왔고, 그 화자의 두 번째·세 번째 발화는 첫 번째만큼 잘 맞춰지지 않았다.

## 결론

> negation cue에서 `medium`의 방언 페널티는 이 코퍼스로 판정할 수 없다. 효과 방향은 일관되게 양수(+0.071 ~ +0.077)이지만 크기가 작아, 깨끗하게 매칭 가능한 최대 표본에서도 유의성에 이르지 못한다.

인용 기준은 **185쌍 결과**를 유지한다. 세 모델 모두 placebo를 통과하는 유일한 구성이다. 290쌍은 강건성 점검으로만 쓴다. 방향이 바뀌지 않고 크기도 비슷하다는 점은 확인됐다.

현재 결과 문서의 서술은 그대로 둔다.

> confirmation에서 강하고, negation에서 약하며 모델에 따라 갈린다.

여기에 한 줄을 더한다.

> negation에서 `medium`이 유의하지 않은 것은 검정력 부족일 수 있으나, 이 코퍼스에서는 확인할 방법이 없다.

## 부수적으로 얻은 것

통계가 화자 단위 클러스터링으로 바뀌었다. 앞으로 화자당 여러 쌍을 쓰는 설계에서도 유효한 검정을 할 수 있다.

## 재현

```bash
uv run scripts/build_cue_bearing_dialect_split.py \
  data/raw/aihub_gyeongsang_119 \
  research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz \
  --output-dir research/experiments/runs/aihub_119_negation_cue_split_wide \
  --category negation --per-speaker 4 --max-pairs 600

D=research/experiments/runs/aihub_119_negation_cue_split_wide
V=../japko/whisper_proto/.venv/bin/python
$V scripts/run_wav2vec2_korean_pilot_asr.py $D/asr_input_manifest.local.jsonl $D/wav2vec2_korean.local.jsonl
$V scripts/run_faster_whisper_pilot_asr.py $D/asr_input_manifest.local.jsonl $D/faster_whisper_medium.local.jsonl medium
$V scripts/run_faster_whisper_pilot_asr.py $D/asr_input_manifest.local.jsonl $D/faster_whisper_large_v3.local.jsonl large-v3

uv run scripts/score_cues_by_alignment.py $D --output-dir research/experiments/runs/aihub_119_negation_wide_aligned
```
