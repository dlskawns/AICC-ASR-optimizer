# Scripts

## AI-Hub Pilot Download

```bash
AIHUB_API_KEY='발급받은키' ./scripts/download_aihub_pilot.sh dataset119-validation-labels
```

Targets:

- `dataset119-validation-labels`: AI-Hub 119 경상도 validation labels only.
- `dataset119-all-labels`: AI-Hub 119 training + validation labels.
- `dataset119-validation-source-audio`: AI-Hub 119 validation source audio only, filekey `572714`.
- `senior-gyeongsang-validation-labels`: AI-Hub 71517 중/노년층 경상 validation labels.

The script does not store the API key. It calls the same AI-Hub download endpoint used by `aihubshell`, then performs a portable `.partN` merge and `unzip -t` integrity check. This avoids the official shell's macOS/BSD merge failure mode where a completed-looking merge can leave a zero-byte zip.

The validation source-audio target has a 90 GB free-space guard because the 28 GB archive can require multiple copies during tar download, part merge, and zip validation. To use a larger disk:

```bash
AIHUB_TARGET_DIR=/Volumes/large-disk/aihub_gyeongsang_119_validation_audio \
AIHUB_API_KEY='발급받은키' \
./scripts/download_aihub_pilot.sh dataset119-validation-source-audio
```

## Metadata Inspection

```bash
uv run scripts/inspect_aihub_metadata.py data/fixtures/aihub_sample \
  --output research/experiments/runs/pilot_001/metadata_summary.json
```

Use this after AI-Hub approval to summarize region fields and transcript annotation coverage.

## Semantic-Critical Evaluation

```bash
uv run scripts/evaluate_semantic_critical.py \
  data/fixtures/pilot/gold_annotations.jsonl \
  data/fixtures/pilot/asr_outputs.jsonl \
  --output-dir research/experiments/runs/pilot_001
```

Use this to score ASR outputs with CER/WER, Intent Accuracy, Slot F1, and semantic-critical error rates.

## Busan Slice Manifest

```bash
uv run scripts/build_busan_slice_manifest.py \
  data/raw/aihub_gyeongsang_119 \
  --output-dir research/experiments/runs/aihub_119_busan_slice
```

Use this after downloading AI-Hub 119 labels to create a Busan/non-Busan Gyeongsang utterance manifest without storing utterance text.

## Dialect Taxonomy

```bash
uv run scripts/build_dialect_taxonomy.py \
  data/raw/aihub_gyeongsang_119 \
  research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz \
  --output-dir research/experiments/runs/aihub_119_dialect_taxonomy
```

Use this to summarize dialect-marked eojeol transformations by Busan cohort, non-Busan Gyeongsang cohort, and TA-risk category.

## Semantic Review Pack

```bash
uv run scripts/build_semantic_review_pack.py \
  data/raw/aihub_gyeongsang_119 \
  research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz \
  --output-dir research/experiments/runs/aihub_119_semantic_review_pack
```

Use this to create a balanced local annotation queue by cohort and primary dialect category. The raw transcript queue is written as `semantic_review_queue.local.jsonl` and must remain local. The shareable manifest stores only hashes, metadata, category counts, and transcript lengths.

## Weak Semantic Preannotations

```bash
uv run scripts/build_weak_semantic_preannotations.py \
  research/experiments/runs/aihub_119_semantic_review_pack/semantic_review_queue.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_semantic_preannotations
```

Use this to create schema-shaped local review seeds from the semantic review queue. These rows are not gold labels. They are useful only for checking schema coverage and prioritizing human review.

## Critical Span Candidate Mining

```bash
uv run scripts/mine_critical_span_candidates.py \
  data/raw/aihub_gyeongsang_119 \
  research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz \
  --output-dir research/experiments/runs/aihub_119_critical_span_candidates
```

Use this when the balanced dialect review queue under-covers AICC-critical categories. It mines the full label set for dialect-bearing utterances with negation, confirmation, amount, date/time, or intent cues. The raw transcript queue is `.local.jsonl`; the manifest is safe to share.

## Gold Review Queue

```bash
uv run scripts/prepare_gold_review_queue.py \
  research/experiments/runs/aihub_119_critical_span_candidates/critical_span_review_queue.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_gold_review
```

Use this to normalize weak preannotations into a human-review queue. The queue is local-only and must be edited by a reviewer before gold freeze.

## Gold Freeze

```bash
uv run scripts/freeze_gold_annotations.py \
  research/experiments/runs/aihub_119_gold_review/gold_review_queue.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_gold_freeze
```

Use this after review. Only rows with `review_status=accepted` are emitted as frozen gold. Unreviewed rows produce zero gold rows.

## Audio Subset Manifest

```bash
uv run scripts/build_audio_subset_manifest.py \
  research/experiments/runs/aihub_119_gold_review/gold_review_queue.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_audio_subset_request
```

Use this after gold freeze to generate the audio request list for accepted rows. `--include-unreviewed` is allowed only for planning. The required AI-Hub validation source-audio archive is filekey `572714`, 28 GB, so this script intentionally does not download it.

