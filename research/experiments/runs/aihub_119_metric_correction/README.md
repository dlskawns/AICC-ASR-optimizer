# 지표 정정: cue 보존 판정 기준

Round 6~8의 cue 손실 판정에 편향이 있었다. 이 문서가 정정된 수치의 기준이며, Round 6·7·8 본문 수치보다 우선한다.

## 무엇이 틀렸나

cue는 표준형 문자열로 채굴된다. 예를 들어 부정 cue는 `아니`로 저장된다. 그런데 실제 발화는 방언형 `아이가`, `아이다`, `아이고`다.

Round 6은 hypothesis에 `아니`가 어절 초에 나오는지만 봤다. 그래서 ASR이 방언형을 **정확히 받아썼는데도** 손실로 셌다. confirmation split 방언 arm 243건 중 40건이 여기 해당한다.

이 편향은 한쪽에만 걸린다. 대조군(평범한 어절)은 방언형과 표준형이 같아 이런 오판정이 생기지 않는다. 따라서 방언 대 평범 격차가 부풀려졌다.

Round 7의 오류 유형 분류는 반대 방향으로 어긋났다. 어절 전체 일치를 요구해서 어미만 다른 경우(`아니더라고요` 대 `아니더라구요`)를 소실로 셌다.

## 정정된 판정 기준

cue는 다음 셋 중 하나만 나와도 보존으로 본다.

1. `dialect_surface_preserved`: ASR이 방언형을 그대로 적었다.
2. `standard_normalised`: ASR이 같은 단어의 표준형을 적었다.
3. `cue_morpheme_only`: 어미가 달라졌지만 cue 형태소가 그대로 있다.

`cue_absent`만 AICC 피해다.

## 정정된 수치

### cue 손실 격차 (방언 arm − 평범 arm)

| Split | Model | 방언 arm 소실 | 평범 arm 소실 | 격차 | 95% CI |
|---|---|---:|---:|---:|---|
| confirmation | medium | 0.309 | 0.096 | +0.213 | [0.143, 0.282] |
| confirmation | large-v3 | 0.267 | 0.092 | +0.175 | [0.110, 0.241] |
| confirmation | wav2vec2-ko | 0.815 | 0.528 | +0.287 | [0.206, 0.364] |
| negation | medium | 0.202 | 0.043 | +0.159 | [0.093, 0.224] |
| negation | large-v3 | 0.202 | 0.043 | +0.159 | [0.094, 0.224] |
| negation | wav2vec2-ko | 0.634 | 0.405 | +0.228 | [0.126, 0.326] |

여섯 조합 모두 CI가 0을 제외한다. **결론은 유지되고 크기만 줄었다.** Round 6이 보고한 +0.396은 인용하면 안 된다. 정정 후 범위는 **+0.16 ~ +0.29**다.

### 방언 arm 결과 분해

| Split | Model | 방언형 그대로 | 표준형 정규화 | 형태소만 | 소실 |
|---|---|---:|---:|---:|---:|
| confirmation | medium | 0.292 | 0.350 | 0.049 | 0.309 |
| confirmation | large-v3 | 0.300 | 0.403 | 0.029 | 0.267 |
| confirmation | wav2vec2-ko | 0.107 | 0.037 | 0.041 | 0.815 |
| negation | medium | 0.350 | 0.366 | 0.082 | 0.202 |
| negation | large-v3 | 0.377 | 0.344 | 0.077 | 0.202 |
| negation | wav2vec2-ko | 0.175 | 0.077 | 0.115 | 0.634 |

Whisper 기준 방언 cue의 34~48%가 표준형 정규화 또는 형태소 보존으로 흡수된다. 의미가 살아남는다는 뜻이다.

### 코호트 (부산 − 기타 경상, 방언 arm)

| Split | medium | large-v3 | wav2vec2-ko |
|---|---|---|---|
| confirmation | +0.086 [-0.027, 0.201] | +0.014 [-0.094, 0.126] | -0.072 [-0.168, 0.024] |
| negation | +0.031 [-0.088, 0.141] | -0.014 [-0.130, 0.099] | -0.059 [-0.196, 0.079] |

여섯 검정 모두 0을 포함한다. 부산 특화 부정은 정정 후에도 유지된다.

### 대체 대 삭제 (Round 8 정정)

| Split | Model | 소실 | 대체 | 삭제 | context_lost | 판정된 것 중 대체 비율 |
|---|---|---:|---:|---:|---:|---:|
| confirmation | medium | 75 | 17 | 4 | 54 | 0.810 |
| confirmation | large-v3 | 65 | 11 | 9 | 45 | 0.550 |
| confirmation | wav2vec2-ko | 198 | 22 | 7 | 169 | 0.759 |
| negation | medium | 37 | 9 | 2 | 26 | 0.818 |
| negation | large-v3 | 37 | 5 | 5 | 27 | 0.500 |
| negation | wav2vec2-ko | 116 | 15 | 5 | 96 | 0.750 |

Round 8은 "여섯 조합 모두 대체가 삭제를 앞선다"고 적었으나, 정정 후 large-v3 negation은 5 대 5 동률이다. 정확한 서술은 **다섯 조합에서 대체가 앞서고 한 조합은 동률**이다. 판정률이 낮다는 한계는 그대로다.

## 영향을 받지 않는 결과

- Round 4의 방언 어절 대 비방언 어절 오류율(약 4배). 이 지표는 방언형과 표준형을 모두 정답으로 인정하고 있었다.
- Round 5의 발화 수준 영점. cue 위치 판정을 쓰지 않는다.
- 대체 표면이 반복되지 않는다는 Round 8의 관찰.

## 재현

```bash
uv run scripts/classify_cue_error_types.py \
  research/experiments/runs/aihub_119_cue_bearing_split \
  --output-dir research/experiments/runs/aihub_119_cue_error_types

uv run scripts/classify_cue_substitution.py \
  research/experiments/runs/aihub_119_cue_bearing_split \
  --output-dir research/experiments/runs/aihub_119_cue_substitution
```

negation split도 같은 명령에서 디렉터리만 바꾸면 된다.
