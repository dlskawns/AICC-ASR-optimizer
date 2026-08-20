# Metadata Inspection Protocol

Run this after AI-Hub or ClovaCall data is approved and downloaded.

## Goals

1. Verify city/region availability, especially Busan.
2. Verify speaker demographics.
3. Verify transcript fields.
4. Verify whether train/dev/test splits exist.
5. Build local-only manifests without committing restricted audio.

## Expected Commands

From the repo root:

```bash
find data/raw/aihub_gyeongsang_119 -name '*.json' | head
find data/raw/aihub_senior_gangwon_gyeongsang_71517 -name '*.json' | head
find data/raw/clovacall -name '*.json' | head
```

Inspect keys:

```bash
jq 'keys' <sample.json>
jq '.speaker // .meta.speaker // empty' <sample.json>
jq '.utterance[0] // .utterances[0] // .[0] // empty' <sample.json>
```

Check region fields:

```bash
jq -r '.. | objects | .birthplace? // empty' data/raw/aihub_gyeongsang_119/**/*.json | sort | uniq -c | sort -nr | head -50
jq -r '.. | objects | .principal_residence? // empty' data/raw/aihub_gyeongsang_119/**/*.json | sort | uniq -c | sort -nr | head -50
jq -r '.. | objects | .current_residence? // empty' data/raw/aihub_gyeongsang_119/**/*.json | sort | uniq -c | sort -nr | head -50
```

Check dialect fields:

```bash
jq -r '.. | objects | .dialect_form? // empty' data/raw/aihub_gyeongsang_119/**/*.json | head
jq -r '.. | objects | .standard_form? // empty' data/raw/aihub_gyeongsang_119/**/*.json | head
jq -r '.. | objects | .eojeolList? // empty' data/raw/aihub_gyeongsang_119/**/*.json | head
```

## Pass Criteria

- At least one region field can distinguish Busan from broader Gyeongsang, or the limitation is documented.
- `dialect_form` and `standard_form` are available for most utterances.
- Audio paths can be paired with utterance timestamps.
- License terms allow local training/evaluation and derived metric reporting.

## Blockers

- No city-level metadata.
- No local permission to perform telephone augmentation.
- Dataset split is unavailable and speaker-independent splitting cannot be guaranteed.
