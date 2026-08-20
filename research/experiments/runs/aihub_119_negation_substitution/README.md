# Cue Substitution Versus Deletion

Round 7 counted a cue as damaged when neither its dialect surface nor its standard form reached the
hypothesis. A contact centre cares which kind of absence it was.

- Deletion leaves the cue position empty. Downstream, the signal is missing and can be noticed as missing.
- Substitution puts another word in the cue position, which reads as a confident wrong answer.

The verdict comes from the cue's neighbouring eojeols. When both survive in the hypothesis, whatever
sits between them is what the cue became. When the neighbours are gone too, or the gap is wider than
three tokens, the alignment is not trustworthy and the case is reported as `context_lost` rather than
forced into one of the two classes.

Read `context_lost` as a property of the model as much as of the method: a system whose output drifts
far from the reference gives no anchors to align against.

The inventory of what each lost cue became is transcript-derived and stays in the local case file.
Labels are weak preannotations that no human has reviewed.

## faster_whisper_medium

| Arm | Absent cues | Substitution | Deletion | Context lost | Substitution share of resolved |
|---|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 37 | 9 | 2 | 26 | 0.818 |
| cue word is plain | 8 | 2 | 2 | 4 | 0.500 |

- Distinct replacement surfaces in the dialect arm: 8

| Cue category, dialect arm | Absent | Substitution share of resolved |
|---|---:|---:|
| negation | 37 | 0.818 |

## faster_whisper_large_v3

| Arm | Absent cues | Substitution | Deletion | Context lost | Substitution share of resolved |
|---|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 37 | 5 | 5 | 27 | 0.500 |
| cue word is plain | 8 | 1 | 4 | 3 | 0.200 |

- Distinct replacement surfaces in the dialect arm: 5

| Cue category, dialect arm | Absent | Substitution share of resolved |
|---|---:|---:|
| negation | 37 | 0.500 |

## wav2vec2_korean

| Arm | Absent cues | Substitution | Deletion | Context lost | Substitution share of resolved |
|---|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 116 | 15 | 5 | 96 | 0.750 |
| cue word is plain | 75 | 16 | 2 | 57 | 0.889 |

- Distinct replacement surfaces in the dialect arm: 15

| Cue category, dialect arm | Absent | Substitution share of resolved |
|---|---:|---:|
| negation | 116 | 0.750 |
