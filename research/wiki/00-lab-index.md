# LLM Wiki Index

## Core Pages

- [Problem Framing](01-problem-framing.md)
- [Agent Harness](02-agent-harness.md)
- [Evaluation Rubric](03-evaluation-rubric.md)
- [Research Questions](04-research-questions.md)
- [First Related-Work Sweep](05-related-work-first-wave.md)
- [Novelty Position](06-novelty-position.md)
- [Pilot Experiment Status](07-pilot-experiment.md)
- [Busan Dialect TA Error Taxonomy](../evaluation/busan_dialect_ta_error_taxonomy.md)
- [Semantic Annotation Guideline](../evaluation/annotation_guideline.md)
- [Gold Readiness Report](../experiments/runs/aihub_119_gold_readiness/README.md)
- [Next Actions](../experiments/runs/aihub_119_next_actions/README.md)
- [Validation Audio Download](../experiments/runs/aihub_119_validation_audio_download/README.md)
- [Data Acquisition Status](../../data/acquisition/dataset_inventory.md)
- [Phase 1 Baseline Protocol](../experiments/phase1_baseline_protocol.md)
- [Related Work Archive](../papers/related-work.yaml)

## Current Thesis

부산/경상도 방언 자체가 novelty는 아니다. 연구의 핵심은 AICC 환경에서 방언 ASR 오류가 어떤 semantic-critical 정보를 잃게 만드는지 측정하고, 그 손실을 줄이는 ASR/SLU 방법을 제안하는 것이다.

## Immediate Unknowns

- 2026년 Korean Whisper dialect/coda 논문의 세부 결과와 접근성.
- SD-QA의 한국어 경상도 결과와 downstream QA 실험 설계.
- ASR-robust SLU, N-best correction, accent-aware adapter/LoRA/MoE 연구의 최신 수준.
- Selective Allophone Level Tokenization이 ASR auxiliary task로 전환될 때의 novelty와 구현 가능성.
- Label-only semantic review queue에서 실제 AICC critical span이 충분히 나오는지.
- Small audio subset을 어떤 파일키/분할로 최소 다운로드할지.
