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

- Pairs: 185 across 185 speakers
- Scorable cues: 185 dialect-marked arm, 185 plain arm
- Cue loss: 0.265 when the cue word is dialect-marked vs 0.038 when it is not
- Paired difference: +0.227, 95% CI [0.162, 0.292] — excludes zero
- Arm-swap permutation p: <5.000e-05
- Discordant pairs: 45 dialect-only vs 3 plain-only, McNemar p 3.262e-09
- Placebo, non-dialect unit error: 0.147 vs 0.133, difference +0.014 95% CI [-0.013, 0.041] — crosses zero

| Cue category | Pairs | Dialect-marked arm loss | Plain arm loss |
|---|---:|---:|---:|
| negation | 185 | 0.265 | 0.038 |

## faster_whisper_large_v3

- Pairs: 185 across 185 speakers
- Scorable cues: 185 dialect-marked arm, 185 plain arm
- Cue loss: 0.265 when the cue word is dialect-marked vs 0.032 when it is not
- Paired difference: +0.232, 95% CI [0.168, 0.303] — excludes zero
- Arm-swap permutation p: <5.000e-05
- Discordant pairs: 46 dialect-only vs 3 plain-only, McNemar p 1.973e-09
- Placebo, non-dialect unit error: 0.151 vs 0.140, difference +0.011 95% CI [-0.016, 0.039] — crosses zero

| Cue category | Pairs | Dialect-marked arm loss | Plain arm loss |
|---|---:|---:|---:|
| negation | 185 | 0.265 | 0.032 |

## wav2vec2_korean

- Pairs: 185 across 185 speakers
- Scorable cues: 185 dialect-marked arm, 185 plain arm
- Cue loss: 0.665 when the cue word is dialect-marked vs 0.389 when it is not
- Paired difference: +0.276, 95% CI [0.173, 0.373] — excludes zero
- Arm-swap permutation p: <5.000e-05
- Discordant pairs: 77 dialect-only vs 26 plain-only, McNemar p 8.365e-07
- Placebo, non-dialect unit error: 0.599 vs 0.568, difference +0.032 95% CI [-0.008, 0.072] — crosses zero

| Cue category | Pairs | Dialect-marked arm loss | Plain arm loss |
|---|---:|---:|---:|
| negation | 185 | 0.665 | 0.389 |
