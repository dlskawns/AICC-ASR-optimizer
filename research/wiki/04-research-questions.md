# Research Questions

## RQ1: Difficulty Claim

**AICC 환경에서 한국어 방언은 어떤 종류의 ASR 오류를 발생시키는가?**

Subquestions:

- 부산/경상도 방언은 표준어보다 WER/CER가 실제로 높은가?
- 모델 크기나 pretraining에 따라 dialect gap이 줄어드는가?
- 음운, 어휘, 어미, 억양, 화자 연령, 속도, 중첩 발화 중 어떤 요인이 큰가?

## RQ2: Domain Shift

**Clean dialect speech에서 telephone/contact-center condition으로 이동할 때 오류가 어떻게 바뀌는가?**

Conditions:

- clean.
- telephone bandwidth.
- background noise.
- overlapped speech.
- fast speech.
- middle-aged/older speakers.
- domain terminology.

## RQ3: Semantic-Critical Error

**어떤 ASR 오류가 AICC downstream task에 치명적인가?**

Error classes:

- negation flip.
- number/date mismatch.
- named entity loss.
- intent flip.
- slot boundary error.
- dialect ending misrecognition.

## RQ4: Method

**방언에서 실제 오류를 유발하는 phonological/allophonic distinction만 선택적으로 모델링하면 ASR과 downstream TA가 개선되는가?**

Candidate method:

```text
Audio encoder
  -> transcript decoder / CTC
  -> selective allophone auxiliary head
  -> dialect/context embedding
  -> semantic-critical reranker or loss
```

## RQ5: Uncertainty-Aware TA

**1-best transcript 대신 N-best/confidence/lattice 정보를 downstream TA 또는 clarification policy에 넘기면 task success가 개선되는가?**

Example:

```text
N-best:
1. 해지한다 캤나
2. 해지 안 된다 캤나
3. 해지는 안 된다 캤나

Policy:
critical span ambiguity + low margin -> ask clarification before task execution
```
