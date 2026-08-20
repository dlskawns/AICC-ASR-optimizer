# Phase 1 Baseline Protocol

## Objective

Establish whether Busan/Gyeongsang dialect plus contact-center acoustic shift causes semantic-critical ASR failures.

## Precondition: Dialect Attribution

Before interpreting AICC semantic-critical errors, run a dialect attribution probe:

- dialect-marked eojeol error rate vs non-dialect eojeol error rate;
- Busan vs non-Busan Gyeongsang cohort comparison;
- surface dialect preservation vs meaning-preserving standard normalization;
- category-level concentration by lexical replacement, ending/particle variant, vowel shift, coda shift, and prefix/stem variant.

If dialect-marked units are not measurably harder or different after ASR, the paper should pivot from "Busan dialect ASR problem" to "semantic-critical AICC ASR evaluation".

## Minimum Conditions

| Condition | Source |
| --- | --- |
| Standard Korean clean | KsponSpeech or NIKL control, if available |
| Gyeongsang dialect clean | AI-Hub dataset 119 |
| Gyeongsang dialect telephone-bandlimited | derived from AI-Hub dataset 119 if license allows |
| Call/contact-center Korean | ClovaCall |

## Baseline Models

1. Whisper large-v3 or current Whisper-family baseline.
2. Korean Conformer/FastConformer baseline if available.
3. AI-Hub Conformer reported score as reference, not as directly comparable unless split/normalization matches.

## Evaluation Metrics

ASR:

- CER.
- WER.
- Dialect-token error rate.

Semantic-critical:

- Negation Error Rate.
- Number/Date Error Rate.
- Entity Error Rate.
- Intent-Flip Error Rate.

Downstream:

- Intent Accuracy.
- Slot F1.
- Task Success Rate.
- Clarification Precision/Recall if N-best/confidence is available.

## First Table

| Model | Data | Condition | CER | WER | Negation Err | Number/Date Err | Entity Err | Intent Acc | Slot F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Whisper | Gyeongsang | clean | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Whisper | Gyeongsang | telephone | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Conformer | Gyeongsang | clean | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Conformer | Gyeongsang | telephone | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

## Required Ablations

- Clean vs telephone-bandlimited.
- Standard Korean vs Gyeongsang.
- 1-best transcript vs N-best/confidence if available.
- Dialect-preserving transcript vs standard-form normalization.

## Stop Condition

Phase 1 is complete when the project has a speaker-independent split and at least one model result table that includes WER/CER plus semantic-critical metrics.
