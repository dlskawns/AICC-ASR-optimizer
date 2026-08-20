# Cue Scoring By Alignment

Rounds 6 to 8 searched for a cue surface anywhere in the hypothesis. Unit scoring has already moved
to alignment; this brings the cue metrics onto the same standard. The reference eojeol sequence is
aligned to the hypothesis tokens and each cue is judged only against the token at its own position.

Five outcomes. Three preserve the business meaning: the dialect form written as spoken, the standard
form of the same word, or the cue morpheme surviving under different inflection. Two are damage:
the position holds some other word, or it holds nothing.

That last split is free here. Round 8 had to infer substitution from surviving neighbours and could
not resolve about two thirds of cases; the alignment states it directly.

Read the placebo line first. If non-dialect unit error differs between arms the pairing is suspect.

Labels are weak preannotations that no human has reviewed.

## faster_whisper_medium

- Pairs: 183 across 183 speakers

| Arm | Cues | Dialect kept | Normalised | Morpheme only | Substituted | Deleted | Damage rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 183 | 65 | 63 | 9 | 18 | 28 | 0.251 |
| cue word is plain | 183 | 146 | 0 | 5 | 2 | 30 | 0.175 |

- Damage gap: +0.077, 95% CI [-0.005, 0.158] — crosses zero
- Arm-swap permutation p: 8.450e-02
- Discordant pairs: 36 dialect-only vs 22 plain-only, McNemar p 8.783e-02
- Substitution share of damage: 0.391 dialect arm, 0.062 plain arm
- Distinct replacement surfaces, dialect arm: 12
- Placebo, non-dialect unit error: +0.011 95% CI [-0.027, 0.048] — crosses zero

## faster_whisper_large_v3

- Pairs: 183 across 183 speakers

| Arm | Cues | Dialect kept | Normalised | Morpheme only | Substituted | Deleted | Damage rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 183 | 69 | 61 | 10 | 9 | 34 | 0.235 |
| cue word is plain | 183 | 155 | 0 | 3 | 3 | 22 | 0.137 |

- Damage gap: +0.098, 95% CI [0.022, 0.175] — excludes zero
- Arm-swap permutation p: 1.750e-02
- Discordant pairs: 35 dialect-only vs 17 plain-only, McNemar p 1.840e-02
- Substitution share of damage: 0.209 dialect arm, 0.120 plain arm
- Distinct replacement surfaces, dialect arm: 9
- Placebo, non-dialect unit error: +0.021 95% CI [-0.016, 0.058] — crosses zero

## wav2vec2_korean

- Pairs: 183 across 183 speakers

| Arm | Cues | Dialect kept | Normalised | Morpheme only | Substituted | Deleted | Damage rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 183 | 36 | 10 | 13 | 85 | 39 | 0.678 |
| cue word is plain | 183 | 76 | 0 | 15 | 58 | 34 | 0.503 |

- Damage gap: +0.175, 95% CI [0.071, 0.279] — excludes zero
- Arm-swap permutation p: 1.500e-03
- Discordant pairs: 66 dialect-only vs 34 plain-only, McNemar p 1.935e-03
- Substitution share of damage: 0.685 dialect arm, 0.630 plain arm
- Distinct replacement surfaces, dialect arm: 75
- Placebo, non-dialect unit error: +0.033 95% CI [-0.005, 0.073] — crosses zero
