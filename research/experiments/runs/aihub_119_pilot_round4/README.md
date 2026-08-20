# Pilot Round 4: 화자 분리 홀드아웃 300발화

> **정정 있음.** 이 문서의 어절 단위 오류율은 어절 경계를 보지 않는 판정으로 계산됐다. 정정된 수치는 [지표 정정](../aihub_119_metric_correction/README.md)을 따른다.

[Round 3](../aihub_119_pilot_round3/README.md)까지의 결론은 전부 50발화·46녹음 파일럿 위에 있었다. Round 4는 파일럿과 녹음이 겹치지 않는 300발화 홀드아웃을 만들고, 같은 분석을 그대로 다시 돌렸다.

사람 검수는 여전히 수행되지 않았다. 모든 수치는 자동 계산이며 gold가 아니다.

## Split 구성

[speaker_independent_split](../aihub_119_speaker_independent_split/README.md)

- 300발화, 화자 300명, 녹음 159개.
- 파일럿이 쓴 녹음 46개는 전부 제외했다.
- 화자당 최대 2발화로 제한했으나 후보 화자가 충분해 실제로는 전원 1발화씩만 선택됐다.
- 방언 단위 352개 / 비방언 단위 2525개. 파일럿(66 / 471)의 5.3배.
- 총 26.47분. 후보 풀 25,911발화에서 콘텐츠 해시 순서로 결정적 선택.

## 1. 방언 격차는 홀드아웃에서 더 크다

[holdout_significance](../aihub_119_holdout_significance/README.md)

| Measure | medium | large-v3 | wav2vec2-ko |
|---|---:|---:|---:|
| 방언 단위 오류율 | 0.631 | 0.622 | 0.886 |
| 비방언 단위 오류율 | 0.156 | 0.155 | 0.556 |
| 차이 | 0.475 | 0.467 | 0.330 |
| 차이 95% CI | [0.418, 0.532] | [0.411, 0.525] | [0.291, 0.367] |
| 비율 | 4.05x | 4.02x | 1.59x |
| utterance 층화 MH OR | 9.30 [7.06, 12.25] | 8.74 [6.67, 11.46] | 6.23 [4.36, 8.91] |
| within-utterance permutation p | <5.0e-05 | <5.0e-05 | <5.0e-05 |
| 발화 구성으로 설명되는 몫 | 4% | 3% | 8% |

파일럿 대비:

| Measure | 파일럿 50 | 홀드아웃 300 |
|---|---|---|
| medium 차이 | 0.283 [0.169, 0.394] | 0.475 [0.418, 0.532] |
| medium 비율 | 2.64x | 4.05x |
| medium MH OR | 4.10 [2.19, 7.70] | 9.30 [7.06, 12.25] |
| large-v3 비율 | 2.54x | 4.02x |
| wav2vec2 비율 | 1.34x | 1.59x |

효과가 사라지기는커녕 세 모델 모두에서 커졌고 CI 폭은 절반 이하로 줄었다. 발화 구성으로 설명되는 몫도 14% → 4%로 떨어졌다. 즉 파일럿에서 남아 있던 "표본이 우연히 어려웠던 것 아니냐"는 반론은 홀드아웃에서 더 약해진다.

한 가지 주의: 파일럿과 홀드아웃은 표본 설계가 다르다. 파일럿은 critical-span 후보 큐에서, 홀드아웃은 방언 어절 보유 발화에서 직접 뽑았다. 절대 효과 크기를 인용할 때는 어느 split인지 반드시 밝혀야 한다.

## 2. 모델 스케일: large-v3의 이점이 홀드아웃에서 사라진다

파일럿에서는 medium 0.283 → large-v3 0.248로 격차가 줄었다. 홀드아웃에서는 0.475 → 0.467로 사실상 차이가 없고 CI가 거의 완전히 겹친다. 비율은 4.05x와 4.02x다.

> Round 2에서 "모델을 키우면 격차가 축소된다"고 적었던 부분은 홀드아웃에서 재현되지 않는다. 더 안전한 서술은 "모델 스케일을 키워도 방언 격차는 닫히지 않으며, 파일럿에서 보였던 소폭 축소는 표본 변동 범위 안이었다"이다.

## 3. 부산 특화 주장: 이제 검정력을 갖춘 부정

| Model | 부산 − 기타 경상 | 95% CI | CI 폭 |
|---|---:|---|---:|
| medium (파일럿) | 0.033 | [-0.197, 0.263] | 0.46 |
| medium (홀드아웃) | -0.023 | [-0.132, 0.087] | 0.22 |
| large-v3 (홀드아웃) | -0.017 | [-0.125, 0.091] | 0.22 |
| wav2vec2 (홀드아웃) | 0.011 | [-0.055, 0.077] | 0.13 |

파일럿에서는 CI가 넓어 "모른다"에 가까웠다. 홀드아웃에서는 CI 폭이 절반 이하로 줄고도 0을 중앙 부근에 포함한다. 부호도 모델마다 갈린다.

> 부산 방언이 기타 경상 방언보다 ASR에 어렵다는 근거는 없다. 이것은 이제 검정력 부족이 아니라 실질적 영점 결과다.

