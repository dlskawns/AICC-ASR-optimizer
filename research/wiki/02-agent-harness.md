# Agent Harness Design

## Purpose

이 하네스는 한 명의 LLM이 낙관적으로 논문 아이디어를 밀어붙이지 못하게 하고, 선행연구/novelty/실험/평가를 반복적으로 공격하게 만든다.

## Orchestration Loop

```text
User idea / new finding
  -> Claim extraction
  -> Literature search agents
  -> Dataset feasibility agent
  -> Novelty attack agent
  -> Experiment design agent
  -> Paper-review agent
  -> Update wiki, related-work archive, and open risks
  -> Next search/experiment lead
```

## Agents

### 1. literature_mapper

Goal: 관련 논문을 수집하고 관계도를 만든다.

Search axes:

- Korean dialect ASR.
- Korean ASR phonology, phoneme, allophone, G2P.
- Accent/dialect adaptation: adapter, LoRA, MoE, CTC/RNN-T/seq2seq.
- ASR-robust SLU: intent, slot, QA.
- N-best/lattice/confidence-aware correction.
- Contact-center ASR and task-oriented dialogue metrics.

Output:

- citation candidate.
- key claim.
- relation to Busan-AICC.
- novelty threat or support.

### 2. novelty_reviewer

Goal: "이미 있는 연구"인지 공격적으로 판정한다.

Checks:

- 같은 task가 있었는가?
- 같은 데이터 조건이 있었는가?
- 같은 method가 있었는가?
- 같은 metric이 있었는가?
- Korean/AICC/downstream 조합이 실제로 비어 있는가?

Verdict:

- `green`: novelty gap survives.
- `yellow`: framing must change.
- `red`: topic is too close to prior work.

### 3. dataset_auditor

Goal: 데이터 사용 가능성과 annotation 구조를 확인한다.

Questions:

- AI-Hub 경상도 방언 데이터의 규모, 화자, 지역, transcript schema.
- dialect_form/standard_form, 어절 단위 방언 태그, speaker metadata 존재 여부.
- 전화망 변환이 가능한 audio quality인지.
- AICC intent/slot/TA annotation을 붙일 수 있는지.
- 라이선스와 재배포 제한.

### 4. experiment_designer

Goal: 논문으로 통과 가능한 실험표를 설계한다.

Baseline families:

- Whisper zero-shot and fine-tuned.
- Korean Conformer/FastConformer or wav2vec2-style ASR.
- Dialect fine-tuning.
- Dialect-conditioned adapter/LoRA.
- Phoneme/allophone auxiliary head.
- N-best reranking or confidence-aware semantic correction.

Ablations:

- no dialect metadata.
- no telephone augmentation.
- no semantic-critical weighting.
- phoneme auxiliary vs selective allophone auxiliary.
- 1-best only vs N-best/confidence.

### 5. aicc_task_designer

Goal: downstream TA 평가 태스크를 만든다.

Metrics:

- Intent Accuracy.
- Slot F1.
- Entity Error Rate.
- Number/Date Error Rate.
- Negation Error Rate.
- Task Success Rate.
- Clarification Precision/Recall.

### 6. phonology_bridge

Goal: 한국어 음운/변이음/방언 현상을 ASR 오류와 연결한다.

Tasks:

- 부산/경상도 특유의 음운·억양·어휘·어미 현상을 분리한다.
- allophone과 dialect variation을 혼동하지 않는다.
- Selective Allophone Level Tokenization을 ASR auxiliary learning으로 전환 가능한지 검토한다.

### 7. paper_reviewer

Goal: 학회 리뷰어 관점에서 reject 사유를 선제적으로 찾는다.

Review lens:

- Problem importance.
- Novelty.
- Methodological soundness.
- Dataset validity.
- Reproducibility.
- Metric validity.
- Ethical/privacy risks for call-center speech.

## Repeat Policy

각 cycle은 다음을 남긴다.

```text
1. New citations archived.
2. Claims updated.
3. Novelty threat updated.
4. Experiments revised.
5. Open risks ranked.
```
