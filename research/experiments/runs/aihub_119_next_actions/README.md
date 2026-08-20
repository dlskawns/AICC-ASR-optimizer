# AI-Hub 119 Next Actions

## Executed Now

The label-side work and validation-audio download are complete.

- Built [gold review queue](../aihub_119_gold_review/README.md).
- Ran [gold freeze dry-run](../aihub_119_gold_freeze/README.md).
- Built [audio subset request manifest](../aihub_119_audio_subset_request/README.md).
- Downloaded and validated [validation source audio](../aihub_119_validation_audio_download/README.md).
- Extracted [50-row pilot audio subset](../aihub_119_pilot_audio_subset/README.md) from the validated archive.
- Built [utterance-level pilot review packet](../aihub_119_pilot_review_packet/README.md).
- Ran [pilot gold freeze dry-run](../aihub_119_pilot_gold_freeze/README.md).
- Built [dialect attribution probe](../aihub_119_dialect_attribution_probe/README.md).
- Checked `../japko/whisper_proto`, cached `faster-whisper` `medium`, and verified local-only model loading.
- Added `scripts/run_faster_whisper_pilot_asr.py` to generate local ASR JSONL.
- Generated 50 `faster-whisper:medium` ASR hypotheses.
- Evaluated dialect attribution and generated row-level ASR error analysis.
- Ran text-only semantic audit of 66 dialect-marked units.
- Verified CLI bad-input paths, JSON parsing, and local-only raw-text ignore rules.

## Current State

| Item | Count |
|---|---:|
| Gold review queue rows | 398 |
| Unreviewed rows | 398 |
| Frozen gold rows | 0 |
| Audio subset request rows | 398 |
| Validation audio WAV files | 843 |
| Pilot review rows | 50 |
| Pilot rows with audio path | 50 |
| Pilot unique WAV files | 46 |
| Pilot review clips | 50 |
| Pilot clip duration minutes | 4.58 |
| Pilot candidate schema errors | 0 |
| Pilot accepted rows | 0 |
| Dialect attribution manifest rows | 50 |
| Dialect-marked eojeol units | 66 |
| Non-dialect eojeol units | 471 |
| ASR evaluated utterances | 50 |
| ASR missing outputs | 0 |
| Dialect unit error rate | 0.455 |
| Dialect surface preservation rate | 0.227 |
| Dialect standard normalization rate | 0.318 |
| Plain unit error rate | 0.172 |
| Dialect/plain error-rate ratio | 2.643 |
| Dialect/plain odds ratio | 4.012 |
| Approx. two-proportion p-value | 1.10e-07 |
| Text-audit meaning-preserved/acceptable units | 50 |
| Text-audit low-impact units | 7 |
| Text-audit potentially harmful units | 9 |

No weak label was promoted to gold. That is intentional.

## ASR Runtime Check

`../japko/whisper_proto` has `faster-whisper 1.2.1` installed and is configured with `WHISPER_MODEL=medium`. The `medium` model is now cached under the Hugging Face cache, and local-only loading succeeds. The model cache is about 1.4 GB.

ASR command:

```bash
../japko/whisper_proto/.venv/bin/python scripts/run_faster_whisper_pilot_asr.py \
  research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_medium.local.jsonl \
  medium
```

## Round 2 Executed

Everything reachable without a human reviewer is now done. See [pilot round 2 report](../aihub_119_pilot_round2/README.md).

- Built the 16-row [audio review packet](../aihub_119_dialect_audio_review/README.md); it is generated, not reviewed.
- Added `scripts/run_dialect_significance_tests.py` and re-tested the dialect gap with utterance clustering.
- Cached `Systran/faster-whisper-large-v3` and transcribed the 50 pilot clips with it.
- Added `scripts/analyze_critical_span_preservation.py` and audited the AICC critical-span metric.
- Found and removed three measurement artifacts: numeral-notation false losses, single-syllable false preservations, and 16 phantom labels out of 74.

| Round 2 measure | medium | large-v3 |
|---|---:|---:|
| Dialect unit error rate | 0.455 | 0.409 |
| Plain unit error rate | 0.172 | 0.161 |
| Difference, cluster bootstrap 95% CI | 0.283 [0.169, 0.394] | 0.248 [0.130, 0.367] |
| Utterance-stratified MH odds ratio | 4.10 [2.19, 7.70] | 3.31 [1.82, 6.04] |
| Within-utterance permutation p | <5.0e-05 | <5.0e-05 |
| Busan minus other Gyeongsang | 0.033 [-0.197, 0.263] | 0.006 [-0.219, 0.223] |
| Critical-span strict loss rate | 0.103 [0.019, 0.203] | 0.069 [0.000, 0.161] |

## Next Tasks

Only the first item needs a human.

1. Human/audio-review the 16 rows in `../aihub_119_dialect_audio_review/dialect_audio_review_sheet.local.tsv`, then freeze accepted pilot semantic annotations.
2. Redesign critical-span mining to require an eojeol-boundary hit, then re-label. 21.6% of the current weak labels name no real eojeol.
3. Add one Korean ASR baseline so the paper is not Whisper-only.
4. Expand to a speaker-independent split from the 843 validated validation WAV files.
5. Human-review `../aihub_119_pilot_review_packet/pilot_reviewer_sheet.local.tsv` while listening to `data/interim/aihub_119_pilot_clips`, then scale to `gold_review_queue.local.jsonl`.

## Download Status

AI-Hub 119 validation source audio is downloaded and zip-validated:

- filekey: `572714`
- archive: `(비식별화완료)경상도_2.zip`
- size: 28 GB
- audio files: 843 WAV
- label/audio stem matches: 843

Do not download training source audio yet.
