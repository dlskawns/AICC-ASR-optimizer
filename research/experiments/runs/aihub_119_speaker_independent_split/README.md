# Speaker-Independent Holdout Split

The 50-utterance pilot reuses 46 recordings and cannot say anything about speaker generalisation.
This split shares no recording with the pilot and caps how many utterances one speaker contributes.

**Gold status: `not_gold_no_human_review`.**

## Composition

- Candidate pool: 25911 utterances with at least one dialect-marked eojeol
- Selected: 300 utterances
- Distinct speakers: 300
- Cap per speaker: 2 utterances
- Excluded pilot recordings: 46
- Cohorts: {"busan": 150, "gyeongsang_other": 150}
- Age bands: {"20대": 205, "30대": 58, "50대": 19, "10대": 15, "60대 이상": 3}
- Sex: {"여성": 228, "남성": 72}
- Dialect units: 352, non-dialect units: 2525
- Total clip duration: 26.47 minutes
- Clip dir: `data/interim/aihub_119_holdout_clips`

## How To Use It

`asr_input_manifest.local.jsonl` uses the same schema as the pilot probe, so the ASR runners, the
clustered significance tests, and the critical-span audit all take it without modification.

Selection is deterministic: candidates are ordered by a content hash and taken round-robin across
speakers, so re-running reproduces the same split without a random seed.

## Limits

- Speaker identity is only known within a recording, so speaker keys are recording-scoped. If the same
  person appears in two recordings under different local ids, this split cannot tell.
- The split is disjoint from the pilot by recording, which is the strongest disjointness the metadata
  supports. It is not a certified speaker-independent test set.
- No human has reviewed any label here.

The manifest carries transcript text and is local-only.
