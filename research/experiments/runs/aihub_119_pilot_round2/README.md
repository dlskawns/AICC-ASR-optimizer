# Pilot Round 2: 클러스터 유의성, 모델 스케일, 메트릭 감사

> **정정 있음.** 이 문서의 어절 단위 오류율은 어절 경계를 보지 않는 판정으로 계산됐다. 정정된 수치는 [지표 정정](../aihub_119_metric_correction/README.md)을 따른다.

Round 1([pilot_conclusion_report.md](../aihub_119_dialect_attribution_probe/pilot_conclusion_report.md))은 `faster-whisper:medium` 단일 모델, unit 독립 가정 p-value, substring 기반 span 매칭에 의존했다. Round 2는 그 세 가지를 모두 다시 검증했다.

사람 검수는 아직 수행되지 않았다. 이 문서의 모든 수치는 자동 계산이며 gold가 아니다.

## 요약

세 가지가 바뀌었다.

1. utterance clustering을 반영해도 방언 효과는 살아남는다.
2. `large-v3`로 키워도 방언 격차는 닫히지 않는다.
3. 기존 critical-span 메트릭과 그 라벨은 신뢰할 수 없었고, 수정하니 결론이 뒤집힌 항목이 있다.

## 1. Clustered 유의성 재검정

unit을 독립으로 본 기존 p-value(1.10e-07)는 과신이다. 어절은 발화 안에 중첩되어 있다. 세 가지 방식으로 다시 검정했다. 상세는 [dialect_significance](../aihub_119_dialect_significance/README.md).

| Measure | medium | large-v3 |
|---|---:|---:|
| 방언 단위 오류율 | 0.455 | 0.409 |
| 비방언 단위 오류율 | 0.172 | 0.161 |
| 차이 | 0.283 | 0.248 |
| 차이 cluster bootstrap 95% CI | [0.169, 0.394] | [0.130, 0.367] |
| 오류율 비율 | 2.64x | 2.54x |
| utterance 층화 Mantel-Haenszel OR | 4.10 [2.19, 7.70] | 3.31 [1.82, 6.04] |
| within-utterance permutation p | <5.0e-05 | <5.0e-05 |

핵심: 발화 내부에서 방언 표지 플래그만 뒤섞는 permutation에서도 관측된 격차에 도달한 draw가 20000회 중 0회였다. 발화 난이도로는 설명되지 않는다.

다만 격차 전부가 방언 때문은 아니다. 방언 단위는 애초에 조금 더 어려운 발화에 몰려 있다. permutation의 null 평균이 0이 아니라 0.040(medium 기준, 원 격차의 14%)이며, 발화 구성으로 설명되지 않는 순수 방언 기여분은 0.243이다. large-v3에서는 0.216이다.

design effect는 medium 1.16, large-v3 1.38로 크지 않다. 즉 기존 p-value는 과신이었지만 결론을 뒤집을 정도는 아니었다.

## 2. 부산 vs 기타 경상: 여전히 근거 없음

| Model | Busan − 기타 경상 방언 단위 오류율 차이 | 95% CI |
|---|---:|---|
| medium | 0.033 | [-0.197, 0.263] |
| large-v3 | 0.006 | [-0.219, 0.223] |

두 모델 모두 0을 넉넉히 포함한다. 모델을 키우면 차이는 오히려 0.006까지 줄어든다. "부산 방언이 유독 어렵다"는 이 데이터로 주장할 수 없다.

## 3. 모델 스케일 ablation

`large-v3`는 medium 대비 전 구간에서 조금 낫다. 하지만 방언 격차의 CI는 여전히 0을 제외한다.

- 방언 단위 오류율: 0.455 → 0.409
- 비방언 단위 오류율: 0.172 → 0.161
- 격차: 0.283 → 0.248
- MH OR: 4.10 → 3.31

이것이 Round 2에서 가장 논문에 가까운 결과다.

> 방언 페널티는 모델 용량 부족의 산물이 아니다. Whisper-family 안에서 medium에서 large-v3로 키워도 격차는 축소될 뿐 사라지지 않는다.

`large-v3`의 50개 클립 총 ASR 시간은 292초였다.

## 4. Critical-span 메트릭 감사

이 부분이 Round 2에서 가장 크게 바뀌었다. 상세는 [critical_span_preservation](../aihub_119_critical_span_preservation/README.md), [large-v3판](../aihub_119_critical_span_preservation_large_v3/README.md).

첫 시도는 span을 substring으로 대조했고, 세 종류의 아티팩트가 나왔다.

