# Experiment Plans

초기 실험은 아직 실행하지 않는다. 먼저 데이터 라이선스와 선행연구 gap을 검증한다.

## Candidate Experiment Matrix

| Axis | Levels |
| --- | --- |
| Speech variety | standard Korean, Busan/Gyeongsang dialect |
| Acoustic condition | clean, telephone-bandlimited, noisy, overlapped, fast speech |
| Model | Whisper, Korean Conformer/FastConformer, dialect fine-tuned, adapter/LoRA, selective allophone auxiliary |
| Transcript target | dialect-preserving transcript, standard normalized transcript |
| Downstream task | intent, slot, TA category, clarification trigger |
| Metric | WER, CER, semantic-critical error rates, Intent Acc, Slot F1, Task Success |

## Minimum Baselines

1. Zero-shot ASR.
2. Standard fine-tuning.
3. Dialect fine-tuning.
4. Telephone/noise augmentation.
5. Dialect + telephone augmentation.
6. Proposed semantic-critical or selective phonology-aware model.

## Ablation Requirements

- Remove dialect metadata.
- Remove telephone augmentation.
- Remove semantic-critical weighting.
- Replace selective allophone auxiliary with full phoneme/allophone auxiliary.
- Compare 1-best transcript with N-best/confidence-aware downstream processing.

## Executed Runs

- [pilot_001](runs/pilot_001/README.md): synthetic fixture smoke test for metadata inspection and semantic-critical scoring. This validates the pipeline mechanics only; it is not a scientific result.
- [aihub_119_busan_slice](runs/aihub_119_busan_slice/summary.md): label-side Busan/non-Busan Gyeongsang manifest without utterance text.
- [aihub_119_dialect_taxonomy](runs/aihub_119_dialect_taxonomy/summary.md): label-side dialect transformation taxonomy without utterance text.
- [aihub_119_semantic_review_pack](runs/aihub_119_semantic_review_pack/README.md): balanced local semantic annotation queue. The raw transcript queue is `.local.jsonl` and git-ignored.
- [aihub_119_semantic_preannotations](runs/aihub_119_semantic_preannotations/README.md): weak schema-shaped local seeds for human review. These are not gold labels.
- [semantic preannotation validation](runs/aihub_119_semantic_preannotations/validation_summary.md): schema and coverage summary for the weak local seeds, without transcript text.
- [aihub_119_critical_span_candidates](runs/aihub_119_critical_span_candidates/README.md): extra label-side mining run for under-covered AICC-critical span categories.
- [aihub_119_critical_span_preannotations](runs/aihub_119_critical_span_preannotations/validation_summary.md): schema validation for mined critical-span weak preannotations.
- [aihub_119_gold_readiness](runs/aihub_119_gold_readiness/README.md): readiness decision and missing data items before ASR experiments.
- [aihub_119_gold_review](runs/aihub_119_gold_review/README.md): local-only human-review queue for gold annotation.
- [aihub_119_gold_freeze](runs/aihub_119_gold_freeze/README.md): dry-run gold freeze; currently 0 accepted rows by design.
- [aihub_119_audio_subset_request](runs/aihub_119_audio_subset_request/README.md): no-download audio request manifest pointing at AI-Hub filekey `572714`.
- [aihub_119_next_actions](runs/aihub_119_next_actions/README.md): ordered task list and large-download stop point.
- [aihub_119_validation_audio_download](runs/aihub_119_validation_audio_download/README.md): downloaded and zip-validated AI-Hub 119 validation source audio.
- [aihub_119_pilot_audio_subset](runs/aihub_119_pilot_audio_subset/README.md): 50-row balanced local review/ASR pilot with extracted validation WAV files.
- [aihub_119_pilot_review_packet](runs/aihub_119_pilot_review_packet/README.md): 50 utterance-level review clips plus a local reviewer TSV.
- [aihub_119_pilot_gold_freeze](runs/aihub_119_pilot_gold_freeze/README.md): pilot freeze dry-run; currently 0 accepted rows by design.
- [aihub_119_dialect_attribution_probe](runs/aihub_119_dialect_attribution_probe/README.md): problem-definition probe plus `faster-whisper:medium` pilot ASR attribution result.
- [aihub_119_dialect_attribution_probe_smoke](runs/aihub_119_dialect_attribution_probe_smoke/README.md): synthetic standard-normalization smoke test for the attribution evaluator.
