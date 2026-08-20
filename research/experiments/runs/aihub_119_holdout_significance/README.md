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
- Dialect unit error rate: 0.648, cluster bootstrap 95% CI [0.593, 0.701]
- Non-dialect unit error rate: 0.204, cluster bootstrap 95% CI [0.185, 0.222]
- Difference: 0.444, cluster bootstrap 95% CI [0.386, 0.501]
- Ratio: 3.18x, cluster bootstrap 95% CI [2.809, 3.597]
- Mantel-Haenszel odds ratio stratified by utterance: 6.73 95% CI [5.209, 8.704]
- Within-utterance permutation p: <5.00e-05 (20000 draws, 280 informative utterances, 0 draws at or beyond the observed gap)
- Utterance composition alone explains a gap of 0.018, which is 4% of the raw gap; the dialect-attributable excess is 0.426
- Naive unit-independent p: 3.17e-71 (design effect vs cluster bootstrap: 1.38)

- Busan dialect unit error rate: 0.648 (150 utterances)
- Non-Busan Gyeongsang dialect unit error rate: 0.648 (150 utterances)
- Cohort difference: 0.000, cluster bootstrap 95% CI [-0.110, 0.106]

## faster-whisper:large-v3

- Utterances (clusters): 300
- Dialect units: 352, non-dialect units: 2525
- Dialect unit error rate: 0.648, cluster bootstrap 95% CI [0.594, 0.701]
- Non-dialect unit error rate: 0.190, cluster bootstrap 95% CI [0.172, 0.209]
- Difference: 0.458, cluster bootstrap 95% CI [0.401, 0.514]
- Ratio: 3.41x, cluster bootstrap 95% CI [2.995, 3.875]
- Mantel-Haenszel odds ratio stratified by utterance: 7.65 95% CI [5.887, 9.943]
- Within-utterance permutation p: <5.00e-05 (20000 draws, 273 informative utterances, 0 draws at or beyond the observed gap)
- Utterance composition alone explains a gap of 0.013, which is 3% of the raw gap; the dialect-attributable excess is 0.445
- Naive unit-independent p: 8.05e-78 (design effect vs cluster bootstrap: 1.41)

- Busan dialect unit error rate: 0.659 (150 utterances)
- Non-Busan Gyeongsang dialect unit error rate: 0.636 (150 utterances)
- Cohort difference: 0.023, cluster bootstrap 95% CI [-0.085, 0.131]

## wav2vec2:wav2vec2-large-xlsr-korean

- Utterances (clusters): 300
- Dialect units: 352, non-dialect units: 2525
- Dialect unit error rate: 0.920, cluster bootstrap 95% CI [0.891, 0.947]
- Non-dialect unit error rate: 0.614, cluster bootstrap 95% CI [0.590, 0.638]
- Difference: 0.307, cluster bootstrap 95% CI [0.271, 0.341]
- Ratio: 1.50x, cluster bootstrap 95% CI [1.429, 1.570]
- Mantel-Haenszel odds ratio stratified by utterance: 7.29 95% CI [4.837, 10.991]
- Within-utterance permutation p: <5.00e-05 (20000 draws, 300 informative utterances, 0 draws at or beyond the observed gap)
- Utterance composition alone explains a gap of 0.023, which is 8% of the raw gap; the dialect-attributable excess is 0.283
- Naive unit-independent p: 1.19e-29 (design effect vs cluster bootstrap: 0.44)

- Busan dialect unit error rate: 0.903 (150 utterances)
- Non-Busan Gyeongsang dialect unit error rate: 0.938 (150 utterances)
- Cohort difference: -0.034, cluster bootstrap 95% CI [-0.092, 0.021]
