# Busan Dialect TA Error Taxonomy

Date: 2026-08-11

## Scope

This taxonomy is derived from AI-Hub 119 validation labels only. It uses `eojeolList` entries where `isDialect=true` and compares the annotated `standard` form against the dialect `eojeol` form. It is not yet an ASR result, and it should be treated as the text-side error taxonomy that future ASR outputs will be evaluated against.

No raw utterance text is stored in the generated run artifacts.

## Cohorts

- Busan cohort: `busan_strict`, `busan_residence`, and `busan_any`
- Non-Busan Gyeongsang cohort: `gyeongsang_other`

Primary paper slice should be `busan_strict`. The broader Busan cohort is useful for sensitivity analysis.

## Observed Distribution

| Category | Busan Count | Busan Share | Gyeongsang Other Count | Gyeongsang Other Share | TA Risk |
|---|---:|---:|---:|---:|---|
| `lexical_replacement` | 9,817 | 49.82% | 9,644 | 54.00% | High |
| `ending_or_particle_variant` | 4,065 | 20.63% | 3,206 | 17.95% | High |
| `vowel_shift` | 3,383 | 17.17% | 2,418 | 13.54% | Medium-High |
| `prefix_or_stem_variant` | 2,269 | 11.52% | 2,442 | 13.67% | Medium-High |
| `coda_shift` | 165 | 0.84% | 143 | 0.80% | Medium |
| `same_surface` | 6 | 0.03% | 6 | 0.03% | Audit |

Total dialect-marked eojeols:

- Busan: 19,705
- Gyeongsang other: 17,859

## Taxonomy Definitions

`lexical_replacement`

The standard and dialect forms have low surface overlap. For TA, this is the highest-risk bucket because it can change named entities, product names, complaint topics, call intents, and slot values.

`ending_or_particle_variant`

The forms share a stem-like prefix but differ in short suffix material. For TA, this can alter request type, stance, politeness, confirmation, modality, or negation-sensitive interpretation. This bucket should be prioritized for semantic-critical annotation.

`vowel_shift`

The forms have equal syllable length and mostly preserve initial/final consonant structure while changing vowel components. For TA, this is important because acoustic ASR systems can normalize or misrecognize the dialectal realization into a different standard form.

`prefix_or_stem_variant`

The forms share suffix material but differ near the beginning or stem. For TA, this can corrupt the head of a noun/verb and should be treated as medium-to-high risk until downstream intent/slot impact is measured.

`coda_shift`

The forms have equal syllable length and mostly preserve initial/vowel structure while changing final consonants. For TA, this is lower frequency here, but it is acoustically relevant and should remain in the ASR robustness set.

`same_surface`

The dialect marker is present but the surface forms are identical. This should be audited as annotation noise or a signal that dialectality is expressed outside the eojeol surface form.

## Paper-Relevant Hypotheses

1. Busan has a higher proportion of `vowel_shift` than non-Busan Gyeongsang in this validation subset: 17.17% vs 13.54%.
2. Busan has a higher proportion of `ending_or_particle_variant`: 20.63% vs 17.95%.
3. Non-Busan Gyeongsang has a higher proportion of broad `lexical_replacement`: 54.00% vs 49.82%.

These are label-side hypotheses only. They become ASR hypotheses after audio is available.

## Evaluation Use

For the next ASR experiment, each recognized utterance should be scored both globally and conditionally:

- Overall CER/WER
- CER/WER on utterances containing each taxonomy category
- Semantic-critical error rate by category
- Intent accuracy and slot F1 by category
- Busan strict vs non-Busan Gyeongsang gap

The first high-value benchmark is not "does ASR improve on Busan?" It is "which Busan dialect categories cause semantic-critical TA failure, and does the proposed method reduce those failures without hurting non-Busan Gyeongsang?"
