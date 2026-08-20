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
- Dialect unit error rate: 0.500, cluster bootstrap 95% CI [0.377, 0.615]
- Non-dialect unit error rate: 0.240, cluster bootstrap 95% CI [0.189, 0.294]
- Difference: 0.260, cluster bootstrap 95% CI [0.132, 0.385]
- Ratio: 2.08x, cluster bootstrap 95% CI [1.511, 2.828]
- Mantel-Haenszel odds ratio stratified by utterance: 3.08 95% CI [1.733, 5.482]
- Within-utterance permutation p: <5.00e-05 (20000 draws, 47 informative utterances, 0 draws at or beyond the observed gap)
- Utterance composition alone explains a gap of 0.034, which is 13% of the raw gap; the dialect-attributable excess is 0.226
- Naive unit-independent p: 8.69e-06 (design effect vs cluster bootstrap: 1.20)

- Busan dialect unit error rate: 0.559 (25 utterances)
- Non-Busan Gyeongsang dialect unit error rate: 0.438 (25 utterances)
- Cohort difference: 0.121, cluster bootstrap 95% CI [-0.113, 0.352]

## faster-whisper:large-v3

- Utterances (clusters): 50
- Dialect units: 66, non-dialect units: 471
- Dialect unit error rate: 0.455, cluster bootstrap 95% CI [0.342, 0.567]
- Non-dialect unit error rate: 0.206, cluster bootstrap 95% CI [0.159, 0.258]
- Difference: 0.249, cluster bootstrap 95% CI [0.122, 0.376]
- Ratio: 2.21x, cluster bootstrap 95% CI [1.525, 3.156]
- Mantel-Haenszel odds ratio stratified by utterance: 2.89 95% CI [1.641, 5.103]
- Within-utterance permutation p: 1.50e-04 (20000 draws, 46 informative utterances, 2 draws at or beyond the observed gap)
- Utterance composition alone explains a gap of 0.033, which is 13% of the raw gap; the dialect-attributable excess is 0.216
- Naive unit-independent p: 8.54e-06 (design effect vs cluster bootstrap: 1.36)

- Busan dialect unit error rate: 0.500 (25 utterances)
- Non-Busan Gyeongsang dialect unit error rate: 0.406 (25 utterances)
- Cohort difference: 0.094, cluster bootstrap 95% CI [-0.132, 0.317]

## wav2vec2:wav2vec2-large-xlsr-korean

- Utterances (clusters): 50
- Dialect units: 66, non-dialect units: 471
- Dialect unit error rate: 0.864, cluster bootstrap 95% CI [0.770, 0.943]
- Non-dialect unit error rate: 0.667, cluster bootstrap 95% CI [0.612, 0.721]
- Difference: 0.197, cluster bootstrap 95% CI [0.087, 0.297]
- Ratio: 1.30x, cluster bootstrap 95% CI [1.125, 1.472]
- Mantel-Haenszel odds ratio stratified by utterance: 2.82 95% CI [1.347, 5.906]
- Within-utterance permutation p: 1.55e-03 (20000 draws, 50 informative utterances, 30 draws at or beyond the observed gap)
- Utterance composition alone explains a gap of 0.032, which is 16% of the raw gap; the dialect-attributable excess is 0.165
- Naive unit-independent p: 1.18e-03 (design effect vs cluster bootstrap: 0.78)

- Busan dialect unit error rate: 0.912 (25 utterances)
- Non-Busan Gyeongsang dialect unit error rate: 0.812 (25 utterances)
- Cohort difference: 0.099, cluster bootstrap 95% CI [-0.078, 0.269]
