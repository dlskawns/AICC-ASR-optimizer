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
| cue word is dialect-marked | 75 | 17 | 4 | 54 | 0.810 |
| cue word is plain | 24 | 6 | 3 | 15 | 0.667 |

- Distinct replacement surfaces in the dialect arm: 14

| Cue category, dialect arm | Absent | Substitution share of resolved |
|---|---:|---:|
| confirmation | 75 | 0.810 |

## faster_whisper_large_v3

| Arm | Absent cues | Substitution | Deletion | Context lost | Substitution share of resolved |
|---|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 65 | 11 | 9 | 45 | 0.550 |
| cue word is plain | 23 | 5 | 0 | 18 | 1.000 |

- Distinct replacement surfaces in the dialect arm: 10

| Cue category, dialect arm | Absent | Substitution share of resolved |
|---|---:|---:|
| confirmation | 64 | 0.550 |
| negation | 1 | n/a |

## wav2vec2_korean

| Arm | Absent cues | Substitution | Deletion | Context lost | Substitution share of resolved |
|---|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 198 | 22 | 7 | 169 | 0.759 |
| cue word is plain | 132 | 17 | 3 | 112 | 0.850 |

- Distinct replacement surfaces in the dialect arm: 22

| Cue category, dialect arm | Absent | Substitution share of resolved |
|---|---:|---:|
| confirmation | 181 | 0.750 |
| negation | 17 | 1.000 |
