# Research Session Handoff

Updated: 2026-08-19 KST

This is the first file a new agent/session should read after `AGENTS.md`.

## One-Line State

ASR is substantially less stable on dialect-marked eojeol units than on non-dialect units. The gap survives utterance-level clustering, reproduces across three baselines (`faster-whisper:medium`, `faster-whisper:large-v3`, a Korean wav2vec2 CTC model), and grows rather than shrinks on a 300-utterance holdout that shares no recording with the pilot. The AICC critical-span layer needed both a metric repair and a mining-rule repair, and two within-speaker paired tests locate the damage: dialect marking elsewhere in an utterance costs nothing, but when the AICC cue word is itself the dialect-marked eojeol its loss rate rises sharply. About half of that is harmless normalisation to the standard form; the genuine damage gap settles around 0.15 to 0.25 across three baselines and two cue categories. The penalty is local to dialect tokens and becomes AICC damage only where those tokens carry business cues and the model fails to normalise them. When it does fail, it usually substitutes another word rather than dropping the cue, so downstream receives a confident wrong reading rather than a detectable gap.

## Read These First

1. [AGENTS.md](AGENTS.md): mandatory lab rules, agent roles, and output shape.
2. [This handoff](HANDOFF.md): current state, claims, risks, and next steps.
3. [Dialect attribution probe README](research/experiments/runs/aihub_119_dialect_attribution_probe/README.md): run-level status and reproduction commands.
4. [Metric correction](research/experiments/runs/aihub_119_metric_correction/README.md): the corrected cue-preservation rule and the numbers it changes. This overrides the cue figures printed in rounds 6, 7, and 8.
5. [Pilot round 8 report](research/experiments/runs/aihub_119_pilot_round8/README.md): what a lost cue becomes, substitution versus deletion.
6. [Pilot round 7 report](research/experiments/runs/aihub_119_pilot_round7/README.md): how much of the round 6 loss is real damage, negation generalisation, and cue-level cohort test.
7. [Pilot round 6 report](research/experiments/runs/aihub_119_pilot_round6/README.md): cue-bearing dialect eojeols, the positive result that completes the round 4-5-6 arc.
8. [Pilot round 5 report](research/experiments/runs/aihub_119_pilot_round5/README.md): within-speaker paired test of dialect versus AICC critical-span loss.
9. [Pilot round 4 report](research/experiments/runs/aihub_119_pilot_round4/README.md): the 300-utterance speaker-disjoint holdout.
10. [Pilot round 3 report](research/experiments/runs/aihub_119_pilot_round3/README.md): mining-rule repair and the non-Whisper Korean baseline.
11. [Pilot round 2 report](research/experiments/runs/aihub_119_pilot_round2/README.md): clustered significance, model-scale ablation, and the critical-span metric audit.
12. [Pilot conclusion report](research/experiments/runs/aihub_119_dialect_attribution_probe/pilot_conclusion_report.md): round 1 conclusion, plots, and paper-safe interpretation. Partly superseded by rounds 2 and 3.
13. [Text-only audit report](research/experiments/runs/aihub_119_dialect_attribution_probe/text_audit_report.md): refined harmful-vs-acceptable semantic audit.
14. [Audio review packet](research/experiments/runs/aihub_119_dialect_audio_review/README.md): the 16-unit human/audio confirmation packet and reviewer protocol.
15. [Next actions](research/experiments/runs/aihub_119_next_actions/README.md): current task queue and download stop point.

Optional background:

- [Problem framing](research/wiki/01-problem-framing.md)
- [Pilot experiment status](research/wiki/07-pilot-experiment.md)
- [Experiment plan index](research/experiments/README.md)
- [Script commands](scripts/README.md)

## Current Research Claim

Safe current claims:

> ASR shows high surface instability on dialect-marked eojeols compared with non-dialect eojeols, and the gap survives utterance-level clustering in every baseline and both splits. On a 300-utterance holdout that shares no recording with the pilot, the cluster bootstrap 95% CI on the difference is [0.418, 0.532] for `faster-whisper:medium`, [0.411, 0.525] for `faster-whisper:large-v3`, and [0.291, 0.367] for `wav2vec2-large-xlsr-korean`; utterance-stratified odds ratios are 9.30, 8.74, and 6.23. A within-utterance permutation of the dialect flag never reached the observed gap in 20000 draws for any model. Text-only audit suggests many surface mismatches are acceptable standard or colloquial normalizations, so AICC evaluation must isolate harmful semantic shifts rather than treating every dialect-surface mismatch as task failure.

