# Dialect Control Pairs

Surface overlap between critical spans and dialect eojeols was a dead end: going from 50 to 300
utterances moved the overlapping-span count only from 4 to 5, because the two rarely co-occur on
the surface. This run replaces that design with an utterance-level, within-speaker comparison.

For each holdout utterance carrying both a dialect eojeol and a critical span, a second utterance
is drawn from the same speaker in the same recording that carries critical spans but no dialect
eojeol, matched on length. Speaker, microphone, session, and topic are held fixed by construction.

**Label status: `weak_preannotation_not_gold`.**

## Composition

- Case utterances offered: 63
- Pairs built: 63, unpaired: 0
- Distinct speakers: 63 across 56 recordings
- Cohorts: {"busan": 33, "gyeongsang_other": 30}
- Critical spans on the control side: 88
- Mean length, case vs control: 10.7 vs 10.6 eojeols (mean difference -0.14)
- Control clip duration: 5.67 minutes

Matching rule: same recording, same speaker, zero dialect eojeols, length-closest, at least one minable critical span.

## Limits

- Dialect marking is not randomly assigned. A speaker may reach for dialect forms in harder or more
  informal stretches of talk, so the pairing controls who is speaking, not what they chose to say.
- Length is matched on eojeol count, not on acoustic duration or speaking rate.
- Control spans are mined by the same weak boundary rules and no human has reviewed them.

Manifests carry transcript text and are local-only.
