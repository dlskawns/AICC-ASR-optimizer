# Pilot Round 8: 잃은 cue는 무엇이 되는가

[Round 7](../aihub_119_pilot_round7/README.md)은 방언 cue의 실제 피해를 "방언 표면도 표준형도 없음"으로 정의했다. AICC 관점에서는 그 안에서 다시 갈린다.

- **삭제**: cue 자리가 비어 있다. 신호가 없다는 사실 자체를 하류에서 감지할 수 있다.
- **대체**: 다른 단어가 cue 자리를 차지한다. 하류는 확신에 찬 오답을 받는다.

Round 8은 둘을 나누고, 대체된 표면을 수집해 오류 패턴 사전이 만들어지는지 확인했다.

사람 검수는 여전히 수행되지 않았다. 모든 수치는 자동 계산이며 gold가 아니다.

## 방법

cue의 앞뒤 이웃 어절을 앵커로 쓴다. 양쪽 이웃이 hypothesis에 살아 있으면 그 사이에 있는 것이 cue가 변한 결과다. 사이가 비어 있으면 삭제다. 이웃까지 사라졌거나 간격이 3토큰을 넘으면 정렬을 믿을 수 없으므로 `context_lost`로 보고하고 둘 중 하나로 강제하지 않는다.

`context_lost`는 방법의 한계인 동시에 모델의 성질이기도 하다. 출력이 정답에서 멀리 표류하는 시스템은 앵커를 제공하지 못한다.

## 결과 1: 대체가 삭제를 압도한다

[cue_substitution](../aihub_119_cue_substitution/README.md) (confirmation 중심 split)

| Model | 방언 arm 소실 | 대체 | 삭제 | context_lost | 판정된 것 중 대체 비율 |
|---|---:|---:|---:|---:|---:|
| medium | 87 | 24 | 4 | 59 | 0.857 |
| large-v3 | 72 | 15 | 9 | 48 | 0.625 |
| wav2vec2-ko | 208 | 24 | 7 | 177 | 0.774 |

[negation_substitution](../aihub_119_negation_substitution/README.md) (negation split)

| Model | 방언 arm 소실 | 대체 | 삭제 | context_lost | 판정된 것 중 대체 비율 |
|---|---:|---:|---:|---:|---:|
| medium | 52 | 16 | 2 | 34 | 0.889 |
| large-v3 | 51 | 13 | 5 | 33 | 0.722 |
| wav2vec2-ko | 137 | 18 | 5 | 114 | 0.783 |

여섯 조합 모두 대체가 삭제보다 많고, 비율은 0.63~0.89다.

> 방언 cue가 망가질 때 ASR은 대체로 침묵하지 않는다. 다른 단어를 채워 넣는다. AICC 하류 입장에서는 "정보 없음"이 아니라 "잘못된 정보"를 받는다는 뜻이다.

이것이 이 프로젝트에서 downstream 위험을 가장 직접적으로 말해주는 지점이다. 삭제라면 신뢰도 임계값이나 결측 처리로 방어할 수 있지만, 대체는 그 방어를 통과한다.

## 결과 2: 오류 패턴 사전은 만들어지지 않는다

대체된 표면을 모아 반복 여부를 봤다.

| Split | Model | 대체 건수 | 서로 다른 표면 | 2회 이상 반복 | 최대 반복 |
|---|---|---:|---:|---:|---:|
| confirmation | medium | 24 | 21 | 2 | 3 |
| confirmation | large-v3 | 15 | 14 | 1 | 2 |
| confirmation | wav2vec2 | 24 | 24 | 0 | 1 |
| negation | medium | 16 | 15 | 1 | 2 |
| negation | large-v3 | 13 | 13 | 0 | 1 |
| negation | wav2vec2 | 18 | 18 | 0 | 1 |

대체 표면이 거의 전부 서로 다르다. 같은 방언 cue가 항상 같은 오답으로 굳어지는 현상은 관찰되지 않는다.

> 후처리 사전으로 고칠 수 있는 문제가 아니다. "이 방언형은 이 오답으로 바뀐다"는 매핑이 존재하지 않으므로, 대응은 음향/모델 수준이어야 한다. 이는 방언 적응이나 어휘 편향 같은 방법론적 방향을 지지하고, 규칙 기반 사후 교정을 배제한다.

## 남은 한계

- **판정률이 낮다.** 소실된 cue의 2/3 안팎이 `context_lost`다. medium 87건 중 59건, wav2vec2는 208건 중 177건이다. 판정된 부분집합은 주변 문맥이 살아남은 사례에 치우쳐 있을 수 있고, 그쪽이 상대적으로 쉬운 발화일 가능성이 있다.
- 따라서 대체 비율 0.63~0.89는 **정렬 가능한 사례에 한정된 값**이다. 전체 소실 사례로 일반화하려면 강제 정렬 기반 검증이 필요하다.
- wav2vec2의 높은 `context_lost`(85%)는 CTC 출력이 정서법상 정답에서 멀기 때문이며, 이 모델에서는 판정 자체가 신뢰도가 낮다.
- 대체 표면 수집 규모가 작다. 사전이 없다는 결론은 24건·15건 수준의 관찰에 기반하므로, 수백 건 규모에서 재확인해야 한다.
- 라벨은 weak이며 사람 검수 전이다.

## 이번 라운드에서 말할 수 있게 된 claim

> 방언 표지 cue가 소실될 때, 정렬 가능한 사례에서는 대체가 삭제를 크게 앞선다. 세 baseline과 두 cue 카테고리 여섯 조합 모두에서 대체 비율이 0.63~0.89다. AICC 하류가 받는 것은 결측이 아니라 오답이다.

> 대체 표면은 반복되지 않는다. 관찰된 대체 중 2회 이상 나타난 표면은 여섯 조합을 합쳐 4건뿐이다. 방언 cue 오류를 사후 매핑 사전으로 교정하는 접근은 이 데이터로 지지되지 않는다.

## 아직 말하면 안 되는 claim

- 대체 비율을 전체 소실 사례의 값으로 인용하기. 2/3가 `context_lost`이며 판정 부분집합은 편향 가능성이 있다.
- wav2vec2의 대체/삭제 비율. 판정률 15%에 불과하다.
- 대체가 항상 의미를 뒤집는다. 대체 단어가 의미상 무해한 경우가 섞여 있을 수 있고, 이번 분류는 그것을 판정하지 않는다.
- 사전이 존재하지 않는다는 결론의 확정. 관찰 규모가 작다.

## 다음 작업

1. 강제 정렬 기반으로 `context_lost`를 줄여 판정률을 높이기.
2. 대체 단어가 의미를 뒤집는지 보존하는지 별도 판정. 현재는 "cue가 아닌 무언가"까지만 본다.
3. 대체 사례를 수백 건 규모로 확대해 사전 부재 결론 재확인.
4. 16행 audio review 사람 검수. 남은 유일한 사람 작업이다.

## 재현 명령

```bash
uv run scripts/classify_cue_substitution.py \
  research/experiments/runs/aihub_119_cue_bearing_split \
  --output-dir research/experiments/runs/aihub_119_cue_substitution

uv run scripts/classify_cue_substitution.py \
  research/experiments/runs/aihub_119_negation_cue_split \
  --output-dir research/experiments/runs/aihub_119_negation_substitution
```

대체 표면 목록은 각 출력 디렉터리의 `cue_substitution_cases.local.jsonl`에 있으며 로컬 전용이다.