## Pilot Audio Subset

```bash
uv run scripts/prepare_pilot_audio_subset.py \
  research/experiments/runs/aihub_119_gold_review/gold_review_queue.local.jsonl \
  research/experiments/runs/aihub_119_critical_span_candidates/critical_span_manifest.jsonl \
  --output-dir research/experiments/runs/aihub_119_pilot_audio_subset \
  --max-rows 50
```

Use this after the AI-Hub 119 validation source-audio archive is downloaded. It extracts only a balanced local pilot subset from the validated archive into `data/interim/aihub_119_pilot_audio`. The review queue and audio manifest are `.local.jsonl` files and must remain local.

## Pilot Review Packet

```bash
uv run scripts/build_pilot_review_packet.py \
  research/experiments/runs/aihub_119_pilot_audio_subset/pilot_gold_review_queue.local.jsonl \
  research/experiments/runs/aihub_119_pilot_audio_subset/pilot_audio_manifest.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_pilot_review_packet
```

Use this to cut utterance-level review clips from the local pilot WAV files and produce a reviewer TSV. The TSV and candidate annotation JSONL contain restricted transcript text and are local-only.

## Dialect Attribution Probe

```bash
uv run scripts/run_dialect_attribution_probe.py \
  research/experiments/runs/aihub_119_pilot_review_packet/pilot_review_manifest.jsonl \
  --output-dir research/experiments/runs/aihub_119_dialect_attribution_probe
```

Use this before making AICC claims. It builds a local ASR input manifest with dialect-marked and non-dialect eojeols. After an ASR output JSONL exists, pass `--asr ASR_OUTPUTS.jsonl` to compare dialect-unit error, surface normalization, and non-dialect-unit error rates.

## Faster-Whisper Pilot ASR

```bash
../japko/whisper_proto/.venv/bin/python scripts/run_faster_whisper_pilot_asr.py \
  research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_medium.local.jsonl \
  medium
```

Use this to reuse the local `../japko/whisper_proto` `faster-whisper` environment and produce ASR hypotheses for the dialect attribution probe. The runner uses `local_files_only=True`, so it does not start model downloads during ASR. In the current pilot, `medium` is cached locally.

## Dialect ASR Error Analysis

```bash
uv run scripts/analyze_dialect_asr_errors.py \
  research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_medium.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_dialect_attribution_probe
```

Use this after ASR to split dialect-marked units into surface-preserved, standard-normalized, and missing/substituted outcomes. The detailed case file is local-only because it includes transcript text.

## Speaker-Independent Holdout Split

```bash
uv run scripts/build_speaker_independent_split.py \
  research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz \
  --output-dir research/experiments/runs/aihub_119_speaker_independent_split \
  --per-cohort 150 --max-per-speaker 2
```

Use this when a result needs to generalise past the 50-utterance pilot. The split excludes every recording the pilot used and caps how many utterances one speaker contributes, so a few speakers cannot carry the outcome. Selection is deterministic through a content hash, so no seed is needed. Clips are cut one recording at a time and the staged source WAV is deleted immediately, so peak disk stays at one recording rather than the whole subset. The output manifest uses the same schema as the pilot probe, so the ASR runners, the significance tests, and the critical-span audit consume it unchanged.

## Dialect Attribution Significance Tests

```bash
uv run scripts/run_dialect_significance_tests.py \
  research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_medium.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_large_v3.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_dialect_significance
```

Use this instead of the probe's two-proportion z-test when the dialect gap is being claimed. Eojeol units are nested in utterances, so the probe's unit-independent p-value overstates the evidence. This script re-tests the same contrast with an utterance-level cluster bootstrap, a within-utterance conditional permutation of the dialect flag, and a Mantel-Haenszel odds ratio stratified by utterance. It accepts several ASR output files at once and labels each result from the `model` field. Outputs carry counts and statistics only.

## AICC Critical Span Preservation

```bash
uv run scripts/analyze_critical_span_preservation.py \
  research/experiments/runs/aihub_119_pilot_review_packet/pilot_candidate_annotations.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_medium.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_critical_span_preservation
```

Use this to score whether the ASR still carries the annotated business-critical spans. Do not replace it with a substring check: Sino-Korean amounts in the reference reach the ASR as Arabic numerals, single-syllable markers such as `안` and `네` occur inside unrelated words, and the weak preannotations themselves were mined by substring, so a cancellation cue like `해지` was harvested out of ordinary `-해지다` verb forms. The script parses numerals to values, rejects labels that name no real eojeol in the reference as `phantom_label`, grades remaining matches by eojeol boundary, and reports strict and inclusive loss rates as bounds. The span-level case file is local-only.

## Critical Span Re-mining

```bash
uv run scripts/remine_critical_spans.py \
  research/experiments/runs/aihub_119_pilot_review_packet/pilot_candidate_annotations.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_critical_span_remine
```

