# Dialect Attribution Significance Tests

The first probe compared dialect-marked and non-dialect eojeol error rates with a two-proportion
z-test over units. Units are nested in utterances, so that test overstates the evidence. This run
re-tests the same contrast three ways that respect the utterance clustering:

1. Utterance-level cluster bootstrap: resamples whole utterances, so units from one utterance stay together.
2. Within-utterance conditional permutation: reshuffles the dialect flag inside each utterance while
   holding that utterance's unit count and error count fixed, so utterance difficulty cannot drive the gap.
3. Mantel-Haenszel odds ratio stratified by utterance.

The unit outcome rule is unchanged and favours dialect units: a dialect unit counts as correct when the
hypothesis carries either the dialect surface or its standard form, while a non-dialect unit counts as
correct only on the standard surface.

Outputs carry counts and statistics only, with no transcript text.

## faster-whisper:medium

- Utterances (clusters): 300
- Dialect units: 352, non-dialect units: 2525
- Dialect unit error rate: 0.631, cluster bootstrap 95% CI [0.576, 0.685]
- Non-dialect unit error rate: 0.156, cluster bootstrap 95% CI [0.139, 0.173]
- Difference: 0.475, cluster bootstrap 95% CI [0.418, 0.532]
- Ratio: 4.05x, cluster bootstrap 95% CI [3.539, 4.655]
- Mantel-Haenszel odds ratio stratified by utterance: 9.30 95% CI [7.057, 12.248]
- Within-utterance permutation p: <5.00e-05 (20000 draws, 264 informative utterances, 0 draws at or beyond the observed gap)
- Utterance composition alone explains a gap of 0.019, which is 4% of the raw gap; the dialect-attributable excess is 0.456
- Naive unit-independent p: 3.31e-92 (design effect vs cluster bootstrap: 1.53)

- Busan dialect unit error rate: 0.619 (150 utterances)
- Non-Busan Gyeongsang dialect unit error rate: 0.642 (150 utterances)
- Cohort difference: -0.023, cluster bootstrap 95% CI [-0.132, 0.087]

## faster-whisper:large-v3

- Utterances (clusters): 300
- Dialect units: 352, non-dialect units: 2525
- Dialect unit error rate: 0.622, cluster bootstrap 95% CI [0.569, 0.677]
- Non-dialect unit error rate: 0.155, cluster bootstrap 95% CI [0.138, 0.172]
- Difference: 0.467, cluster bootstrap 95% CI [0.411, 0.525]
- Ratio: 4.02x, cluster bootstrap 95% CI [3.482, 4.638]
- Mantel-Haenszel odds ratio stratified by utterance: 8.74 95% CI [6.668, 11.460]
- Within-utterance permutation p: <5.00e-05 (20000 draws, 260 informative utterances, 0 draws at or beyond the observed gap)
- Utterance composition alone explains a gap of 0.016, which is 3% of the raw gap; the dialect-attributable excess is 0.452
- Naive unit-independent p: 8.19e-90 (design effect vs cluster bootstrap: 1.57)

- Busan dialect unit error rate: 0.614 (150 utterances)
- Non-Busan Gyeongsang dialect unit error rate: 0.631 (150 utterances)
- Cohort difference: -0.017, cluster bootstrap 95% CI [-0.125, 0.091]

## wav2vec2:wav2vec2-large-xlsr-korean

- Utterances (clusters): 300
- Dialect units: 352, non-dialect units: 2525
- Dialect unit error rate: 0.886, cluster bootstrap 95% CI [0.852, 0.918]
- Non-dialect unit error rate: 0.556, cluster bootstrap 95% CI [0.532, 0.581]
- Difference: 0.330, cluster bootstrap 95% CI [0.291, 0.367]
- Ratio: 1.59x, cluster bootstrap 95% CI [1.510, 1.680]
- Mantel-Haenszel odds ratio stratified by utterance: 6.23 95% CI [4.359, 8.907]
- Within-utterance permutation p: <5.00e-05 (20000 draws, 300 informative utterances, 0 draws at or beyond the observed gap)
- Utterance composition alone explains a gap of 0.027, which is 8% of the raw gap; the dialect-attributable excess is 0.303
- Naive unit-independent p: 3.02e-32 (design effect vs cluster bootstrap: 0.49)

- Busan dialect unit error rate: 0.892 (150 utterances)
- Non-Busan Gyeongsang dialect unit error rate: 0.881 (150 utterances)
- Cohort difference: 0.011, cluster bootstrap 95% CI [-0.055, 0.077]
