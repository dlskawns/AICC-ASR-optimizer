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
| cue word is dialect-marked | 243 | 0.292 | 0.350 | 0.049 | 0.309 |
| cue word is plain | 250 | 0.836 | 0.000 | 0.068 | 0.096 |

- Genuine cue loss gap: +0.213, 95% CI [0.143, 0.282] — excludes zero
- Busan minus other Gyeongsang, dialect arm: +0.086, 95% CI [-0.027, 0.201] — crosses zero (139 vs 104 cues)

| Cue category, dialect arm | Cues | Dialect surface kept | Normalised | Absent |
|---|---:|---:|---:|---:|
| confirmation | 214 | 0.262 | 0.341 | 0.047 | 0.350 |
| negation | 29 | 0.517 | 0.414 | 0.069 | 0.000 |

## faster_whisper_large_v3

| Arm | Cues | Dialect surface kept | Normalised to standard | Cue morpheme only | Cue absent |
|---|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 243 | 0.300 | 0.403 | 0.029 | 0.267 |
| cue word is plain | 250 | 0.852 | 0.000 | 0.056 | 0.092 |

- Genuine cue loss gap: +0.175, 95% CI [0.110, 0.241] — excludes zero
- Busan minus other Gyeongsang, dialect arm: +0.014, 95% CI [-0.094, 0.126] — crosses zero (139 vs 104 cues)

| Cue category, dialect arm | Cues | Dialect surface kept | Normalised | Absent |
|---|---:|---:|---:|---:|
| confirmation | 214 | 0.271 | 0.407 | 0.023 | 0.299 |
| negation | 29 | 0.517 | 0.379 | 0.069 | 0.034 |

## wav2vec2_korean

| Arm | Cues | Dialect surface kept | Normalised to standard | Cue morpheme only | Cue absent |
|---|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 243 | 0.107 | 0.037 | 0.041 | 0.815 |
| cue word is plain | 250 | 0.348 | 0.000 | 0.124 | 0.528 |

- Genuine cue loss gap: +0.287, 95% CI [0.206, 0.364] — excludes zero
- Busan minus other Gyeongsang, dialect arm: -0.072, 95% CI [-0.168, 0.024] — crosses zero (139 vs 104 cues)

| Cue category, dialect arm | Cues | Dialect surface kept | Normalised | Absent |
|---|---:|---:|---:|---:|
| confirmation | 214 | 0.103 | 0.023 | 0.028 | 0.846 |
| negation | 29 | 0.138 | 0.138 | 0.138 | 0.586 |