> The dialect penalty is neither a model-capacity artifact, nor a Whisper artifact, nor a pilot-sample artifact. It reproduces in a Korean-specialised CTC architecture, and on the speaker-disjoint holdout it grows rather than shrinks: `medium` goes from 2.64x to 4.05x and `large-v3` from 2.54x to 4.02x.

> Measuring the dialect-to-AICC-damage link through surface overlap between critical spans and dialect eojeols does not work, and more data does not fix it. Going from 50 to 300 utterances moved the overlapping-span count only from 4 to 5 of 93, because AICC markers and dialect-marked eojeols barely co-occur on the surface in this corpus.

> Rebuilt at utterance level, the link is not there at the resolution this pilot can see. In 63 within-speaker pairs, an utterance carrying dialect marking loses no more AICC critical spans than the same speaker's length-matched dialect-free utterance: +0.028 [-0.056, 0.114] for `medium`, -0.018 [-0.102, 0.066] for `large-v3`, +0.023 [-0.151, 0.198] for wav2vec2, with signs disagreeing and a clean placebo on non-dialect unit error. The dialect penalty appears to be local to the dialect tokens rather than a whole-utterance degradation.

> When the AICC cue word is itself a dialect-marked eojeol, it is lost far more often. Under the corrected preservation rule, cue loss in the dialect arm versus the plain arm is 0.309 against 0.096 for `medium`, 0.267 against 0.092 for `large-v3`, and 0.815 against 0.528 for wav2vec2 on the confirmation split, and 0.202 against 0.043, 0.202 against 0.043, and 0.634 against 0.405 on the negation split. All six gaps exclude zero, at +0.16 to +0.29. The placebo on non-dialect unit error is null throughout. Read with the round 5 null, the dialect penalty is local to dialect tokens and turns into AICC damage only where those tokens carry business cues.

> A large share of that cue loss is harmless. Outcomes split four ways: the dialect form written as spoken, the standard form of the same word, the cue morpheme surviving under different inflection, and the cue gone. For Whisper, 34 to 48 percent of dialect-marked cues land in the two middle classes, where the business meaning survives.

> The effect is not confirmation-only. A negation-only split of 185 pairs reproduces it in all three baselines at +0.159, +0.159, and +0.228.

> A damaged cue is usually replaced, not dropped. Among the cases whose position can be aligned against surviving neighbour eojeols, substitution outnumbers deletion in five of six model-by-category combinations and ties in the sixth, at 0.50 to 0.82 of resolved cases. Downstream that means a confident wrong reading rather than a detectable gap, which a confidence threshold or missing-value guard would not catch.

> No substitution dictionary exists. Of the substitutions observed, almost every replacement surface is unique: 21 distinct for 24 in `medium`, 14 for 15 in `large-v3`, 24 for 24 in wav2vec2. Post-hoc string mapping is not a viable correction; the fix has to be acoustic or model-level.

> A Korean AICC critical-span metric cannot be built from string containment, and neither can its label set. Substring scoring reported 91.7% loss on amounts that were only a numeral-notation difference and near-total preservation on single-syllable markers that matched inside unrelated words. Substring mining additionally produced labels that named no real eojeol: 21.6% of the weak critical-span labels. Re-mining with eojeol-boundary rules brings that to 1.8%.

Do not yet claim:

