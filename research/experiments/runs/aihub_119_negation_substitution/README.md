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
| cue word is dialect-marked | 52 | 16 | 2 | 34 | 0.889 |
| cue word is plain | 16 | 8 | 2 | 6 | 0.800 |

- Distinct replacement surfaces in the dialect arm: 15

| Cue category, dialect arm | Absent | Substitution share of resolved |
|---|---:|---:|
| negation | 52 | 0.889 |

## faster_whisper_large_v3

| Arm | Absent cues | Substitution | Deletion | Context lost | Substitution share of resolved |
|---|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 51 | 13 | 5 | 33 | 0.722 |
| cue word is plain | 18 | 9 | 4 | 5 | 0.692 |

- Distinct replacement surfaces in the dialect arm: 13

| Cue category, dialect arm | Absent | Substitution share of resolved |
|---|---:|---:|
| negation | 51 | 0.722 |

## wav2vec2_korean

| Arm | Absent cues | Substitution | Deletion | Context lost | Substitution share of resolved |
|---|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 137 | 18 | 5 | 114 | 0.783 |
| cue word is plain | 94 | 22 | 2 | 70 | 0.917 |

- Distinct replacement surfaces in the dialect arm: 18

| Cue category, dialect arm | Absent | Substitution share of resolved |
|---|---:|---:|
| negation | 137 | 0.783 |
