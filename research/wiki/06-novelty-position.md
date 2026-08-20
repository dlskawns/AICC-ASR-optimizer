# Novelty Position

## Current Novelty Grade

**Yellow-green.** The research direction is viable, but only if the scope is tightened around AICC semantic-critical robustness.

## What Is Not Novel Enough

- Busan/Gyeongsang ASR error analysis alone.
- Whisper fine-tuning on AI-Hub dialect data.
- Dialect-specific LoRA/adapters.
- Generic ASR-robust SLU.
- N-best ASR correction.
- Korean ASR error explainability in general.

## Surviving Gap

No verified first-wave source simultaneously covers all of:

```text
Korean Busan/Gyeongsang dialect
  + contact-center/telephone acoustic condition
  + semantic-critical error taxonomy
  + downstream AICC TA intent/slot/task-success evaluation
  + method optimized for critical semantic loss rather than only WER
```

This is the gap the lab should defend.

## Strong Method Candidates

### Candidate A: Selective Dialectal Allophone Auxiliary ASR

Core:

```text
audio encoder
  -> transcript CTC/decoder loss
  -> selective allophone/phonology auxiliary loss
  -> semantic-critical error analysis
```

Novelty condition:

- Select only phonological/allophonic distinctions that are empirically overrepresented in Busan/Gyeongsang ASR errors.
- Show improvement on semantic-critical categories, not only global WER.

Risk:

- Korean allophone ASR exists; the novelty is not allophone use itself.

### Candidate B: Semantic-Critical Dialect ASR Objective

Core:

```text
ASR loss + lambda * critical-span preservation loss
```

Critical spans:

- negation.
- amount.
- date/time.
- product/entity.
- intent cue.

Novelty condition:

- Demonstrate that similar WER models differ in downstream AICC success.
- Optimize explicitly for those differences.

Risk:

- Needs reliable annotation of critical spans.

### Candidate C: N-best Critical-Span Clarification Policy

Core:

```text
ASR N-best/confidence
  -> detect low-margin critical span ambiguity
  -> rerank or ask clarification
  -> TA only when risk is acceptable
```

Novelty condition:

- Not just N-best correction; use AICC-specific cost-sensitive ambiguity handling.

Risk:

- If true transcript is absent from N-best, recovery is impossible.

## Recommended First Paper

Title candidate:

**Semantic-Critical Dialect Robustness for Korean Contact-Center Speech Understanding**

Main contribution:

1. A benchmark/protocol for Korean Gyeongsang/Busan dialect speech under contact-center acoustic shift.
2. A semantic-critical ASR error taxonomy for AICC.
3. Evidence that WER underestimates downstream harm.
4. A first method: selective phonological auxiliary learning or critical-span-aware reranking.

## Target Venues

- Interspeech or ICASSP if method is primarily ASR/acoustic/phonological.
- ACL/EMNLP Findings if the strongest contribution is speech-to-TA evaluation and downstream robustness.
- ACL/EMNLP main only if there is a clean new benchmark plus strong method and ablations.
