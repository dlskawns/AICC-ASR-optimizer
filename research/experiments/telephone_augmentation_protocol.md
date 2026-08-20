# Telephone Augmentation Protocol

## Purpose

AI-Hub Gyeongsang dialect data is clean. AICC speech is not. This protocol defines a conservative telephone/contact-center stress condition.

## Legal First

Do not transform or redistribute restricted audio unless the dataset license allows local derivative processing for research. For ClovaCall, the README license restricts modification/editing/reproduction, so use caution and clarify permission before generating modified ClovaCall audio.

## Candidate Transformations

Apply one at a time before combining:

- Bandlimit to 300-3400 Hz.
- Resample to 8 kHz.
- Add call-like background noise.
- Add packet-loss/dropout simulation.
- Add overlapped speech only if a clear policy exists.
- Speed perturbation for fast speech stress.

## Reporting Rule

Every transformed condition must report:

- transform command/config.
- random seed.
- source file count.
- duration after transform.
- whether the transform was used for training, evaluation, or both.

## Validity Warning

Synthetic telephone degradation is not the same as a real AICC recording. The paper can claim telephone stress-test robustness, but not real call-center deployment robustness unless evaluated on real call/contact-center data.
