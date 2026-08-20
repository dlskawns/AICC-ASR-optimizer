# Pilot Experiment Status

## What Ran

The first executable pilot used a synthetic local fixture to validate the metadata and semantic-critical scoring pipeline. After AI-Hub 119 validation labels were acquired, the lab also ran a real label-side Busan slice, dialect taxonomy pass, and semantic review pack build.

Artifacts:

- [Pilot report](../experiments/runs/pilot_001/README.md)
- [Metadata summary](../experiments/runs/pilot_001/metadata_summary.json)
- [Semantic metrics JSON](../experiments/runs/pilot_001/semantic_metrics_summary.json)
- [Semantic metrics Markdown](../experiments/runs/pilot_001/semantic_metrics_summary.md)
- [AI-Hub 119 validation metadata summary](../experiments/runs/aihub_119_validation_labels_metadata_summary.md)
- [Busan slice summary](../experiments/runs/aihub_119_busan_slice/summary.md)
- [Dialect taxonomy summary](../experiments/runs/aihub_119_dialect_taxonomy/summary.md)
- [Busan dialect TA taxonomy](../evaluation/busan_dialect_ta_error_taxonomy.md)
- [Semantic review pack summary](../experiments/runs/aihub_119_semantic_review_pack/summary.json)
- [Semantic review pack README](../experiments/runs/aihub_119_semantic_review_pack/README.md)
- [Weak semantic preannotation summary](../experiments/runs/aihub_119_semantic_preannotations/summary.json)
- [Weak semantic preannotation README](../experiments/runs/aihub_119_semantic_preannotations/README.md)
- [Semantic annotation validation summary](../experiments/runs/aihub_119_semantic_preannotations/validation_summary.md)
- [Critical span candidate summary](../experiments/runs/aihub_119_critical_span_candidates/summary.json)
- [Critical span preannotation validation](../experiments/runs/aihub_119_critical_span_preannotations/validation_summary.md)
- [Gold readiness report](../experiments/runs/aihub_119_gold_readiness/README.md)
- [Next actions](../experiments/runs/aihub_119_next_actions/README.md)
- [Gold freeze dry-run](../experiments/runs/aihub_119_gold_freeze/README.md)
- [Audio subset request](../experiments/runs/aihub_119_audio_subset_request/README.md)
- [Validation audio download](../experiments/runs/aihub_119_validation_audio_download/README.md)
- [Pilot audio subset](../experiments/runs/aihub_119_pilot_audio_subset/README.md)
- [Pilot review packet](../experiments/runs/aihub_119_pilot_review_packet/README.md)
- [Pilot gold freeze dry-run](../experiments/runs/aihub_119_pilot_gold_freeze/README.md)
- [Dialect attribution probe](../experiments/runs/aihub_119_dialect_attribution_probe/README.md)

## Why Synthetic

The synthetic fixture exists only to exercise the pipeline and catch implementation bugs before real ASR outputs exist. The AI-Hub 119 validation labels now provide real text-side dialect annotations and a local annotation queue, but no audio baseline has been run yet.

## Key Result

The deliberately weak `generic_asr` output has:

- CER 0.083.
- WER 0.207.
- Intent Accuracy 0.800.
- Slot F1 0.500.
- Semantic-Critical Error Rate 0.667.

The `dialect_aware_asr` fixture output has zero errors by construction.

## Research Implication

The pipeline can now test the core paper claim once real ASR outputs exist:

> Similar WER can hide different levels of AICC-critical semantic loss.

The pilot does not prove that claim empirically. It proves that the lab can measure it.

The label-side taxonomy adds a concrete pre-ASR claim: Busan-labeled dialect eojeols are dominated by lexical replacement, ending/particle variants, and vowel shifts, with Busan showing a higher vowel-shift share than non-Busan Gyeongsang in the validation subset.

The semantic review pack samples 510 utterances by cohort and primary dialect category. Ten main cohort/category groups have 50 rows each; `same_surface` has 5 Busan and 5 non-Busan rows because the candidate pool is small. Raw transcript text exists only in `semantic_review_queue.local.jsonl`, which is git-ignored.

