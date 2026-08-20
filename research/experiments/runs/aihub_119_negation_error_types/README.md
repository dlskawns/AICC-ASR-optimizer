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
| cue word is dialect-marked | 183 | 0.350 | 0.366 | 0.284 |
| cue word is plain | 185 | 0.914 | 0.000 | 0.086 |

- Genuine cue loss gap: +0.198, 95% CI [0.121, 0.274] — excludes zero
- Busan minus other Gyeongsang, dialect arm: +0.089, 95% CI [-0.041, 0.217] — crosses zero (102 vs 81 cues)

| Cue category, dialect arm | Cues | Dialect surface kept | Normalised | Absent |
|---|---:|---:|---:|---:|
| negation | 183 | 0.350 | 0.366 | 0.284 |

## faster_whisper_large_v3

| Arm | Cues | Dialect surface kept | Normalised to standard | Cue absent |
|---|---:|---:|---:|---:|
| cue word is dialect-marked | 183 | 0.377 | 0.344 | 0.279 |
| cue word is plain | 185 | 0.903 | 0.000 | 0.097 |

- Genuine cue loss gap: +0.181, 95% CI [0.105, 0.258] — excludes zero
- Busan minus other Gyeongsang, dialect arm: +0.013, 95% CI [-0.118, 0.141] — crosses zero (102 vs 81 cues)

| Cue category, dialect arm | Cues | Dialect surface kept | Normalised | Absent |
|---|---:|---:|---:|---:|
| negation | 183 | 0.377 | 0.344 | 0.279 |

## wav2vec2_korean

| Arm | Cues | Dialect surface kept | Normalised to standard | Cue absent |
|---|---:|---:|---:|---:|
| cue word is dialect-marked | 183 | 0.175 | 0.077 | 0.749 |
| cue word is plain | 185 | 0.492 | 0.000 | 0.508 |

- Genuine cue loss gap: +0.241, 95% CI [0.143, 0.333] — excludes zero
- Busan minus other Gyeongsang, dialect arm: -0.119, 95% CI [-0.241, 0.007] — crosses zero (102 vs 81 cues)

| Cue category, dialect arm | Cues | Dialect surface kept | Normalised | Absent |
|---|---:|---:|---:|---:|
| negation | 183 | 0.175 | 0.077 | 0.749 |
