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

- Utterances: 50, dialect units 66, non-dialect units 471
- Dialect unit error rate: 0.470
- Non-dialect unit error rate: 0.274
- Difference: 0.196, cluster bootstrap 95% CI [0.063, 0.327]
- Ratio: 1.71x
- Utterance-stratified odds ratio: 2.25 [1.29, 3.92]
- Within-utterance permutation p: 2.15e-03
- Busan minus other Gyeongsang: +0.123

## faster-whisper:large-v3

- Utterances: 50, dialect units 66, non-dialect units 471
- Dialect unit error rate: 0.439
- Non-dialect unit error rate: 0.231
- Difference: 0.208, cluster bootstrap 95% CI [0.081, 0.338]
- Ratio: 1.90x
- Utterance-stratified odds ratio: 2.42 [1.38, 4.25]
- Within-utterance permutation p: 1.15e-03
- Busan minus other Gyeongsang: +0.125

## wav2vec2:wav2vec2-large-xlsr-korean

- Utterances: 50, dialect units 66, non-dialect units 471
- Dialect unit error rate: 0.864
- Non-dialect unit error rate: 0.656
- Difference: 0.208, cluster bootstrap 95% CI [0.107, 0.301]
- Ratio: 1.32x
- Utterance-stratified odds ratio: 2.98 [1.43, 6.21]
- Within-utterance permutation p: 1.30e-03
- Busan minus other Gyeongsang: +0.039
