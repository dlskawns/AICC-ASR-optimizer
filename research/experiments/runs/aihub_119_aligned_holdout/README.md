# Aligned Unit Scoring

Earlier versions of this metric asked whether a reference eojeol appeared anywhere in the hypothesis.
Raw containment credited a single syllable that turned up inside an unrelated word; the eojeol-boundary
rule that replaced it still let a one-syllable unit match any eojeol beginning with it. Half the dialect
units in this data are one syllable, so that loophole stayed open.

Here the reference eojeol sequence is aligned to the hypothesis token sequence by edit distance, with a
substitution cost drawn from character similarity, and each unit is judged only against whatever aligned
to its position. Evidence cannot be borrowed from elsewhere in the sentence.

Dialect units keep their standing concession: the dialect surface or its standard form both count as
correct. That makes the dialect arm easier to score well, so it cannot manufacture a dialect penalty.

## faster-whisper:medium

- Utterances: 300, dialect units 352, non-dialect units 2525
- Dialect unit error rate: 0.659
- Non-dialect unit error rate: 0.234
- Difference: 0.425, cluster bootstrap 95% CI [0.367, 0.480]
- Ratio: 2.81x
- Utterance-stratified odds ratio: 6.08 [4.70, 7.88]
- Within-utterance permutation p: <5.00e-05
- Busan minus other Gyeongsang: +0.023

## faster-whisper:large-v3

- Utterances: 300, dialect units 352, non-dialect units 2525
- Dialect unit error rate: 0.656
- Non-dialect unit error rate: 0.215
- Difference: 0.441, cluster bootstrap 95% CI [0.386, 0.496]
- Ratio: 3.05x
- Utterance-stratified odds ratio: 7.15 [5.49, 9.30]
- Within-utterance permutation p: <5.00e-05
- Busan minus other Gyeongsang: +0.040

## wav2vec2:wav2vec2-large-xlsr-korean

- Utterances: 300, dialect units 352, non-dialect units 2525
- Dialect unit error rate: 0.901
- Non-dialect unit error rate: 0.623
- Difference: 0.277, cluster bootstrap 95% CI [0.238, 0.313]
- Ratio: 1.44x
- Utterance-stratified odds ratio: 5.41 [3.73, 7.83]
- Within-utterance permutation p: <5.00e-05
- Busan minus other Gyeongsang: -0.028