The weak semantic preannotation pass produced 160 schema-valid local rows from those 510 review items. It is not gold: most inferred domains remain `other` because AI-Hub 119 is not a contact-center corpus. The value is schema validation and human-review prioritization, not final AICC labels. The validator confirms 160 valid rows, 0 schema errors, and 0 rows with audio paths.

The pre-data analysis found that the 160 weak rows under-covered `amount`, `date_time`, and `intent_cue`. A second full-label mining pass selected 398 dialect-bearing critical-span candidates: 198 Busan and 200 non-Busan Gyeongsang. The schema validator confirms 398 valid weak preannotation rows, 0 schema errors, and 0 rows with audio paths.

The gold review queue now contains 398 unreviewed rows. The freeze dry-run emits 0 gold rows, which confirms that weak labels do not enter the gold set without `review_status=accepted`. The audio subset request manifest points at AI-Hub filekey `572714`, the 28 GB validation source-audio archive; at that stage it intentionally did not start a download.

After disk cleanup, local free space was about 36 GiB. The validation source-audio download target now has a 90 GB guard and correctly stops before transfer on the current filesystem.

AI-Hub 119 validation source audio filekey `572714` was later downloaded successfully. The zip contains 843 WAV files, passes `unzip -tq`, and matches all 843 validation label JSON stems.

The first real audio pilot subset is now materialized locally. It contains 50 critical-span review rows, balanced as 25 Busan and 25 non-Busan Gyeongsang rows. All 50 rows have an attached local audio path, represented by 46 unique WAV files because several selected utterances share recording files. Critical-span coverage is now broad enough for a first reviewer pass: negation 17, confirmation 17, intent cue 15, date/time 12, and amount 11. This subset is still review/ASR pilot material, not frozen gold.

The review packet now cuts those long recordings into 50 utterance-level WAV clips. The clip set is 8.5 MB and 4.58 minutes total, so a reviewer can audit the pilot without scanning 46 full recording files. The local candidate annotations validate against the semantic-critical schema with 50 valid rows and 0 schema errors. The pilot freeze dry-run still emits 0 gold rows because all rows remain `unreviewed`; this confirms the weak-label guard is working.

The problem-definition order has been corrected: before claiming AICC impact, the lab now has a dialect attribution probe. The pilot probe contains 50 utterances, 66 dialect-marked eojeol units, and 471 non-dialect units. A synthetic standard-normalization smoke test confirms that the evaluator separates dialect surface change from meaning-preserving normalization; this smoke test is not a scientific result.

The first real ASR attribution run used `faster-whisper:medium` through `../japko/whisper_proto`. It evaluated all 50 utterances with 0 missing outputs. Dialect-marked unit error rate is 0.455, plain unit error rate is 0.172, the dialect/plain error-rate ratio is 2.643, and the odds ratio is 4.012 with an approximate two-proportion p-value of 1.10e-07. Among dialect-marked units, 0.227 preserve the dialect surface, 0.318 are standard-normalized, and 0.455 are missing or substituted. This supports continuing the dialect problem definition, but it remains a pilot signal until speaker-independent gold review is available.

A text-only semantic audit then narrowed the 30 raw missing/substituted dialect-unit cases to 9 potentially harmful semantic-shift candidates and 7 low-impact discourse/hedge-loss candidates. The remaining 50 of 66 dialect-marked units are either surface-preserved, standard-normalized, or acceptable colloquial normalizations. This refines the problem definition: the paper should measure harmful semantic shifts, not treat every dialect-surface mismatch as AICC failure.

## Next Required Step

1. Keep `busan_strict` as the primary paper slice and broader Busan as sensitivity analysis.
2. Human/audio-review the 9 potentially harmful and 7 low-impact candidates in `dialect_asr_text_audit.local.jsonl`.
3. Human-review `pilot_reviewer_sheet.local.tsv` with the 50 utterance-level clips for the semantic-critical layer.
4. Freeze accepted pilot annotations and then add a second ASR baseline.
5. Defer training source-audio downloads until the validation pilot baseline exposes the actual adaptation target.
