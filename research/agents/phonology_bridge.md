# phonology_bridge

TASK: Connect Korean phonology, allophone modeling, and dialect ASR errors.

## Required Distinctions

- Allophone is not the same as dialect.
- Grapheme, phoneme, allophone, acoustic realization must be separated.
- Korean phonological rules and Busan/Gyeongsang dialect phenomena should be tied to actual ASR error observations, not assumed.

## Method Candidates

- Phoneme-aware auxiliary loss.
- Selective allophone auxiliary head.
- Dialect-conditioned adapter.
- Pronunciation augmentation.
- Error-type-aware reranker.

## Output

```text
Verdict:
Evidence:
Claims:
Open Risks:
Next Leads:
```

For each proposed phonological feature, state why it should affect ASR, what data can label it, and what ablation would falsify it.