- Busan dialect is uniquely harder than other Gyeongsang dialects. On the holdout, with intervals half as wide as the pilot's, all three baselines still straddle zero and disagree on sign: -0.023 [-0.132, 0.087], -0.017 [-0.125, 0.091], 0.011 [-0.055, 0.077]. This is now a powered null, not an unknown.
- Every dialect ASR surface error harms AICC text analytics.
- The critical-span loss rate is an AICC task failure rate. The labels are weak and unreviewed.
- Dialect marking has no effect on AICC critical-span loss. Round 5 detected none at utterance level, but round 6 found a large effect once the cue word itself is dialect-marked. The correct statement is that the effect is local, not absent.
- Round 6's headline numbers as AICC damage. Round 7 shows about half of that loss is standard-form normalisation, which preserves meaning. Quote the genuine gap, not the surface gap.
- Generalisation to amount, date/time, or intent cues. Those categories effectively never land on a dialect-marked eojeol in this corpus, so no test is possible here.
- The substitution-versus-deletion split as a property of all lost cues. Roughly two thirds of absent cues are `context_lost` and could not be aligned, and the resolved subset may lean toward easier utterances. For wav2vec2 only about 15 percent resolve at all.
- That substitution always flips the meaning. The classifier only establishes that something other than the cue sits in its position.
- Dialect-marked critical spans are lost more often than other spans. Only 4 spans in the pilot and 5 in the holdout are dialect-marked, so that contrast stays underpowered at both sizes.
- `large-v3` is better than `medium` on dialect. The pilot showed a small gap reduction that the holdout does not reproduce: 4.05x versus 4.02x, with overlapping intervals.
- Effect sizes from the pilot and the holdout are interchangeable. The two splits were sampled differently, so always name the split.
- Anything about speaker sex or age. The holdout is 228 female to 72 male and 205 of 300 are in their twenties, with no confound control.
- Anything comparing absolute error rates across the three baselines. The wav2vec2 CTC output differs in orthography and spacing and its training domain is read speech, so only the within-model dialect-versus-plain contrast is comparable.
- Whisper is worse or better than Korean-specialized ASR systems.
- Any adaptation/fine-tuning method solves the problem.
- The pilot is speaker-independent gold evidence.

## What Has Been Done

Data and preparation:

- AI-Hub 119 validation labels were downloaded and inspected.
- AI-Hub 119 validation source audio was downloaded and zip-validated.
- 843 validation WAV files matched 843 validation label JSON stems.
- A 50-row balanced pilot subset was extracted: 25 Busan and 25 non-Busan Gyeongsang.
- 50 utterance-level pilot clips were cut; total clip duration is 4.58 minutes.
- Weak semantic annotations remain unreviewed; no weak label has been promoted to gold.

ASR baseline:

- `../japko/whisper_proto` was found and reused.
- `faster-whisper 1.2.1` is installed there.
- `faster-whisper` `medium` model was cached locally; cache size is about 1.4 GB.
- `Systran/faster-whisper-large-v3` was then cached locally as the second baseline.
- 50 pilot clips were transcribed with `faster-whisper:medium` and again with `faster-whisper:large-v3`, `compute_type=int8`.
- ASR output rows: 50 per model; missing outputs: 0. `large-v3` took 292 seconds of ASR time for the 50 clips.

Evaluation:

- Dialect attribution probe built 66 dialect-marked units and 471 non-dialect units.
- Dialect unit error rate: 45.5%.
- Non-dialect unit error rate: 17.2%.
- Error-rate ratio: 2.64x.
- Odds ratio: 4.01, 95% CI 2.34-6.89.
- Approximate two-proportion p-value: 1.10e-07.

Text-only semantic audit:

- Automatic `missing_or_substituted` dialect units: 30 of 66.
- Meaning-preserved or acceptable normalization: 50 of 66.
- Low-impact discourse/hedge loss: 7 of 66.
- Potentially harmful semantic shift candidates: 9 of 66.

Human/audio review packet:

- 16 units requiring audio confirmation were extracted into `aihub_119_dialect_audio_review`.
- Packet spans 14 distinct utterances, 9 Busan and 7 non-Busan Gyeongsang units, 16 of 16 clips present.
- Reviewer decisions are not filled yet; no unit has been confirmed harmful by audio.

Round 2, all automatic and requiring no human review:

- Utterance-clustered significance tests were added; the dialect gap survives all three of cluster bootstrap, within-utterance permutation, and utterance-stratified Mantel-Haenszel.
- Design effect versus the old unit-independent test is only 1.16 (`medium`) and 1.38 (`large-v3`), so the original p-value was overconfident but not wrong in direction.
- Utterance composition alone accounts for 14% of the raw gap; the dialect-attributable excess is 0.243 for `medium` and 0.216 for `large-v3`.
- `large-v3` was added as a second baseline and reduced but did not remove the gap.
- The AICC critical-span metric was rebuilt after a substring-based first pass produced three artifacts: numeral-notation false losses, single-syllable false preservations, and phantom labels.
- After repair, critical-span strict loss is 0.103 [0.019, 0.203] for `medium` and 0.069 [0.000, 0.161] for `large-v3`, over 58 scorable spans.
- Amount spans, previously reported at 91.7% loss, are at 0 loss once numerals are compared by value.

