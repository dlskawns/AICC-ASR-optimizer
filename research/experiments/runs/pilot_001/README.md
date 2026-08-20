# Pilot 001: Semantic-Critical Pipeline Smoke Experiment

Run date: 2026-08-11 KST

## Purpose

Validate the local experiment harness before restricted AI-Hub/ClovaCall data is approved.

This is not a scientific result. The fixture is synthetic and intentionally constructed to test whether the pipeline detects semantic-critical ASR failures.

## Inputs

- Gold annotations: `data/fixtures/pilot/gold_annotations.jsonl`
- ASR outputs: `data/fixtures/pilot/asr_outputs.jsonl`
- AI-Hub-like metadata fixture: `data/fixtures/aihub_sample/gyeongsang_sample_001.json`

## Commands

```bash
uv run scripts/inspect_aihub_metadata.py \
  data/fixtures/aihub_sample \
  --output research/experiments/runs/pilot_001/metadata_summary.json

uv run scripts/evaluate_semantic_critical.py \
  data/fixtures/pilot/gold_annotations.jsonl \
  data/fixtures/pilot/asr_outputs.jsonl \
  --output-dir research/experiments/runs/pilot_001
```

## Metadata Smoke Result

- Files inspected: 1
- Speakers with region metadata: 2
- Utterances with dialect/standard transcript fields: 2
- Regions observed: 부산, 대구
- Dialect eojeols: 2 of 10

## Semantic Metric Smoke Result

| model | examples | cer | wer | intent_accuracy | slot_f1 | semantic_critical_error_rate |
| --- | --- | --- | --- | --- | --- | --- |
| dialect_aware_asr | 5 | 0.000 | 0.000 | 1.000 | 1.000 | 0.000 |
| generic_asr | 5 | 0.083 | 0.207 | 0.800 | 0.500 | 0.667 |

## Interpretation

The smoke test proves the intended measurement surface works:

- WER/CER are computed.
- Intent accuracy and Slot F1 are computed.
- Critical-span preservation detects negation, amount/date, and entity failures.
- A model can have a moderate WER but much larger semantic-critical failure rate.

The next real experiment must replace the synthetic fixture with approved AI-Hub/ClovaCall data and a speaker-independent split.
