# Dialect Control Pair Comparison

Does dialect marking in an utterance raise AICC critical-span loss? Earlier rounds asked this by
checking whether a critical span's surface sat on a dialect eojeol, which never had more than five
usable observations. This asks it at utterance level, paired within speaker.

Each pair is one speaker in one recording: a dialect-bearing utterance and a length-matched
dialect-free utterance, both carrying critical spans. The paired difference removes speaker ability
and recording quality.

Read the placebo line first. Non-dialect unit error should be similar in both arms; if it is not,
the pairs differ in something beyond dialect marking and the critical-span number means little.

Labels are weak preannotations that no human has reviewed.

## faster_whisper_medium

- Pairs: 63 across 63 speakers
- Scorable critical spans: 93 dialect arm, 88 control arm
- Critical-span loss: 0.108 dialect vs 0.080 control
- Paired difference: +0.028, 95% CI [-0.056, 0.114] — crosses zero
- Arm-swap permutation p: 5.541e-01
- Discordant pairs: 7 dialect-only vs 5 control-only, McNemar p 0.773
- Placebo, non-dialect unit error: 0.224 vs 0.218, difference +0.007 95% CI [-0.049, 0.062] — crosses zero

## faster_whisper_large_v3

- Pairs: 63 across 63 speakers
- Scorable critical spans: 93 dialect arm, 88 control arm
- Critical-span loss: 0.118 dialect vs 0.136 control
- Paired difference: -0.018, 95% CI [-0.102, 0.066] — crosses zero
- Arm-swap permutation p: 7.042e-01
- Discordant pairs: 5 dialect-only vs 7 control-only, McNemar p 0.773
- Placebo, non-dialect unit error: 0.190 vs 0.210, difference -0.020 95% CI [-0.075, 0.035] — crosses zero

## wav2vec2_korean

- Pairs: 63 across 63 speakers
- Scorable critical spans: 93 dialect arm, 88 control arm
- Critical-span loss: 0.398 dialect vs 0.375 control
- Paired difference: +0.023, 95% CI [-0.151, 0.198] — crosses zero
- Arm-swap permutation p: 8.107e-01
- Discordant pairs: 15 dialect-only vs 13 control-only, McNemar p 0.850
- Placebo, non-dialect unit error: 0.620 vs 0.614, difference +0.006 95% CI [-0.051, 0.062] — crosses zero
