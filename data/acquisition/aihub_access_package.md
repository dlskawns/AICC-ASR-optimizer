# AI-Hub Access Package

## Dataset 1

Name: 한국어 방언 발화(경상도)

URL: https://aihub.or.kr/aidata/33981

Dataset ID: `119`

Purpose in this project:

- Clean Gyeongsang dialect ASR baseline.
- Dialect-preserving transcript vs standard-form normalization.
- Word-level dialect token analysis using `eojeolList`.
- Speaker metadata audit for Busan/Daegu/Ulsan/Gyeongbuk/Gyeongnam distribution.

## Dataset 2

Name: 중·노년층 한국어 방언 데이터(강원도, 경상도)

URL: https://www.aihub.or.kr/aihubdata/data/view.do?aihubDataSe=realm&currMenu=&dataSetSn=71517&topMenu=

Dataset ID: `71517`

Purpose in this project:

- Age/dialect robustness.
- Middle-aged/older speaker AICC stress condition.
- Cross-dataset generalization check.

## Access Steps

1. Log in to AI-Hub.
2. Open each dataset page.
3. Click download/application.
4. Use the research-purpose text in `aihub_application_statement_ko.md`.
5. Download:
   - dataset guide / 활용가이드.
   - annotation guide / 데이터 설명서.
   - sample data if available.
   - full WAV and JSON files after approval.
6. Save under:

```text
data/raw/aihub_gyeongsang_119/
data/raw/aihub_senior_gangwon_gyeongsang_71517/
```

## Terminal Download Path

AI-Hub's `aihubshell` is available locally at `.tools/aihubshell` after the access probe.

Export your API key in the terminal, not in a file:

```bash
export AIHUB_API_KEY='...'
```

Then start with labels only:

```bash
./scripts/download_aihub_pilot.sh dataset119-validation-labels
```

Current disk space is not sufficient for the 28 GB source-audio archives. Use label packages first, then free space or use an external disk before audio.

## Must Capture After Download

- File tree snapshot.
- Dataset guide PDF filename/version.
- Region/city codebook.
- Speaker metadata fields.
- Sample JSON with all keys.
- License/use declaration screenshot or PDF.
- Any restriction on transformed audio, telephone augmentation, or derived annotations.

## First Metadata Questions

- Is Busan explicitly represented in `birthplace`, `principal_residence`, or `current_residence`?
- Can speaker IDs be grouped by Busan/Daegu/Ulsan/Gyeongbuk/Gyeongnam?
- Are train/dev/test splits provided?
- Are utterances aligned to audio timestamps?
- Does `standard_form` preserve negation, number/date, and entity cues?
- Are dialect annotations reliable enough to build selective phonology/allophone labels?