## 4. Critical span: 구조적 한계 확인

[holdout_critical_spans](../aihub_119_holdout_critical_spans/README.md)에서 어절 경계 규칙으로 93개 span을 채굴했고 phantom은 0개다. 규칙이 새 데이터에서도 유지된다.

| Model | scorable | strict loss | 95% CI |
|---|---:|---:|---|
| medium | 93 | 0.108 | [0.044, 0.182] |
| large-v3 | 93 | 0.118 | [0.053, 0.196] |
| wav2vec2-ko | 93 | 0.398 | [0.278, 0.521] |

그러나 **표본을 6배로 늘려도 방언 표지와 겹치는 critical span은 93개 중 5개뿐이다.** 파일럿에서 4개였던 것이 5개가 됐을 뿐이다.

원인이 표본 크기가 아니었다:

- 300발화 전부에 방언 단위가 있다.
- critical span을 가진 발화는 63개다.
- 그런데 span 표면과 방언 어절 표면이 겹치는 경우는 5건뿐이다.

즉 AICC 표지(부정·확인 표지)와 방언 표지 어절은 이 코퍼스에서 표면적으로 거의 공기하지 않는다. span 표면 겹침으로 "방언 → AICC 손상"을 재려는 설계 자체가 틀렸다.

또한 홀드아웃 span은 negation 48개, confirmation 42개에 쏠려 있고 amount는 0개다. 방언 어절 기준으로 발화를 뽑았기 때문이며, AICC 카테고리 균형이 필요한 분석에는 그대로 쓸 수 없다.

## 이번 라운드에서 말할 수 있게 된 claim

> 경상 방언 표지 어절의 ASR 취약성은 파일럿 표본 특성이 아니다. 파일럿과 녹음이 겹치지 않는 화자 300명 홀드아웃에서, 세 baseline 모두 격차가 오히려 커졌고(medium 4.05x, large-v3 4.02x, wav2vec2 1.59x), 발화 내부 permutation에서 20000회 중 관측값에 도달한 draw가 하나도 없었다.

> 부산 방언이 기타 경상 방언보다 어렵다는 주장은 검정력 있는 데이터에서 기각된다. 세 모델의 코호트 차이 CI가 모두 0을 포함하고 부호도 일치하지 않는다.

> 방언과 AICC 손상의 연결을 span 표면 겹침으로 측정하는 설계는 표본을 6배 늘려도 작동하지 않는다. 두 현상이 표면에서 공기하지 않기 때문이며, 발화 수준 설계로 재정의해야 한다.

## 아직 말하면 안 되는 claim

- 모델 간 절대 오류율 비교. wav2vec2의 높은 오류율은 CTC 정서법·학습 도메인 차이가 크다.
- 파일럿과 홀드아웃의 절대 효과 크기를 같은 것으로 취급하기. 표본 설계가 다르다.
- 성별·연령 효과. 홀드아웃은 여성 228 / 남성 72, 20대 205명으로 치우쳐 있고 교란을 통제하지 않았다.
- critical-span 손실률이 실제 AICC 업무 실패율이다. 라벨은 weak이고 사람 검수 전이다.
- large-v3가 medium보다 방언에 강하다. 홀드아웃에서 두 모델은 구분되지 않는다.

## 다음 작업

1. dialect → AICC 연결을 발화 수준으로 재설계한다. 두 조건을 모두 갖춘 63개 발화에서 방언 밀도가 critical-span 손실을 예측하는지 보는 편이 검정력이 훨씬 높다.
2. AICC 카테고리 균형을 맞춘 별도 홀드아웃을 채굴한다. 현재 홀드아웃에는 amount가 0개다.
3. 성별·연령 층화 또는 균형 split.
4. 16행 audio review 사람 검수(미착수).

## 재현 명령

```bash
uv run scripts/build_speaker_independent_split.py \
  research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz \
  --output-dir research/experiments/runs/aihub_119_speaker_independent_split \
  --per-cohort 150 --max-per-speaker 2

D=research/experiments/runs/aihub_119_speaker_independent_split
V=../japko/whisper_proto/.venv/bin/python
$V scripts/run_wav2vec2_korean_pilot_asr.py $D/asr_input_manifest.local.jsonl $D/wav2vec2_korean.local.jsonl
$V scripts/run_faster_whisper_pilot_asr.py $D/asr_input_manifest.local.jsonl $D/faster_whisper_medium.local.jsonl medium
$V scripts/run_faster_whisper_pilot_asr.py $D/asr_input_manifest.local.jsonl $D/faster_whisper_large_v3.local.jsonl large-v3

uv run scripts/run_dialect_significance_tests.py \
  $D/asr_input_manifest.local.jsonl \
  $D/faster_whisper_medium.local.jsonl $D/faster_whisper_large_v3.local.jsonl $D/wav2vec2_korean.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_holdout_significance

uv run scripts/remine_critical_spans.py $D/asr_input_manifest.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_holdout_critical_spans
```

ASR 소요: wav2vec2 118초, medium 840초, large-v3 1544초.
