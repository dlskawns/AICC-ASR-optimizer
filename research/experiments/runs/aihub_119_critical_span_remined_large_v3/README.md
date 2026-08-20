# AICC Critical Span Preservation

Model: `faster-whisper:large-v3`

Dialect unit error rates measure surface movement. This run measures something closer to the AICC task:
whether the ASR hypothesis still carries the annotated business-critical spans - negation, confirmation,
intent cue, amount, date/time.

**Label status: `weak_preannotation_not_gold`.** The critical spans come from weak preannotations that no
human has reviewed, so these rates size the problem; they do not settle it.

## Why Plain Substring Matching Was Rejected

A first pass scored spans by substring containment and produced three artifacts:

- Amount spans looked catastrophic. The reference transcribes amounts in Sino-Korean numerals while the
  ASR emits Arabic numerals, so a string comparison reported loss where the value was identical.
  Corrected, amount loss goes to zero.
- Single-syllable spans looked perfect. Markers such as `안`, `네`, `못` occur inside unrelated words, so a
  string comparison reported preservation that the audio does not support.
- Some spans were never business events at all. The weak preannotations were themselves mined by
  substring, so the cancellation cue `해지` was harvested out of ordinary `-해지다` verb forms that carry
  no cancellation meaning. Those labels are reported here as `phantom_label` and excluded from every rate.

This run parses numerals to values, checks that each label names a real eojeol in the reference, and
grades every remaining match by eojeol boundary. A mid-eojeol hit is reported as `substring_only` rather
than being counted as either preserved or lost. The correction is itself a finding: neither a Korean AICC
span metric nor its label set can be built from raw string containment.

## Headline

- Utterances: 43
- Labelled critical spans: 56
- Phantom labels removed: 1 (1.8% of labelled spans)
- Scorable critical spans: 55
- Match types: {"eojeol_initial": 41, "numeral_equivalent": 10, "absent": 4, "phantom_label": 1}
- Strict loss rate (`absent` only): 0.073, utterance bootstrap 95% CI [0.000, 0.167]
- Inclusive loss rate (`absent` plus ambiguous): 0.073

The two rates bound the damage. The truth needs audio review of the ambiguous spans.

## Loss by Category

| Category | Labelled | Phantom | Scorable | Preserved | Ambiguous | Absent | Strict loss rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| negation | 17 | 0 | 17 | 15 | 0 | 2 | 0.118 |
| date_time | 13 | 0 | 13 | 13 | 0 | 0 | 0.000 |
| amount | 11 | 1 | 10 | 10 | 0 | 0 | 0.000 |
| confirmation | 10 | 0 | 10 | 8 | 0 | 2 | 0.200 |
| intent_cue | 5 | 0 | 5 | 5 | 0 | 0 | 0.000 |

## Dialect Marking Contrast

- Dialect-marked critical spans: 4, strict loss rate 0.000
- Other critical spans: 51, strict loss rate 0.078
- Difference: -0.078, utterance bootstrap 95% CI [-0.179, 0.000] — crosses zero
- **Underpowered.** Only 4 dialect-marked spans across 3 utterances survive the phantom-label filter, so the
  interval reflects repeated resampling of a few observations, not a dialect effect. Do not cite it.

## Open Method Limits

- An eojeol-initial hit still ignores position, so a marker recognised in the wrong clause counts as preserved.
- Numeral equality ignores unit words, so an amount and a count sharing the same number compare equal.
- The phantom-label filter only checks that the label names a real eojeol. It cannot tell whether that
  eojeol carried a business meaning, and this corpus is spontaneous conversation rather than contact-centre
  speech, so the surviving label set is still weak.
- Confidence intervals resample utterances, not spans.

The span-level case file is local-only because it carries transcript surfaces.
