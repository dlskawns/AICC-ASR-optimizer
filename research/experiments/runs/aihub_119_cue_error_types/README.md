# Cue Error Types

Round 6 measured how often a dialect-marked cue word goes missing from the hypothesis. That number
mixes two outcomes a contact centre would treat very differently: the ASR writing the standard form
of the same cue, where the business meaning survives, and the cue disappearing outright, where it
does not. This run separates them.

`standard_normalised` is not damage. Only `cue_absent` is.

The cohort line re-tests the Busan-versus-other question at cue level, where round 4 could only test
it at whole-utterance level.

Labels are weak preannotations that no human has reviewed.

## faster_whisper_medium

| Arm | Cues | Dialect surface kept | Normalised to standard | Cue absent |
|---|---:|---:|---:|---:|
| cue word is dialect-marked | 243 | 0.292 | 0.350 | 0.358 |
| cue word is plain | 250 | 0.836 | 0.000 | 0.164 |

- Genuine cue loss gap: +0.194, 95% CI [0.117, 0.268] — excludes zero
- Busan minus other Gyeongsang, dialect arm: +0.105, 95% CI [-0.015, 0.227] — crosses zero (139 vs 104 cues)

| Cue category, dialect arm | Cues | Dialect surface kept | Normalised | Absent |
|---|---:|---:|---:|---:|
| confirmation | 214 | 0.262 | 0.341 | 0.397 |
| negation | 29 | 0.517 | 0.414 | 0.069 |

## faster_whisper_large_v3

| Arm | Cues | Dialect surface kept | Normalised to standard | Cue absent |
|---|---:|---:|---:|---:|
| cue word is dialect-marked | 243 | 0.300 | 0.403 | 0.296 |
| cue word is plain | 250 | 0.852 | 0.000 | 0.148 |

- Genuine cue loss gap: +0.148, 95% CI [0.075, 0.221] — excludes zero
- Busan minus other Gyeongsang, dialect arm: +0.014, 95% CI [-0.101, 0.129] — crosses zero (139 vs 104 cues)

| Cue category, dialect arm | Cues | Dialect surface kept | Normalised | Absent |
|---|---:|---:|---:|---:|
| confirmation | 214 | 0.271 | 0.407 | 0.322 |
| negation | 29 | 0.517 | 0.379 | 0.103 |

## wav2vec2_korean

| Arm | Cues | Dialect surface kept | Normalised to standard | Cue absent |
|---|---:|---:|---:|---:|
| cue word is dialect-marked | 243 | 0.107 | 0.037 | 0.856 |
| cue word is plain | 250 | 0.348 | 0.000 | 0.652 |

- Genuine cue loss gap: +0.204, 95% CI [0.131, 0.277] — excludes zero
- Busan minus other Gyeongsang, dialect arm: -0.050, 95% CI [-0.134, 0.039] — crosses zero (139 vs 104 cues)

| Cue category, dialect arm | Cues | Dialect surface kept | Normalised | Absent |
|---|---:|---:|---:|---:|
| confirmation | 214 | 0.103 | 0.023 | 0.874 |
| negation | 29 | 0.138 | 0.138 | 0.724 |
