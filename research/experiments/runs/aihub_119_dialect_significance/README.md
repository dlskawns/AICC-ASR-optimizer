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

- Utterances (clusters): 50
- Dialect units: 66, non-dialect units: 471
- Dialect unit error rate: 0.455, cluster bootstrap 95% CI [0.338, 0.567]
- Non-dialect unit error rate: 0.172, cluster bootstrap 95% CI [0.130, 0.218]
- Difference: 0.283, cluster bootstrap 95% CI [0.169, 0.394]
- Ratio: 2.64x, cluster bootstrap 95% CI [1.912, 3.616]
- Mantel-Haenszel odds ratio stratified by utterance: 4.10 95% CI [2.188, 7.697]
- Within-utterance permutation p: <5.00e-05 (20000 draws, 44 informative utterances, 0 draws at or beyond the observed gap)
- Utterance composition alone explains a gap of 0.040, which is 14% of the raw gap; the dialect-attributable excess is 0.243
- Naive unit-independent p: 1.10e-07 (design effect vs cluster bootstrap: 1.16)

- Busan dialect unit error rate: 0.471 (25 utterances)
- Non-Busan Gyeongsang dialect unit error rate: 0.438 (25 utterances)
- Cohort difference: 0.033, cluster bootstrap 95% CI [-0.197, 0.263]

## faster-whisper:large-v3

- Utterances (clusters): 50
- Dialect units: 66, non-dialect units: 471
- Dialect unit error rate: 0.409, cluster bootstrap 95% CI [0.297, 0.521]
- Non-dialect unit error rate: 0.161, cluster bootstrap 95% CI [0.122, 0.205]
- Difference: 0.248, cluster bootstrap 95% CI [0.130, 0.367]
- Ratio: 2.54x, cluster bootstrap 95% CI [1.716, 3.646]
- Mantel-Haenszel odds ratio stratified by utterance: 3.31 95% CI [1.817, 6.038]
- Within-utterance permutation p: <5.00e-05 (20000 draws, 44 informative utterances, 0 draws at or beyond the observed gap)
- Utterance composition alone explains a gap of 0.032, which is 13% of the raw gap; the dialect-attributable excess is 0.216
- Naive unit-independent p: 1.69e-06 (design effect vs cluster bootstrap: 1.38)

- Busan dialect unit error rate: 0.412 (25 utterances)
- Non-Busan Gyeongsang dialect unit error rate: 0.406 (25 utterances)
- Cohort difference: 0.006, cluster bootstrap 95% CI [-0.219, 0.223]

## wav2vec2:wav2vec2-large-xlsr-korean

- Utterances (clusters): 50
- Dialect units: 66, non-dialect units: 471
- Dialect unit error rate: 0.818, cluster bootstrap 95% CI [0.719, 0.909]
- Non-dialect unit error rate: 0.611, cluster bootstrap 95% CI [0.550, 0.673]
- Difference: 0.207, cluster bootstrap 95% CI [0.088, 0.320]
- Ratio: 1.34x, cluster bootstrap 95% CI [1.138, 1.562]
- Mantel-Haenszel odds ratio stratified by utterance: 2.53 95% CI [1.300, 4.924]
- Within-utterance permutation p: 1.65e-03 (20000 draws, 50 informative utterances, 32 draws at or beyond the observed gap)
- Utterance composition alone explains a gap of 0.039, which is 19% of the raw gap; the dialect-attributable excess is 0.168
- Naive unit-independent p: 1.07e-03 (design effect vs cluster bootstrap: 0.87)

- Busan dialect unit error rate: 0.824 (25 utterances)
- Non-Busan Gyeongsang dialect unit error rate: 0.812 (25 utterances)
- Cohort difference: 0.011, cluster bootstrap 95% CI [-0.187, 0.200]
