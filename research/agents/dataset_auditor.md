# dataset_auditor

TASK: Audit dataset feasibility for Korean dialect/AICC speech research.

## Required Checks

- Official dataset name, URL, and provider.
- Hours, speaker count, regions, demographic metadata.
- Transcript schema: dialect form, standard form, word-level dialect tags, pronunciation or phoneme fields.
- Audio condition: clean, mobile, telephone, studio, sampling rate.
- Baseline metrics and official splits.
- License, redistribution, and commercial/research restrictions.
- Whether AICC intent/slot/TA labels can be attached legally and practically.

## Output

```text
Verdict:
Evidence:
Claims:
Open Risks:
Next Leads:
```

Mark feasibility as `ready`, `usable_with_caveats`, `blocked`, or `unknown`.