| 문제 | 잘못된 결과 | 원인 | 수정 후 |
|---|---|---|---|
| 금액 | amount 손실률 0.917 | 정답은 한자어 수사 표기, ASR은 아라비아 숫자 표기. 표기 체계만 다르고 값은 동일 | 숫자를 값으로 파싱 → 손실률 0.000 |
| 단음절 표지 | negation 손실률 0.059 | `안`, `네`, `못`이 무관한 단어 내부에 우연히 포함 | 어절 시작 매칭, 어중 매칭은 ambiguous로 분리 |
| intent_cue 라벨 | 15개 중 8개가 "보존" | weak preannotation이 일반 `-해지다` 활용형에서 해지 취소 cue를 substring으로 채굴 | reference 어절에 실재하지 않는 라벨을 phantom으로 제외 |

phantom label은 74개 중 16개(21.6%)였고, intent_cue 15개 중 10개가 여기 해당한다.

수정 후 결과(scorable 58개 기준):

| Measure | medium | large-v3 |
|---|---:|---:|
| strict loss rate | 0.103 [0.019, 0.203] | 0.069 [0.000, 0.161] |
| inclusive loss rate | 0.121 | 0.069 |
| amount 손실 | 0/10 | 0/10 |
| negation 손실 | 1/17 | 2/17 |
| confirmation 손실 | 3/13 | 2/13 |

방언 표지 span과 그 외 span의 대조는 dialect-marked가 4개뿐이라 underpowered로 표시했고 인용해서는 안 된다.

## 이번 라운드에서 말할 수 있게 된 claim

> AI-Hub 경상도 50발화 pilot에서, 발화 단위 클러스터링과 발화 내부 permutation을 적용한 뒤에도 `faster-whisper`의 방언 표지 어절 오류율은 비방언 어절보다 유의하게 높다(medium 2.64x, large-v3 2.54x). 이 격차는 `medium`에서 `large-v3`로 모델을 키워도 유지되므로 단순한 모델 용량 문제로 설명되지 않는다.

> 한국어 AICC critical-span 메트릭은 문자열 포함 관계로 만들 수 없다. 금액은 표기 정규화 때문에 손실이 과대 계상되고, 단음절 표지는 우연 일치 때문에 보존이 과대 계상되며, substring으로 채굴한 라벨 자체가 21.6% 오염되어 있었다.

## 아직 말하면 안 되는 claim

- 부산 방언이 기타 경상 방언보다 어렵다. (두 모델 모두 CI가 0을 포함)
- critical-span 손실률이 실제 AICC 업무 실패율이다. (weak label, 사람 검수 전)
- 방언 표지 span이 일반 span보다 더 많이 손실된다. (dialect-marked 4개, underpowered)
- Whisper가 한국어 특화 ASR보다 나쁘다. (한국어 baseline 미실행)
- 이 pilot이 speaker-independent 근거다. (아님)

## 드러난 구조적 리스크

AI-Hub 119는 contact-center 발화가 아니라 자유 대화다. 그래서 AICC critical span을 substring으로 채굴하면 해지·취소 같은 업무 cue가 일반 활용형에서 유령 라벨로 대량 생성된다. phantom filter는 라벨이 실재 어절을 가리키는지만 검사할 뿐, 그 어절이 업무적 의미를 가졌는지는 판정하지 못한다.

즉 "AICC condition" 축을 논문에서 주장하려면 둘 중 하나가 필요하다.

1. 실제 contact-center 유사 발화 소스를 확보한다.
2. 자유 대화에서 AICC-critical 사건을 뽑는 채굴 규칙을 substring 이상으로 정교화하고 사람 검수로 검증한다.

## 다음 작업

1. 16행 audio review packet 사람 검수 → 확정 harmful 집계.
2. 한국어 특화 ASR baseline 1종 추가.
3. speaker-independent split으로 확장(현재 validation WAV 843개 확보됨).
4. critical-span 라벨 채굴 규칙 재설계 후 재라벨.

## 재현 명령

```bash
uv run scripts/run_dialect_significance_tests.py \
  research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_medium.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_large_v3.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_dialect_significance

uv run scripts/analyze_critical_span_preservation.py \
  research/experiments/runs/aihub_119_pilot_review_packet/pilot_candidate_annotations.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_medium.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_critical_span_preservation
```

`large-v3` ASR은 `Systran/faster-whisper-large-v3`를 로컬 캐시에 받은 뒤 실행한다.

```bash
../japko/whisper_proto/.venv/bin/python scripts/run_faster_whisper_pilot_asr.py \
  research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_large_v3.local.jsonl \
  large-v3
```