Metric correction, applied after round 8:

- The cue-preservation test now accepts the dialect surface, the standard form of the same eojeol, or the bare cue morpheme. Previously it tested only the canonical cue string, which carries the standard spelling.
- That bias hit the dialect arm alone: 40 of 243 dialect-arm cases on the confirmation split were perfectly transcribed dialect forms scored as losses.
- Corrected gaps are +0.213, +0.175, +0.287 on the confirmation split and +0.159, +0.159, +0.228 on the negation split. All still exclude zero; round 6's +0.396 does not stand.
- Corrected substitution shares are 0.50 to 0.82, so round 8's "all six combinations" becomes five plus one tie.
- Rounds 4 and 5 are unaffected: round 4 already accepted both dialect and standard surfaces, and round 5 does not use cue-position judgements.

Round 8, also fully automatic:

- Absent cues were split into substitution and deletion by anchoring on the cue's surviving neighbour eojeols; unalignable cases are reported as `context_lost` rather than forced.
- Substitution outnumbers deletion in all six model-by-category combinations, 0.63 to 0.89 of resolved cases.
- Resolution is poor: about two thirds of absent cues are `context_lost`, and for wav2vec2 it is 85 percent.
- Replacement surfaces almost never repeat, so no correction dictionary emerges. Across all six combinations only four surfaces appeared more than once.

Round 7, also fully automatic:

- Cue outcomes were split into dialect surface kept, normalised to standard, and absent, by resolving each cue's eojeol pair from the labels.
- For Whisper, 35 to 40 percent of dialect-marked cues are normalised to the standard form, so roughly half the round 6 gap was never AICC damage.
- Genuine damage gaps: +0.194 (`medium`), +0.148 (`large-v3`), +0.204 (wav2vec2), all excluding zero.
- `large-v3` normalises more and drops less than `medium`, the first model-quality difference to appear anywhere in this project.
- A negation-only split of 185 pairs, up from 30, reproduces the effect in all three baselines and removes the confirmation-only caveat.
- Cohort decomposition at cue level keeps the Busan null across six tests: three models by two splits, all crossing zero with mixed signs.

Round 6, also fully automatic:

- The full label set was scanned for utterances where a dialect-marked eojeol itself carries an AICC cue: 829 such cue-bearing dialect eojeols against 56018 non-dialect cue occurrences.
- 250 within-speaker, within-category pairs were built across 250 speakers and 213 recordings, 500 clips, 42.32 minutes.
- Cue loss when the cue word is dialect-marked versus not: 0.488 vs 0.092 (`medium`), 0.436 vs 0.092 (`large-v3`), 0.872 vs 0.524 (wav2vec2).
- Discordant pairs are heavily one-sided: 108 to 9, 96 to 10, 102 to 15.
- Placebos are null in all three models, so the pairing holds.
- The cue inventory is confirmation 220 and negation 30; amount and intent cues effectively never land on a dialect-marked eojeol in this corpus.

Round 5, also fully automatic:

- 63 within-speaker control pairs were built: each pair is one speaker in one recording, a dialect-bearing utterance against a length-matched dialect-free utterance, both carrying critical spans.
- Length matching is near-exact: 10.71 versus 10.57 mean eojeols, mean difference -0.14.
- Critical-span loss does not differ between arms in any of the three baselines; permutation p 0.55, 0.70, 0.81 and McNemar p 0.77, 0.77, 0.85.
- The placebo, non-dialect unit error, also shows no arm difference, so the matching holds.
- Conclusion: dialect fragility is local to dialect-marked tokens and does not propagate to AICC critical spans elsewhere in the utterance, at this resolution.

Round 4, also fully automatic:

