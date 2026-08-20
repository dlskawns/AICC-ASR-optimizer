# Dialect Attribution Probe

- Manifest rows: 50
- Dialect units: 66
- Plain units: 471
- Status: `asr_outputs_evaluated`

This probe tests whether ASR errors concentrate on dialect-marked eojeols before making AICC claims.

Full conclusion report with plots: [pilot_conclusion_report.md](pilot_conclusion_report.md)

Text-only semantic audit: [text_audit_report.md](text_audit_report.md)

## Faster-Whisper Medium Result

ASR hypotheses were generated with `../japko/whisper_proto` `faster-whisper 1.2.1`, model alias `medium`, `compute_type=int8`.

| Metric | Value |
|---|---:|
| Evaluated utterances | 50 |
| Missing ASR outputs | 0 |
| Dialect unit error rate | 0.455 |
| Dialect surface preservation rate | 0.227 |
| Dialect standard normalization rate | 0.318 |
| Plain unit error rate | 0.172 |
| Dialect/plain error-rate ratio | 2.643 |
| Dialect/plain odds ratio | 4.012 |
| Approx. two-proportion p-value | 1.10e-07 |
| ASR wall-clock sum, seconds | 152.181 |
| ASR average per clip, seconds | 3.044 |

Pilot interpretation: dialect-marked eojeols are substantially more fragile than non-dialect eojeols under this baseline. This is a problem-definition signal, not a final scientific result, because the sample is 50 utterances and is not yet speaker-independent gold.

The row-level local error file is `dialect_asr_error_cases.local.jsonl`. The shareable no-transcript manifest is `dialect_asr_error_manifest.jsonl`.

Reproduction:

```bash
../japko/whisper_proto/.venv/bin/python scripts/run_faster_whisper_pilot_asr.py \
  research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_medium.local.jsonl \
  medium
```

```bash
uv run scripts/run_dialect_attribution_probe.py \
  research/experiments/runs/aihub_119_pilot_review_packet/pilot_review_manifest.jsonl \
  --output-dir research/experiments/runs/aihub_119_dialect_attribution_probe \
  --asr research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_medium.local.jsonl
```
