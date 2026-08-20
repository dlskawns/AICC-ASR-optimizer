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
| cue word is dialect-marked | 87 | 24 | 4 | 59 | 0.857 |
| cue word is plain | 41 | 17 | 3 | 21 | 0.850 |

- Distinct replacement surfaces in the dialect arm: 21

| Cue category, dialect arm | Absent | Substitution share of resolved |
|---|---:|---:|
| confirmation | 85 | 0.846 |
| negation | 2 | 1.000 |

## faster_whisper_large_v3

| Arm | Absent cues | Substitution | Deletion | Context lost | Substitution share of resolved |
|---|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 72 | 15 | 9 | 48 | 0.625 |
| cue word is plain | 37 | 14 | 0 | 23 | 1.000 |

- Distinct replacement surfaces in the dialect arm: 14

| Cue category, dialect arm | Absent | Substitution share of resolved |
|---|---:|---:|
| confirmation | 69 | 0.591 |
| negation | 3 | 1.000 |

## wav2vec2_korean

| Arm | Absent cues | Substitution | Deletion | Context lost | Substitution share of resolved |
|---|---:|---:|---:|---:|---:|
| cue word is dialect-marked | 208 | 24 | 7 | 177 | 0.774 |
| cue word is plain | 163 | 26 | 3 | 134 | 0.897 |

- Distinct replacement surfaces in the dialect arm: 24

| Cue category, dialect arm | Absent | Substitution share of resolved |
|---|---:|---:|
| confirmation | 187 | 0.759 |
| negation | 21 | 1.000 |
