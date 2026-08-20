# Semantic-Critical Annotation Guideline

## Purpose

This annotation layer measures whether ASR errors preserve the information needed for AICC task success.

WER/CER remains useful, but every utterance used in the Busan-AICC benchmark must also mark business-critical spans.

## Required Fields

- `utterance_id`: stable local ID.
- `audio_path`: local-only path.
- `speaker_region`: Busan/Daegu/Ulsan/Gyeongbuk/Gyeongnam/unknown if available.
- `acoustic_condition`: clean, telephone_bandlimited, noise, overlap, fast_speech, call_real, unknown.
- `dialect_transcript`: dialect-preserving transcript.
- `standard_transcript`: standard Korean meaning-preserving transcript.
- `domain`: AICC domain.
- `intent`: task intent label.
- `slots`: named entities or task slots.
- `critical_spans`: spans where ASR errors can change the business outcome.

## Critical Span Categories

| Category | Examples | Risk |
| --- | --- | --- |
| negation | 안 된다, 못 한다, 없다, 아니다, 불가 | high |
| amount | 2만 원, 20만 원, 15만 원, 50만 원 | high |
| date_time | 9월 26일, 내일 오전, 다음 주 | high |
| entity | 상품명, 요금제, 지명, 사람명, 기관명 | medium-high |
| intent_cue | 해지, 변경, 환불, 결제, 배송 | high |
| confirmation | 맞다, 아니다, 그런 말 아니다 | high |

## Annotation Principle

Annotate what the contact-center system must not lose.

Example:

```json
{
  "utterance_id": "pilot-0001",
  "audio_path": "data/raw/aihub_gyeongsang_119/example.wav",
  "speaker_region": "Busan",
  "acoustic_condition": "telephone_bandlimited",
  "dialect_transcript": "해지 안 된다 캤나?",
  "standard_transcript": "해지가 안 된다고 했나요?",
  "domain": "cancellation",
  "intent": "ask_cancellation_availability",
  "slots": [
    {
      "name": "service_action",
      "value": "cancellation",
      "span_text": "해지"
    }
  ],
  "critical_spans": [
    {
      "span_text": "안 된다",
      "category": "negation",
      "business_risk": "high",
      "expected_asr_preservation": "must preserve negation"
    }
  ],
  "clarification_required": true
}
```

## ASR Error Labels

Use these when comparing ASR output to gold:

- `critical_span_deleted`
- `critical_span_substituted`
- `critical_span_inserted`
- `negation_flip`
- `amount_magnitude_error`
- `date_shift`
- `entity_substitution`
- `intent_flip`
- `dialect_ending_normalized_without_meaning_loss`
- `dialect_ending_changed_meaning`

## Reviewer-Safe Rule

Do not claim task success from WER alone. A result table is valid only if it includes at least one semantic-critical or downstream metric.

## Label-Only Review Pack Workflow

Before downloading audio, use the AI-Hub label-side taxonomy to build a small semantic review queue.

```bash
uv run scripts/build_semantic_review_pack.py \
  data/raw/aihub_gyeongsang_119 \
  research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz \
  --output-dir research/experiments/runs/aihub_119_semantic_review_pack
```

Annotators should fill:

- `domain`: one of the schema domains.
- `intent`: the AICC task intent implied by the utterance.
- `slots`: task entities such as service action, amount, date, location, product, or confirmation target.
- `critical_spans`: only spans whose ASR corruption can change the business outcome.

The `candidate_critical_spans` field is a hint from the dialect taxonomy and keyword rules. It is not a gold label.

The `.local.jsonl` queue contains restricted transcript text. Keep it local; use the manifest for shareable counts and audit references.

## Weak Preannotation Rule

Weak preannotations can be used to prioritize review, but never as final labels.

Accept a preannotated row as gold only after a reviewer checks:

- the span is genuinely business-critical in an AICC setting;
- the inferred `domain` and `intent` are not merely keyword artifacts;
- all amount/date/negation/confirmation spans that affect the task are covered;
- non-critical dialect variants are not mislabeled as semantic failures.

## Gold Freeze Rule

Gold freeze only includes rows where `review_status` is `accepted`.

Before setting `accepted`, the reviewer must edit `final_annotation` so that:

- `domain` and `intent` reflect the AICC task meaning;
- `critical_spans` contains only business-critical spans;
- `slots` are aligned with the accepted critical spans;
- `audio_path` remains empty until the matching audio subset is actually present locally.
