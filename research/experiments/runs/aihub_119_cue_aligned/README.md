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

- Pairs: 243 across 243 speakers

| Arm | Cues | Dialect kept | Normalised | Morpheme only | Substituted | Deleted | Damage rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 243 | 72 | 80 | 7 | 36 | 48 | 0.346 |
| cue word is plain | 243 | 204 | 0 | 11 | 8 | 20 | 0.115 |

- Damage gap: +0.230, 95% CI [0.156, 0.305] — excludes zero
- Arm-swap permutation p: <5.000e-05
- Discordant pairs: 75 dialect-only vs 19 plain-only, McNemar p 1.405e-08
- Substitution share of damage: 0.429 dialect arm, 0.286 plain arm
- Distinct replacement surfaces, dialect arm: 23
- Placebo, non-dialect unit error: +0.022 95% CI [-0.010, 0.055] — crosses zero

## faster_whisper_large_v3

- Pairs: 243 across 243 speakers

| Arm | Cues | Dialect kept | Normalised | Morpheme only | Substituted | Deleted | Damage rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 243 | 72 | 96 | 5 | 22 | 48 | 0.288 |
| cue word is plain | 243 | 209 | 0 | 7 | 7 | 20 | 0.111 |

- Damage gap: +0.177, 95% CI [0.111, 0.247] — excludes zero
- Arm-swap permutation p: <5.000e-05
- Discordant pairs: 60 dialect-only vs 17 plain-only, McNemar p 1.698e-06
- Substitution share of damage: 0.314 dialect arm, 0.259 plain arm
- Distinct replacement surfaces, dialect arm: 19
- Placebo, non-dialect unit error: +0.017 95% CI [-0.013, 0.047] — crosses zero

## wav2vec2_korean

- Pairs: 243 across 243 speakers

| Arm | Cues | Dialect kept | Normalised | Morpheme only | Substituted | Deleted | Damage rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 243 | 31 | 7 | 5 | 145 | 55 | 0.823 |
| cue word is plain | 243 | 81 | 0 | 22 | 106 | 34 | 0.576 |

- Damage gap: +0.247, 95% CI [0.169, 0.325] — excludes zero
- Arm-swap permutation p: <5.000e-05
- Discordant pairs: 86 dialect-only vs 26 plain-only, McNemar p 2.476e-08
- Substitution share of damage: 0.725 dialect arm, 0.757 plain arm
- Distinct replacement surfaces, dialect arm: 121
- Placebo, non-dialect unit error: +0.004 95% CI [-0.029, 0.036] — crosses zero