- A 300-utterance speaker-disjoint holdout was built: 300 speakers, 159 recordings, none shared with the pilot's 46, 352 dialect units and 2525 non-dialect units, 26.47 minutes.
- All three baselines were run on it: wav2vec2 118 s, `medium` 840 s, `large-v3` 1544 s, 300 rows each, no empty hypotheses.
- The dialect gap grew on the holdout for every model, and utterance composition explains only 3-8% of it versus 14% in the pilot.
- The Busan-versus-other null tightened to intervals of width 0.13-0.22 and still contains zero in all three models.
- Critical-span re-mining on the holdout produced 93 spans with zero phantom labels, confirming the boundary rules hold on unseen data.
- Holdout critical-span strict loss: 0.108 `medium`, 0.118 `large-v3`, 0.398 wav2vec2.

Round 3, also fully automatic:

- The critical-span mining rule was replaced with eojeol-boundary rules; phantom labels drop from 16 of 74 to 1 of 56.
- Re-mined labels reproduce the audit's numbers, so the upstream fix and the downstream filter cross-validate each other.
- `kresnik/wav2vec2-large-xlsr-korean` was added as a third, non-Whisper, Korean-trained baseline. 50 clips took 27.4 seconds.
- The dialect gap reproduces there: difference 0.207 [0.088, 0.320], ratio 1.34x, MH odds ratio 2.53 [1.30, 4.92], permutation p 1.65e-03.
- On re-mined labels, critical-span strict loss is 0.091 for `medium`, 0.073 for `large-v3`, 0.509 for wav2vec2 over 55 scorable spans.
- The wav2vec2 amount loss of 9 of 10 is largely an output-format effect, not semantic damage; its CTC output does not spell numerals in a parseable form.

## Key Artifacts

Run directory:

- `research/experiments/runs/aihub_119_dialect_attribution_probe/`

Primary reports:

- [Metric correction](research/experiments/runs/aihub_119_metric_correction/README.md)
- [Pilot round 8 report](research/experiments/runs/aihub_119_pilot_round8/README.md)
- [Cue substitution, confirmation split](research/experiments/runs/aihub_119_cue_substitution/README.md)
- [Cue substitution, negation split](research/experiments/runs/aihub_119_negation_substitution/README.md)
- [Pilot round 7 report](research/experiments/runs/aihub_119_pilot_round7/README.md)
- [Cue error types](research/experiments/runs/aihub_119_cue_error_types/README.md)
- [Negation cue split](research/experiments/runs/aihub_119_negation_cue_split/README.md)
- [Negation cue comparison](research/experiments/runs/aihub_119_negation_cue_comparison/README.md)
- [Negation error types](research/experiments/runs/aihub_119_negation_error_types/README.md)
- [Pilot round 6 report](research/experiments/runs/aihub_119_pilot_round6/README.md)
- [Cue-bearing dialect split](research/experiments/runs/aihub_119_cue_bearing_split/README.md)
- [Cue-bearing comparison](research/experiments/runs/aihub_119_cue_bearing_comparison/README.md)
- [Pilot round 5 report](research/experiments/runs/aihub_119_pilot_round5/README.md)
- [Dialect control pairs](research/experiments/runs/aihub_119_dialect_control_pairs/README.md)
- [Dialect control comparison](research/experiments/runs/aihub_119_dialect_control_comparison/README.md)
- [Pilot round 4 report](research/experiments/runs/aihub_119_pilot_round4/README.md)
- [Speaker-independent holdout split](research/experiments/runs/aihub_119_speaker_independent_split/README.md)
- [Holdout significance tests](research/experiments/runs/aihub_119_holdout_significance/README.md)
- [Holdout critical spans](research/experiments/runs/aihub_119_holdout_critical_spans/README.md)
- [Pilot round 3 report](research/experiments/runs/aihub_119_pilot_round3/README.md)
- [Pilot round 2 report](research/experiments/runs/aihub_119_pilot_round2/README.md)
- [pilot_conclusion_report.md](research/experiments/runs/aihub_119_dialect_attribution_probe/pilot_conclusion_report.md)
- [text_audit_report.md](research/experiments/runs/aihub_119_dialect_attribution_probe/text_audit_report.md)
- [Clustered significance tests](research/experiments/runs/aihub_119_dialect_significance/README.md)
- [Critical span preservation, medium](research/experiments/runs/aihub_119_critical_span_preservation/README.md)
- [Critical span preservation, large-v3](research/experiments/runs/aihub_119_critical_span_preservation_large_v3/README.md)
- [Critical span re-mining](research/experiments/runs/aihub_119_critical_span_remine/README.md)
- [Re-mined span preservation, medium](research/experiments/runs/aihub_119_critical_span_remined_medium/README.md)
- [Re-mined span preservation, large-v3](research/experiments/runs/aihub_119_critical_span_remined_large_v3/README.md)
- [Re-mined span preservation, wav2vec2](research/experiments/runs/aihub_119_critical_span_remined_wav2vec2/README.md)

