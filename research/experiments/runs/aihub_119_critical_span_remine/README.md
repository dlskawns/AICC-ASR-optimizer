# Critical Span Re-mining

The weak AICC critical-span labels were mined by raw substring containment. Two failure classes
followed from ignoring the eojeol boundary:

- A business cue was harvested from ordinary inflected verbs that carry no business event.
- An amount pattern was matched across an eojeol break, turning a noun-plus-particle sequence into money.

This run re-mines the same utterances with boundary-aware rules. Every cue must open a real eojeol,
single-syllable markers must stand alone, and amounts are matched token-wise.

**Label status: `weak_preannotation_not_gold`.** More precise is not gold.

## Result

| Rule | Spans | Phantom labels | Phantom rate |
|---|---:|---:|---:|
| old, substring | 74 | 16 | 0.216 |
| new, eojeol boundary | 56 | 1 | 0.018 |

- Old category counts: {"negation": 17, "confirmation": 17, "intent_cue": 15, "date_time": 13, "amount": 12}
- New category counts: {"negation": 17, "date_time": 13, "amount": 11, "confirmation": 10, "intent_cue": 5}
- Old phantom labels by category: {"intent_cue": 10, "confirmation": 4, "amount": 2}
- New phantom labels by category: {"amount": 1}

## What This Does Not Fix

The boundary rule proves a label names a real eojeol. It cannot prove that eojeol carried a business
event. This corpus is spontaneous conversation, so a cue that opens a real eojeol may still describe
something unrelated to contact-centre work. Human review remains required before any of this is gold.

Recall also drops on purpose. Single-syllable negation markers fused to a following stem are no longer
collected, because keeping them costs more precision than the extra recall is worth.

The re-mined annotation file carries transcript text and is local-only.
