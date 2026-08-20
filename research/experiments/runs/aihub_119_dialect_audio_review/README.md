# Dialect ASR Audio Review Packet

Human/audio confirmation of the text-only semantic audit. Text-only audit is not gold; a dialect unit is only counted as an AICC-harmful ASR failure after a reviewer has heard the clip.

## Scope

- Audited dialect units in the pilot: 66
- Units in this packet: 16
- `potentially_harmful_semantic_shift`: 9
- `low_impact_discourse_or_hedge_loss`: 7
- Distinct utterances: 14
- Clips present: 16, missing: 0

`meaning_preserved_or_acceptable_normalization` units are excluded on purpose. They are the audit's low-risk bulk and would dominate reviewer time without changing the harmful-case count.

## Files

- `dialect_audio_review_sheet.local.tsv`: reviewer sheet, restricted, git-ignored.
- `dialect_audio_review_queue.local.jsonl`: same rows as JSONL, restricted, git-ignored.
- `dialect_audio_review_manifest.jsonl`: shareable metadata only, no transcript text and no dialect surface forms.
- `summary.json`: shareable counts.

## Reviewer Protocol

1. Play `clip_path` before reading `asr_hypothesis`, so the decision is anchored on audio.
2. Compare `dialect_unit` against what the ASR hypothesis says at that position.
3. Fill `reviewer_decision` with exactly one of:
   - `harmful`: the ASR output changes AICC-relevant meaning (negation, amount, date/time, entity, intent cue, slot).
   - `acceptable`: meaning survives; the difference is spelling, register, or a harmless normalization.
   - `artifact`: the reference label, the clip window, or the audio itself is at fault, not the ASR system.
   - `unclear`: audio is not decidable; do not guess.
4. Fill `reviewer_confidence` with `high`, `medium`, or `low`.
5. Use `reviewer_notes` for the AICC field at risk when the decision is `harmful`.

Leave a row blank rather than guessing. Blank rows stay `unreviewed` and are excluded from any harmful-case count.

## After Review

Summarize confirmed `harmful` units, then decide whether to freeze pilot semantic annotations. Until then, the paper-safe claim stays at the text-audit level: many dialect surface mismatches are acceptable normalizations, so AICC evaluation must isolate harmful semantic shifts rather than treat every dialect-surface mismatch as task failure.
