# Control Pairs Scored By Alignment

Round 5 asked whether an utterance carrying dialect marking loses more AICC critical spans than the
same speaker's dialect-free utterance, and found nothing. It judged a span by searching the whole
hypothesis. Every other metric in this project has since moved to alignment, and every correction so
far moved a number, so the null needed rescoring on the same standard.

Each span is located at its evidence eojeol and judged only against the token aligned to that
position. The placebo is non-dialect unit error, which should not differ between arms.

Labels are weak preannotations that no human has reviewed.

## faster_whisper_medium

- Pairs: 63 across 63 speakers
- Spans: 93 dialect arm, 85 control arm
- Critical-span loss: 0.194 dialect vs 0.165 control
- Paired difference: +0.029, 95% CI [-0.092, 0.147] — crosses zero
- Arm-swap permutation p: 6.518e-01
- Discordant pairs: 12 dialect-only vs 9 control-only, McNemar p 0.663
- Placebo, non-dialect unit error: +0.000 95% CI [-0.062, 0.062] — crosses zero

## faster_whisper_large_v3

- Pairs: 63 across 63 speakers
- Spans: 93 dialect arm, 85 control arm
- Critical-span loss: 0.161 dialect vs 0.176 control
- Paired difference: -0.015, 95% CI [-0.113, 0.080] — crosses zero
- Arm-swap permutation p: 7.573e-01
- Discordant pairs: 6 dialect-only vs 8 control-only, McNemar p 0.789
- Placebo, non-dialect unit error: -0.026 95% CI [-0.086, 0.031] — crosses zero

## wav2vec2_korean

- Pairs: 63 across 63 speakers
- Spans: 93 dialect arm, 85 control arm
- Critical-span loss: 0.495 dialect vs 0.471 control
- Paired difference: +0.024, 95% CI [-0.147, 0.193] — crosses zero
- Arm-swap permutation p: 7.660e-01
- Discordant pairs: 15 dialect-only vs 10 control-only, McNemar p 0.424
- Placebo, non-dialect unit error: +0.022 95% CI [-0.034, 0.076] — crosses zero