Plots:

- [Dialect vs plain error rate](research/experiments/runs/aihub_119_dialect_attribution_probe/figures/01_dialect_vs_plain_error_rate.png)
- [Dialect outcome split](research/experiments/runs/aihub_119_dialect_attribution_probe/figures/02_dialect_outcome_split.png)
- [Category outcome breakdown](research/experiments/runs/aihub_119_dialect_attribution_probe/figures/03_category_outcome_breakdown.png)
- [Cohort error rates](research/experiments/runs/aihub_119_dialect_attribution_probe/figures/04_cohort_error_rates.png)

Machine-readable summaries:

- `research/experiments/runs/aihub_119_dialect_attribution_probe/summary.json`
- `research/experiments/runs/aihub_119_dialect_attribution_probe/dialect_asr_error_analysis_summary.json`
- `research/experiments/runs/aihub_119_dialect_attribution_probe/dialect_asr_text_audit_summary.json`
- `research/experiments/runs/aihub_119_dialect_audio_review/summary.json`
- `research/experiments/runs/aihub_119_dialect_significance/summary.json`
- `research/experiments/runs/aihub_119_critical_span_preservation/summary.json`
- `research/experiments/runs/aihub_119_critical_span_preservation_large_v3/summary.json`
- `research/experiments/runs/aihub_119_critical_span_remine/summary.json`
- `research/experiments/runs/aihub_119_critical_span_remined_medium/summary.json`
- `research/experiments/runs/aihub_119_critical_span_remined_large_v3/summary.json`
- `research/experiments/runs/aihub_119_critical_span_remined_wav2vec2/summary.json`
- `research/experiments/runs/aihub_119_speaker_independent_split/summary.json`
- `research/experiments/runs/aihub_119_holdout_significance/summary.json`
- `research/experiments/runs/aihub_119_holdout_critical_spans/summary.json`
- `research/experiments/runs/aihub_119_dialect_control_pairs/summary.json`
- `research/experiments/runs/aihub_119_dialect_control_comparison/summary.json`
- `research/experiments/runs/aihub_119_cue_bearing_split/summary.json`
- `research/experiments/runs/aihub_119_cue_bearing_comparison/summary.json`
- `research/experiments/runs/aihub_119_cue_error_types/summary.json`
- `research/experiments/runs/aihub_119_negation_cue_split/summary.json`
- `research/experiments/runs/aihub_119_negation_cue_comparison/summary.json`
- `research/experiments/runs/aihub_119_negation_error_types/summary.json`
- `research/experiments/runs/aihub_119_cue_substitution/summary.json`
- `research/experiments/runs/aihub_119_negation_substitution/summary.json`
- `research/experiments/runs/aihub_119_next_actions/summary.json`

Local-only restricted files:

