# Dataset Inventory

Observed at: 2026-08-11 KST

## Primary Targets

### AI-Hub 한국어 방언 발화(경상도)

- Official page: https://aihub.or.kr/aidata/33981
- Redirected dataset ID: `119`
- Publicly verified:
  - 구축년도 2020.
  - 유형: audio + text.
  - clean/quiet environment.
  - 2,000+ speakers.
  - 3,000+ hours.
  - 500k+ dialect/standard word-level pairs.
  - JSON annotations with speaker metadata, `dialect_form`, `standard_form`, `eojeolList`, and `isDialect`.
  - Conformer indicators: CER 5.28%, WER 14.68%.
- Acquisition blocker:
  - AI-Hub download requires login and application.
  - Direct unauthenticated `curl` returned HTTP 403.

### AI-Hub 중·노년층 한국어 방언 데이터(강원도, 경상도)

- Official page: https://www.aihub.or.kr/aihubdata/data/view.do?aihubDataSe=realm&currMenu=&dataSetSn=71517&topMenu=
- Publicly verified:
  - 50+ speaker focus.
  - Total 2,004.3 hours.
  - Gyeongsang subset 1,202.9 hours.
  - WAV + JSON.
  - Read, question-answer, and two-person dialogue speech types.
- Acquisition blocker:
  - AI-Hub download requires login and application.

### ClovaCall

- GitHub: https://github.com/clovaai/ClovaCall
- Paper: https://arxiv.org/abs/2004.09367
- Publicly verified from README:
  - Korean goal-oriented call/contact-center ASR corpus.
  - Restaurant reservation domain.
  - Raw data: 81,222 utterances, 125 raw hours / 67 clean hours.
  - Train: 59,662 utterances, 80 raw hours / 50 clean hours.
  - Test: 1,084 utterances, 1.66 raw hours / 0.88 clean hours.
  - JSON structure has `wav`, `text`, `speaker_id`.
- Acquisition blocker:
  - Data application form.
  - Non-commercial AI R&D only.
  - Modification/editing/reproduction of data is restricted by the license text in the README.

## Why These Three

- AI-Hub Gyeongsang gives dialect and standard-form annotation.
- AI-Hub senior dialect gives age/dialect robustness.
- ClovaCall gives a contact-center-like call corpus baseline.

The first paper should not claim a real Busan AICC corpus unless a Busan-specific held-out set is collected or city-level metadata proves Busan coverage.

## Current Local Acquisition State

- AI-Hub 119 validation labels are downloaded and validated locally.
- AI-Hub 119 validation source audio filekey `572714` is downloaded and zip-validated locally.
- Label-side mining found enough dialect-bearing candidates for negation, confirmation, amount, date/time, and intent-cue human review.
- Next audio handling should target only the frozen gold subset, not full archive extraction unless needed.
- The current audio subset request points to AI-Hub filekey `572714`, `(비식별화완료)경상도_2.zip`, 28 GB. This large-download step is now complete for validation only.
- `scripts/download_aihub_pilot.sh dataset119-validation-source-audio` refuses to run unless the target filesystem has at least 90 GB available. Use `AIHUB_TARGET_DIR` to point at a larger disk.
