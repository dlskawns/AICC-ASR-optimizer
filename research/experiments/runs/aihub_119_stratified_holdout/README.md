# Stratified Unit Scoring

The holdout is skewed: 228 women to 72 men, and 205 of its 300 speakers are in their twenties.
That skew cannot confound the headline contrast, because the contrast lives inside each utterance.
Every utterance supplies both its dialect-marked and its non-dialect units, so speaker, sex, age,
and recording are identical on both sides by construction.

What the skew threatens is generality. This splits the same alignment-scored data by sex, age band,
and cohort, and reports the dialect-minus-plain gap inside each stratum.

Strata with fewer than 20 utterances are descriptive only and carry no interval.

## faster_whisper_medium

### By sex

| Stratum | Utterances | Dialect | Plain | Difference | Ratio | 95% CI | |
|---|---:|---:|---:|---:|---:|---|---|
| 여성 | 228 | 0.667 | 0.231 | +0.436 | 2.89x | [0.374, 0.499] | excludes zero |
| 남성 | 72 | 0.634 | 0.247 | +0.388 | 2.57x | [0.265, 0.508] | excludes zero |

### By age band

| Stratum | Utterances | Dialect | Plain | Difference | Ratio | 95% CI | |
|---|---:|---:|---:|---:|---:|---|---|
| 20대 | 205 | 0.685 | 0.223 | +0.461 | 3.06x | [0.392, 0.529] | excludes zero |
| 30대 | 58 | 0.548 | 0.253 | +0.295 | 2.17x | [0.159, 0.430] | excludes zero |
| 50대 | 19 | 0.600 | 0.281 | +0.319 | 2.13x | descriptive only | n=19 |
| 10대 | 15 | 0.810 | 0.248 | +0.562 | 3.27x | descriptive only | n=15 |
| 60대 이상 | 3 | 0.500 | 0.280 | +0.220 | 1.79x | descriptive only | n=3 |

### By cohort

| Stratum | Utterances | Dialect | Plain | Difference | Ratio | 95% CI | |
|---|---:|---:|---:|---:|---:|---|---|
| busan | 150 | 0.670 | 0.257 | +0.413 | 2.61x | [0.333, 0.492] | excludes zero |
| gyeongsang_other | 150 | 0.648 | 0.212 | +0.436 | 3.06x | [0.356, 0.516] | excludes zero |

Overall: dialect 0.659, plain 0.234, difference +0.425, ratio 2.81x.

## faster_whisper_large_v3

### By sex

| Stratum | Utterances | Dialect | Plain | Difference | Ratio | 95% CI | |
|---|---:|---:|---:|---:|---:|---|---|
| 여성 | 228 | 0.667 | 0.212 | +0.454 | 3.14x | [0.392, 0.515] | excludes zero |
| 남성 | 72 | 0.622 | 0.226 | +0.396 | 2.76x | [0.278, 0.510] | excludes zero |

### By age band

| Stratum | Utterances | Dialect | Plain | Difference | Ratio | 95% CI | |
|---|---:|---:|---:|---:|---:|---|---|
| 20대 | 205 | 0.680 | 0.208 | +0.472 | 3.27x | [0.405, 0.538] | excludes zero |
| 30대 | 58 | 0.565 | 0.236 | +0.328 | 2.39x | [0.193, 0.462] | excludes zero |
| 50대 | 19 | 0.550 | 0.237 | +0.313 | 2.32x | descriptive only | n=19 |
| 10대 | 15 | 0.810 | 0.197 | +0.613 | 4.12x | descriptive only | n=15 |
| 60대 이상 | 3 | 0.500 | 0.260 | +0.240 | 1.92x | descriptive only | n=3 |

### By cohort

| Stratum | Utterances | Dialect | Plain | Difference | Ratio | 95% CI | |
|---|---:|---:|---:|---:|---:|---|---|
| busan | 150 | 0.676 | 0.230 | +0.446 | 2.94x | [0.368, 0.523] | excludes zero |
| gyeongsang_other | 150 | 0.636 | 0.201 | +0.435 | 3.17x | [0.358, 0.513] | excludes zero |

Overall: dialect 0.656, plain 0.215, difference +0.441, ratio 3.05x.

## wav2vec2_korean

### By sex

| Stratum | Utterances | Dialect | Plain | Difference | Ratio | 95% CI | |
|---|---:|---:|---:|---:|---:|---|---|
| 여성 | 228 | 0.904 | 0.625 | +0.278 | 1.44x | [0.234, 0.320] | excludes zero |
| 남성 | 72 | 0.890 | 0.616 | +0.274 | 1.44x | [0.195, 0.348] | excludes zero |

### By age band

| Stratum | Utterances | Dialect | Plain | Difference | Ratio | 95% CI | |
|---|---:|---:|---:|---:|---:|---|---|
| 20대 | 205 | 0.900 | 0.601 | +0.299 | 1.50x | [0.252, 0.344] | excludes zero |
| 30대 | 58 | 0.887 | 0.674 | +0.213 | 1.32x | [0.118, 0.306] | excludes zero |
| 50대 | 19 | 0.900 | 0.704 | +0.196 | 1.28x | descriptive only | n=19 |
| 10대 | 15 | 0.905 | 0.607 | +0.298 | 1.49x | descriptive only | n=15 |
| 60대 이상 | 3 | 1.000 | 0.740 | +0.260 | 1.35x | descriptive only | n=3 |

### By cohort

| Stratum | Utterances | Dialect | Plain | Difference | Ratio | 95% CI | |
|---|---:|---:|---:|---:|---:|---|---|
| busan | 150 | 0.886 | 0.614 | +0.273 | 1.44x | [0.218, 0.325] | excludes zero |
| gyeongsang_other | 150 | 0.915 | 0.633 | +0.282 | 1.45x | [0.229, 0.332] | excludes zero |

Overall: dialect 0.901, plain 0.623, difference +0.277, ratio 1.44x.
