# Dialect ASR Text-Only Error Audit

## 결론

문제정의는 더 선명해졌다. `faster-whisper:medium`은 방언 표지 어절의 표면을 자주 보존하지 못한다. 그러나 그 전부가 AICC 의미 손상은 아니다.

자동 evaluator에서는 66개 방언 표지 어절 중 30개가 `missing_or_substituted`로 잡혔다. 하지만 text-only 의미 감사로 다시 보면, 잠재적 의미 손상 후보는 9개다.

따라서 연구 질문은 다음처럼 좁히는 것이 맞다.

> 경상/부산 방언 표지 어절은 범용 ASR에서 표면 보존이 약하고, 그중 일부는 의미 손상 후보로 이어진다. AICC TA에서는 방언 표면 오류 전체가 아니라 harmful semantic shift를 분리해 측정해야 한다.

## Audit Result

| Status | Units | Rate |
|---|---:|---:|
| Meaning preserved or acceptable normalization | 50 | 75.8% |
| Low-impact discourse or hedge loss | 7 | 10.6% |
| Potentially harmful semantic shift | 9 | 13.6% |

| Comparison | Units | Rate |
|---|---:|---:|
| Raw automatic missing/substituted | 30 | 45.5% |
| Text-audit potentially harmful | 9 | 13.6% |

## Why This Matters

The first probe answered whether dialect-marked units are harder for ASR. Yes: they are.

This audit answers whether every dialect-surface error should be counted as semantic failure. No: many are acceptable normalizations.

Common acceptable cases:

- dialect colloquial spelling normalized into common Korean surface;
- dialect ending normalized into standard polite ending;
- repeated hedge markers collapsed without changing the core meaning;
- dialect surface preserved even when not standard.

Potentially harmful candidates are concentrated in cases where ASR changes reference, predicate meaning, negation-like discourse force, or tense/modality.

## Category View

| Category | Meaning preserved | Low impact | Potentially harmful |
|---|---:|---:|---:|
| lexical replacement | 13 | 2 | 3 |
| ending/particle variant | 11 | 4 | 2 |
| prefix/stem variant | 12 | 1 | 3 |
| vowel shift | 14 | 0 | 1 |

The earlier category plot showed lexical replacement had the highest raw surface mismatch. After text audit, lexical replacement remains important, but not all lexical replacement mismatches are harmful. Many are degree-adverb normalizations.

## Research Implication

The novelty should not be framed as only “dialect increases WER.”

The stronger framing is:

1. Dialect-marked units are ASR-fragile.
2. A large part of that fragility is surface normalization rather than meaning loss.
3. The real AICC risk is the subset that causes semantic shift in reference, predicate, negation, amount/date/time, or intent cues.
4. Therefore, the paper needs a semantic-critical dialect ASR metric, not just WER/CER.

## Current Claim Strength

Safe claim:

> In the 50-utterance pilot, dialect-marked units show high ASR surface instability, but text-only audit suggests only 13.6% of dialect-marked units are potentially harmful semantic shifts. This justifies a semantic-critical error taxonomy for dialect ASR.

Not safe yet:

- that all dialect ASR errors harm AICC TA;
- that Busan dialect is uniquely harder than other Gyeongsang dialect;
- that lexical replacement always causes semantic failure;
- that text-only audit is final gold.

## Next Action

The next required action is human/audio review of the 9 potentially harmful candidates and 7 low-impact candidates. Text-only audit cannot resolve whether the ASR missed acoustically important content or whether the label segmentation/evaluator caused a false alarm.

Artifacts:

- Local audit rows: `dialect_asr_text_audit.local.jsonl`
- Shareable no-transcript audit manifest: `dialect_asr_text_audit_manifest.jsonl`
- Audit summary: `dialect_asr_text_audit_summary.json`