Use this instead of the substring cues in `build_weak_semantic_preannotations.py` when critical spans are being mined. That miner tests `cue in transcript` and scans the amount pattern across the whole string, so it harvests business cues out of ordinary inflected verbs and reads amounts across an eojeol break. This miner requires every cue to open a real eojeol, declares per cue whether it may take inflection (`prefix`) or must stand alone (`exact`), and matches amounts token-wise. On the 50-utterance pilot it takes the phantom-label rate from 21.6% to 1.8%. Output uses the annotation schema, so it feeds `analyze_critical_span_preservation.py` directly, and it is local-only because it carries transcript text.

## Korean wav2vec2 Pilot ASR

```bash
../japko/whisper_proto/.venv/bin/python -c "
from huggingface_hub import snapshot_download
print(snapshot_download('kresnik/wav2vec2-large-xlsr-korean'))
"

../japko/whisper_proto/.venv/bin/python scripts/run_wav2vec2_korean_pilot_asr.py \
  research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/wav2vec2_korean.local.jsonl
```

Use this to add a non-Whisper, Korean-trained baseline so the dialect gap is not a claim about one model family. The runner reuses the `../japko/whisper_proto` environment, which already has torch and transformers, reads 16 kHz mono clips directly, and loads with `local_files_only=True`, so cache the model first.

## Dialect ASR Audio Review Packet

```bash
uv run scripts/build_dialect_audio_review_packet.py \
  research/experiments/runs/aihub_119_dialect_attribution_probe/dialect_asr_text_audit.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_dialect_audio_review
```

Use this after the text-only audit to build the human/audio confirmation packet. It keeps only the units whose text audit status is `potentially_harmful_semantic_shift` or `low_impact_discourse_or_hedge_loss`, and drops `meaning_preserved_or_acceptable_normalization`. The reviewer sheet and queue contain transcript text and are local-only; the manifest and summary carry metadata only, without transcript text or dialect surface forms. Reviewer decisions are `harmful`, `acceptable`, `artifact`, or `unclear`.

## Semantic Annotation Validation

```bash
uv run scripts/validate_semantic_annotations.py \
  research/experiments/runs/aihub_119_semantic_preannotations/weak_semantic_preannotations.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_semantic_preannotations
```

Use this after human review to validate schema conformance and summarize domain, critical-span, slot, and audio-path coverage without printing transcript text.

## Dialect Control Pairs

```bash
uv run scripts/build_dialect_control_pairs.py \
  research/experiments/runs/aihub_119_speaker_independent_split/asr_input_manifest.local.jsonl \
  research/experiments/runs/aihub_119_holdout_critical_spans/remined_annotations.local.jsonl \
  research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz \
  --output-dir research/experiments/runs/aihub_119_dialect_control_pairs
```

Use this to ask whether dialect marking damages AICC critical spans. Do not use surface overlap between a critical span and a dialect eojeol: the two barely co-occur, and going from 50 to 300 utterances moved the overlapping-span count only from 4 to 5. This builds the comparison at utterance level instead, pairing each dialect-bearing utterance with a length-matched dialect-free utterance from the same speaker in the same recording, so speaker, channel, session, and topic are fixed inside a pair. Manifests are local-only.

## Dialect Control Pair Comparison

```bash
uv run scripts/compare_dialect_control_pairs.py \
  research/experiments/runs/aihub_119_dialect_control_pairs/pair_manifest.jsonl \
  --case-dir research/experiments/runs/aihub_119_speaker_independent_split \
  --case-annotations research/experiments/runs/aihub_119_holdout_critical_spans/remined_annotations.local.jsonl \
  --control-dir research/experiments/runs/aihub_119_dialect_control_pairs \
  --output-dir research/experiments/runs/aihub_119_dialect_control_comparison
```

Scores the pairs with a paired bootstrap, a within-pair arm-swap permutation, and McNemar. Read the placebo line first: non-dialect unit error should be similar in both arms, and if it is not, the pairs differ in something beyond dialect marking and the critical-span number cannot be trusted.

## Cue-Bearing Dialect Split

```bash
uv run scripts/build_cue_bearing_dialect_split.py \
  data/raw/aihub_gyeongsang_119 \
  research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz \
  --output-dir research/experiments/runs/aihub_119_cue_bearing_split
```

Use this to test whether dialect marking hurts an AICC cue when the cue word itself is the dialect-marked eojeol. Those cases are too rare to catch by sampling, five of ninety-three in the round 4 holdout, so this scans the whole label set for them and pairs each with an utterance where the same speaker carries the same cue category on a plain eojeol. Speaker, recording, and cue category are fixed inside a pair. The surviving cue inventory is dominated by confirmation markers, so the split cannot speak for amount or intent cues.

## Cue-Bearing Pair Comparison

```bash
uv run scripts/compare_cue_bearing_pairs.py \
  research/experiments/runs/aihub_119_cue_bearing_split \
  --output-dir research/experiments/runs/aihub_119_cue_bearing_comparison
```

Scores the cue pairs with a paired bootstrap, a within-pair arm-swap permutation, and McNemar, and breaks the result down by cue category. Read the placebo line first: non-dialect unit error should not differ between arms.
