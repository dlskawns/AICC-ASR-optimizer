# AI-Hub 119 Gold Readiness

## Decision

사전 데이터 분석은 필요했고 완료했다. 기존 510개 semantic review queue는 방언 카테고리 균형은 좋지만 AICC critical span 균형이 부족했다. 특히 weak preannotation 기준 `amount`, `date_time`, `intent_cue`가 너무 적었다.

전체 AI-Hub 119 validation labels에서 방언 표시 어절이 있으면서 critical cue가 있는 발화를 다시 채굴했고, 398개 local review 후보를 만들었다. 이 후보들은 schema-valid weak preannotation으로 변환됐지만 gold는 아니다.

## Current Coverage

| Metric | Value |
|---|---:|
| Critical-span candidate rows | 398 |
| Schema-valid weak preannotations | 398 |
| Schema errors | 0 |
| Busan selected rows | 198 |
| Gyeongsang-other selected rows | 200 |
| Rows with audio path | 0 |

Critical span counts:

- `negation`: 178
- `confirmation`: 174
- `amount`: 92
- `date_time`: 87
- `intent_cue`: 83

## Needed Items

1. Human-reviewed gold annotations from `weak_semantic_preannotations.local.jsonl`.
2. Audio paths for only the frozen gold subset.
3. AICC domain grounding from ClovaCall or internal task labels, because AI-Hub 119 is not a contact-center corpus.
4. A speaker/session split key; file/session split is currently the safest fallback.
5. ASR outputs from baseline models after audio subset download.

## Data Download Decision

Do not download the full audio corpus yet. Freeze the label-side gold subset first, then download only matching source audio if AI-Hub file keys allow it.
