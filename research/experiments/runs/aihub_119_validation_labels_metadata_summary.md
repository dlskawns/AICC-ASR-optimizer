# AI-Hub 119 Validation Labels Metadata Summary

Date: 2026-08-11

## Acquisition Check

- Target: AI-Hub 119 `dataset119-validation-labels`
- Local artifact: `data/raw/aihub_gyeongsang_119/014.한국어_방언_발화_데이터(경상도)/01.데이터/2.Validation/(new3)라벨링데이터/(비식별화완료)경상도_학습데이터_2.zip`
- Zip size: 34,001,449 bytes
- Integrity: `unzip -t` completed with no compressed-data errors.
- Remaining `.partN` files: none

## Structural Counts

- JSON label files: 843
- TXT files: 843
- Speaker records: 1,686
- Speaker file-pairs: 1,686
- Speaker IDs are local role IDs: `1`, `2`
- Utterances: 229,497
- Eojeol records: 1,776,854
- Dialect-marked eojeols: 37,564
- Dialect-marked eojeol rate: 0.021141

## Field Coverage

All 229,497 utterances include:

- `form`
- `dialect_form`
- `standard_form`
- `eojeolList`

This is enough to build a dialect-vs-standard lexical/semantic error evaluation set without audio yet.

## Region Signals

Top current residences:

- 부산: 733
- 대구: 376
- 울산: 262
- 경북: 163
- 경남: 72

Top principal residences:

- 부산: 695
- 대구: 346
- 울산: 269
- 경북: 235
- 경남: 104

Top birthplaces:

- 부산: 659
- 대구: 362
- 울산: 261
- 경북: 206
- 경남: 115

## Demographic Signals

Sex:

- 여성: 1,218
- 남성: 468

Age:

- 20대: 1,118
- 30대: 284
- 10대: 118
- 50대: 94
- 40대: 64
- 60대 이상: 8

## Research Implication

This validation-label subset is suitable for the first metadata and text-only dialect analysis stage. It strongly supports a Busan-heavy Gyeongsang slice, but it is not a Busan-only corpus. The next experiment should explicitly define Busan filtering by `birthplace`, `principal_residence`, and/or `current_residence`, then compare Busan against non-Busan Gyeongsang speakers before any ASR fine-tuning claims.
