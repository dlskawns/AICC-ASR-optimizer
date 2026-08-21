# Cue-Bearing Dialect Split

Round 5 showed that dialect marking somewhere in an utterance does not raise AICC critical-span
loss, which points to dialect fragility being local to the dialect tokens themselves. That reading
predicts something testable: when the AICC cue word *is* the dialect-marked eojeol, loss should rise.

Such cases are rare in a random sample, so this split mines the whole label set for them and pairs
each with an utterance from the same speaker where the same cue category is carried by a non-dialect
eojeol. Speaker, recording, and cue category are fixed inside a pair; only the dialect marking of the
cue word differs.

**Label status: `weak_preannotation_not_gold`.**

## Composition

- Cue-bearing dialect hits found: 829
- Non-dialect cue hits available for matching: 56018
- Pairs built: 290
- Distinct speakers: 185, recordings: 156
- Cohorts: {"busan": 160, "gyeongsang_other": 130}
- Cue categories: {"negation": 290}
- Clips: 580, 50.32 minutes

Matching rule: same speaker, same cue category, cue eojeol dialect-marked versus not.

## Limits

- The cue inventory that survives boundary-safe mining is dominated by confirmation and negation
  markers. Amount and intent cues almost never appear on a dialect-marked eojeol in this corpus, so
  this split cannot speak for those categories.
- Whether a speaker renders a cue in dialect form is not randomly assigned.
- Labels are weak and unreviewed.

Manifests carry transcript text and are local-only.
