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

- Pairs: 281 across 184 speakers

| Arm | Cues | Dialect kept | Normalised | Morpheme only | Substituted | Deleted | Damage rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 281 | 104 | 92 | 15 | 27 | 43 | 0.249 |
| cue word is plain | 281 | 226 | 0 | 5 | 5 | 45 | 0.178 |

- Damage gap: +0.071, 95% CI [0.003, 0.142] — excludes zero
- Arm-swap permutation p: 6.010e-02
- Discordant pairs: 56 dialect-only vs 36 plain-only, McNemar p 4.760e-02
- Substitution share of damage: 0.386 dialect arm, 0.100 plain arm
- Distinct replacement surfaces, dialect arm: 19
- Placebo, non-dialect unit error: +0.017 95% CI [-0.013, 0.047] — crosses zero

## faster_whisper_large_v3

- Pairs: 281 across 184 speakers

| Arm | Cues | Dialect kept | Normalised | Morpheme only | Substituted | Deleted | Damage rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 281 | 110 | 92 | 14 | 15 | 50 | 0.231 |
| cue word is plain | 281 | 244 | 0 | 3 | 4 | 30 | 0.121 |

- Damage gap: +0.110, 95% CI [0.045, 0.176] — excludes zero
- Arm-swap permutation p: 1.700e-03
- Discordant pairs: 53 dialect-only vs 22 plain-only, McNemar p 5.320e-04
- Substitution share of damage: 0.231 dialect arm, 0.118 plain arm
- Distinct replacement surfaces, dialect arm: 15
- Placebo, non-dialect unit error: +0.034 95% CI [0.005, 0.064] — EXCLUDES ZERO, matching is suspect

## wav2vec2_korean

- Pairs: 281 across 184 speakers

| Arm | Cues | Dialect kept | Normalised | Morpheme only | Substituted | Deleted | Damage rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 281 | 55 | 13 | 24 | 131 | 58 | 0.673 |
| cue word is plain | 281 | 121 | 0 | 20 | 80 | 60 | 0.498 |

- Damage gap: +0.174, 95% CI [0.085, 0.260] — excludes zero
- Arm-swap permutation p: 2.500e-04
- Discordant pairs: 101 dialect-only vs 52 plain-only, McNemar p 1.042e-04
- Substitution share of damage: 0.693 dialect arm, 0.571 plain arm
- Distinct replacement surfaces, dialect arm: 109
- Placebo, non-dialect unit error: +0.022 95% CI [-0.011, 0.055] — crosses zero