- `research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl`
- `research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_medium.local.jsonl`
- `research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_large_v3.local.jsonl`
- `research/experiments/runs/aihub_119_dialect_attribution_probe/wav2vec2_korean.local.jsonl`
- `research/experiments/runs/aihub_119_critical_span_remine/remined_annotations.local.jsonl`
- `research/experiments/runs/aihub_119_speaker_independent_split/asr_input_manifest.local.jsonl`
- `research/experiments/runs/aihub_119_speaker_independent_split/faster_whisper_medium.local.jsonl`
- `research/experiments/runs/aihub_119_speaker_independent_split/faster_whisper_large_v3.local.jsonl`
- `research/experiments/runs/aihub_119_speaker_independent_split/wav2vec2_korean.local.jsonl`
- `research/experiments/runs/aihub_119_holdout_critical_spans/remined_annotations.local.jsonl`
- `research/experiments/runs/aihub_119_dialect_control_pairs/asr_input_manifest.local.jsonl`
- `research/experiments/runs/aihub_119_dialect_control_pairs/control_annotations.local.jsonl`
- `data/interim/aihub_119_holdout_clips/`
- `research/experiments/runs/aihub_119_cue_bearing_split/asr_input_manifest.local.jsonl`
- `research/experiments/runs/aihub_119_cue_bearing_split/cue_annotations.local.jsonl`
- `data/interim/aihub_119_control_clips/`
- `research/experiments/runs/aihub_119_negation_cue_split/asr_input_manifest.local.jsonl`
- `research/experiments/runs/aihub_119_negation_cue_split/cue_annotations.local.jsonl`
- `research/experiments/runs/aihub_119_cue_substitution/cue_substitution_cases.local.jsonl`
- `research/experiments/runs/aihub_119_negation_substitution/cue_substitution_cases.local.jsonl`
- `data/interim/aihub_119_cue_clips/`
- `research/experiments/runs/aihub_119_critical_span_preservation/critical_span_cases.local.jsonl`
- `research/experiments/runs/aihub_119_critical_span_preservation_large_v3/critical_span_cases.local.jsonl`
- `research/experiments/runs/aihub_119_dialect_attribution_probe/dialect_asr_error_cases.local.jsonl`
- `research/experiments/runs/aihub_119_dialect_attribution_probe/dialect_asr_text_audit.local.jsonl`
- `research/experiments/runs/aihub_119_pilot_review_packet/pilot_reviewer_sheet.local.tsv`
- `research/experiments/runs/aihub_119_dialect_audio_review/dialect_audio_review_sheet.local.tsv`
- `research/experiments/runs/aihub_119_dialect_audio_review/dialect_audio_review_queue.local.jsonl`
- `data/interim/aihub_119_pilot_clips/`

These local-only files may contain transcript text or restricted dataset paths. Do not quote raw transcript content in shareable reports.

## Current Best Problem Definition

The problem is not simply “Busan dialect STT is bad.”

The sharper research problem is:

> Korean Gyeongsang/Busan dialect-marked speech causes surface instability in general ASR, but only some of those instabilities create harmful semantic shifts for AICC text analytics. The research target is to measure and reduce semantic-critical dialect ASR failures beyond WER/CER.

This framing is stronger because it connects:

- Korean dialect robustness;
- telephone/contact-center deployment conditions;
- semantic-critical AICC tasks;
- error taxonomy beyond WER/CER;
- downstream intent/slot/TA failure risk.

## Next Action

The 16-row human/audio review packet has been built. It is generated, not reviewed.

Packet location:

- `research/experiments/runs/aihub_119_dialect_audio_review/`

Packet contents:

- `dialect_audio_review_sheet.local.tsv`: 16 reviewer rows, restricted, git-ignored.
- `dialect_audio_review_queue.local.jsonl`: same rows as JSONL, restricted, git-ignored.
- [dialect_audio_review_manifest.jsonl](research/experiments/runs/aihub_119_dialect_audio_review/dialect_audio_review_manifest.jsonl): shareable metadata only.
- [summary.json](research/experiments/runs/aihub_119_dialect_audio_review/summary.json) and [README.md](research/experiments/runs/aihub_119_dialect_audio_review/README.md): shareable counts and reviewer protocol.

Packet composition: 9 `potentially_harmful_semantic_shift` + 7 `low_impact_discourse_or_hedge_loss` units, drawn from 14 distinct utterances, 9 Busan and 7 non-Busan Gyeongsang, all 16 clips present.

Do this next:

1. Have a human reviewer play each `clip_path` and fill `reviewer_decision` with `harmful`, `acceptable`, `artifact`, or `unclear`, plus `reviewer_confidence` and `reviewer_notes`.
2. Leave undecidable rows blank rather than guessing; blank rows stay `unreviewed`.
3. Summarize confirmed harmful dialect ASR cases from the completed sheet.
4. Decide whether to freeze pilot semantic annotations.

Regenerate the packet with:

```bash
uv run scripts/build_dialect_audio_review_packet.py \
  research/experiments/runs/aihub_119_dialect_attribution_probe/dialect_asr_text_audit.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_dialect_audio_review
```

Regeneration overwrites the sheet, so do not rerun it after a reviewer has started filling rows.

