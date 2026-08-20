# Cue Error Types

Round 6 measured how often a dialect-marked cue word goes missing from the hypothesis. That number
mixes two outcomes a contact centre would treat very differently: the ASR writing the standard form
of the same cue, where the business meaning survives, and the cue disappearing outright, where it
does not. This run separates them.

Three outcomes preserve the business meaning and one does not. `dialect_surface_preserved` means the
ASR wrote the dialect form as spoken. `standard_normalised` means it wrote the standard form of the same
word. `cue_morpheme_only` means the inflection changed but the cue morpheme is plainly there. Only
`cue_absent` is AICC damage.

Accepting all three matters. Matching the canonical cue string alone scores a perfectly transcribed
dialect form as a loss, because the mined cue carries the standard spelling, and that bias falls only on
the dialect arm. Matching the full eojeol alone scores an inflectional variant as a loss.

The cohort line re-tests the Busan-versus-other question at cue level, where round 4 could only test
it at whole-utterance level.

Labels are weak preannotations that no human has reviewed.

## faster_whisper_medium

| Arm | Cues | Dialect surface kept | Normalised to standard | Cue morpheme only | Cue absent |
|---|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 183 | 0.350 | 0.366 | 0.082 | 0.202 |
| cue word is plain | 185 | 0.914 | 0.000 | 0.043 | 0.043 |

- Genuine cue loss gap: +0.159, 95% CI [0.093, 0.224] — excludes zero
- Busan minus other Gyeongsang, dialect arm: +0.031, 95% CI [-0.088, 0.141] — crosses zero (102 vs 81 cues)

| Cue category, dialect arm | Cues | Dialect surface kept | Normalised | Absent |
|---|---:|---:|---:|---:|
| negation | 183 | 0.350 | 0.366 | 0.082 | 0.202 |

## faster_whisper_large_v3

| Arm | Cues | Dialect surface kept | Normalised to standard | Cue morpheme only | Cue absent |
|---|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 183 | 0.377 | 0.344 | 0.077 | 0.202 |
| cue word is plain | 185 | 0.903 | 0.000 | 0.054 | 0.043 |

- Genuine cue loss gap: +0.159, 95% CI [0.094, 0.224] — excludes zero
- Busan minus other Gyeongsang, dialect arm: -0.014, 95% CI [-0.130, 0.099] — crosses zero (102 vs 81 cues)

| Cue category, dialect arm | Cues | Dialect surface kept | Normalised | Absent |
|---|---:|---:|---:|---:|
| negation | 183 | 0.377 | 0.344 | 0.077 | 0.202 |

## wav2vec2_korean

| Arm | Cues | Dialect surface kept | Normalised to standard | Cue morpheme only | Cue absent |
|---|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 183 | 0.175 | 0.077 | 0.115 | 0.634 |
| cue word is plain | 185 | 0.492 | 0.000 | 0.103 | 0.405 |

- Genuine cue loss gap: +0.228, 95% CI [0.126, 0.326] — excludes zero
- Busan minus other Gyeongsang, dialect arm: -0.059, 95% CI [-0.196, 0.079] — crosses zero (102 vs 81 cues)

| Cue category, dialect arm | Cues | Dialect surface kept | Normalised | Absent |
|---|---:|---:|---:|---:|
| negation | 183 | 0.175 | 0.077 | 0.115 | 0.634 |
