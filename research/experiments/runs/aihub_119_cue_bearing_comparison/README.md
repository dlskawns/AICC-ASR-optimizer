# Cue-Bearing Dialect Comparison

Round 5 compared utterances containing dialect marking anywhere against utterances containing none
and found no difference in AICC critical-span loss. That pointed to dialect fragility being local to
the dialect token, which predicts an effect when the cue word itself is the dialect-marked eojeol.

Each pair here is one speaker producing the same cue category twice: once on a dialect-marked eojeol,
once on a plain one. Speaker, recording, and cue category are fixed inside the pair.

Read the placebo line first. If non-dialect unit error differs between arms, the pairs differ in more
than the dialect marking of the cue word and the headline number cannot carry weight.

Labels are weak preannotations that no human has reviewed.

## faster_whisper_medium

- Pairs: 250 across 250 speakers
- Scorable cues: 250 dialect-marked arm, 250 plain arm
- Cue loss: 0.488 when the cue word is dialect-marked vs 0.092 when it is not
- Paired difference: +0.396, 95% CI [0.324, 0.464] — excludes zero
- Arm-swap permutation p: <5.000e-05
- Discordant pairs: 108 dialect-only vs 9 plain-only, McNemar p 1.303e-19
- Placebo, non-dialect unit error: 0.218 vs 0.204, difference +0.014 95% CI [-0.016, 0.043] — crosses zero

| Cue category | Pairs | Dialect-marked arm loss | Plain arm loss |
|---|---:|---:|---:|
| confirmation | 220 | 0.550 | 0.105 |
| negation | 30 | 0.033 | 0.000 |

## faster_whisper_large_v3

- Pairs: 250 across 250 speakers
- Scorable cues: 250 dialect-marked arm, 250 plain arm
- Cue loss: 0.436 when the cue word is dialect-marked vs 0.092 when it is not
- Paired difference: +0.344, 95% CI [0.276, 0.412] — excludes zero
- Arm-swap permutation p: <5.000e-05
- Discordant pairs: 96 dialect-only vs 10 plain-only, McNemar p 1.507e-16
- Placebo, non-dialect unit error: 0.194 vs 0.181, difference +0.013 95% CI [-0.014, 0.039] — crosses zero

| Cue category | Pairs | Dialect-marked arm loss | Plain arm loss |
|---|---:|---:|---:|
| confirmation | 220 | 0.495 | 0.105 |
| negation | 30 | 0.000 | 0.000 |

## wav2vec2_korean

- Pairs: 250 across 250 speakers
- Scorable cues: 250 dialect-marked arm, 250 plain arm
- Cue loss: 0.872 when the cue word is dialect-marked vs 0.524 when it is not
- Paired difference: +0.348, 95% CI [0.272, 0.420] — excludes zero
- Arm-swap permutation p: <5.000e-05
- Discordant pairs: 102 dialect-only vs 15 plain-only, McNemar p 1.855e-15
- Placebo, non-dialect unit error: 0.655 vs 0.634, difference +0.021 95% CI [-0.010, 0.053] — crosses zero

| Cue category | Pairs | Dialect-marked arm loss | Plain arm loss |
|---|---:|---:|---:|
| confirmation | 220 | 0.914 | 0.559 |
| negation | 30 | 0.567 | 0.267 |