Everything reachable without a human has been done through round 3: `large-v3` and a Korean wav2vec2 baseline are run, clustered significance testing is in place, the AICC-critical field linkage exists, and the mining rule that produced the phantom labels is fixed.

## Medium-Term Next Leads

1. Freeze accepted pilot semantic annotations after the 16-row audio review.
2. Raise the alignment resolution rate with forced alignment, so the substitution finding rests on more than a third of cases.
3. Judge whether a substituting word actually flips the business meaning. Round 8 only shows that the cue is not there.
4. Explain why normalisation rates differ by model. `large-v3` absorbs dialect cues into standard forms better than `medium`; whether that is training data or decoding is unknown.
5. Mine a second holdout balanced across AICC categories. The current holdout has 48 negation and 42 confirmation spans but zero amount spans, because it was sampled on dialect eojeols.
4. Stratify or balance the holdout by speaker sex and age band.
5. Have a human confirm that re-mined cue eojeols actually carry business events. The boundary rule proves the label names a real eojeol, not that it means anything.
6. Decide the AICC-condition story. AI-Hub 119 is spontaneous conversation, not contact-centre speech, so either a contact-centre-like source is needed or the telephone condition must be simulated and stated as such.

## Open Risks

- The 50-utterance pilot is not a final scientific sample.
- Text-only audit is not gold; audio review is required.
- Busan-specific effect is not established; current evidence supports broader Gyeongsang dialect fragility, and the cohort gap shrinks to 0.006 at `large-v3`.
- Many dialect mismatches are harmless normalizations, so a WER-only paper would be weak.
- The critical-span label set is weak and partly artificial. The phantom-label filter removes labels that name no real eojeol, but it cannot tell whether a surviving eojeol carried business meaning.
- The dialect-to-AICC-damage link is now measured twice with opposite outcomes, and the resolution is that the effect is local. Round 5's utterance-level null stands; round 6's cue-level positive stands. Do not quote either alone.
- Cue figures printed in rounds 6, 7, and 8 came from a biased preservation rule and are superseded. The mined cue carries the standard spelling, so a perfectly transcribed dialect form was scored as a loss, and that bias fell only on the dialect arm. Quote the metric correction document instead.
- The thesis has to be narrow to be true. The AICC angle cannot rest on whole-utterance degradation, which round 5 rules out. It rests on the dialect tokens themselves and on the cue positions they land on.
- The round 5 null is underpowered against small effects, roughly below 0.10.
- Absolute error rates are not comparable across the three baselines; the wav2vec2 CTC output differs in orthography and training domain. Only within-model contrasts are.
- Dataset licensing and raw transcript handling remain restricted; keep `.local.*` files out of shareable artifacts.

## Reproduction Commands

Run ASR using the cached `faster-whisper` models. The runner loads with `local_files_only=True`, so cache the model first if it is missing:

```bash
../japko/whisper_proto/.venv/bin/python -c "
from huggingface_hub import snapshot_download
print(snapshot_download('Systran/faster-whisper-large-v3'))
"

../japko/whisper_proto/.venv/bin/python scripts/run_faster_whisper_pilot_asr.py \
  research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_medium.local.jsonl \
  medium
```

Run the clustered significance tests and the AICC critical-span audit:

```bash
uv run scripts/run_dialect_significance_tests.py \
  research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_medium.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_large_v3.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_dialect_significance

uv run scripts/analyze_critical_span_preservation.py \
  research/experiments/runs/aihub_119_pilot_review_packet/pilot_candidate_annotations.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_medium.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_critical_span_preservation
```

Run dialect attribution:

```bash
uv run scripts/run_dialect_attribution_probe.py \
  research/experiments/runs/aihub_119_pilot_review_packet/pilot_review_manifest.jsonl \
  --output-dir research/experiments/runs/aihub_119_dialect_attribution_probe \
  --asr research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_medium.local.jsonl
```

Run text audit analysis summary generation:

```bash
uv run scripts/analyze_dialect_asr_errors.py \
  research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl \
  research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_medium.local.jsonl \
  --output-dir research/experiments/runs/aihub_119_dialect_attribution_probe
```

## Agent Output Reminder

When a new agent writes a result, follow the repository rule:

```text
Verdict:
Evidence:
Claims:
Open Risks:
Next Leads:
```
