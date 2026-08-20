# Busan-AICC Research Lab

이 디렉토리는 한국어 AICC 환경에서 방언, 통화 음질, downstream 상담 태스크가 얽혀 발생하는 Speech Understanding 실패를 연구하기 위한 에이전트 기반 랩실이다.

## Working Thesis

단순한 "부산 사투리 STT 파인튜닝"은 novelty가 약하다. 더 강한 논문 축은 다음 조합이다.

> Korean dialect robustness x telephone/contact-center domain shift x semantic-critical downstream TA robustness

핵심 가설은 "방언 ASR의 모든 오류가 동일하게 중요하지 않으며, 부정/금액/날짜/상품명/의도처럼 상담 업무 결과를 바꾸는 semantic-critical 오류를 줄이는 방향으로 ASR과 SLU를 평가하고 학습해야 한다"이다.

## First Research Target

임시 프로젝트명:

**Busan-AICC: Semantic-Critical Dialect Robustness for Korean Contact-Center Speech Understanding**

초기 범위:

1. 부산/경상도 방언과 표준어의 ASR 오류 차이를 검증한다.
2. clean dialect speech에서 telephone/AICC condition으로 이동할 때 어떤 오류가 증가하는지 분석한다.
3. WER/CER뿐 아니라 Intent Accuracy, Slot F1, Negation Error, Number/Date Error, Entity Error, Task Success를 함께 평가한다.
4. Selective allophone/phonological auxiliary modeling, dialect-aware adaptation, N-best/confidence-aware reranking 중 novelty가 가장 강한 방법을 선별한다.

## Directory Map

- [HANDOFF.md](HANDOFF.md): 새 세션이 가장 먼저 읽어야 할 현재 상태와 다음 작업 요약.
- [AGENTS.md](AGENTS.md): 이 랩에서 에이전트가 따라야 할 운영 규칙.
- [research/wiki/00-lab-index.md](research/wiki/00-lab-index.md): LLM wiki 진입점.
- [research/wiki/01-problem-framing.md](research/wiki/01-problem-framing.md): 문제 정의와 주요 가설.
- [research/wiki/02-agent-harness.md](research/wiki/02-agent-harness.md): 연구 에이전트 하네스 설계.
- [research/wiki/03-evaluation-rubric.md](research/wiki/03-evaluation-rubric.md): 논문성, novelty, 실험 타당성 평가 루브릭.
- [research/papers/related-work.yaml](research/papers/related-work.yaml): 선행연구 아카이브.
- [.omo/ulw-research/](.omo/ulw-research): 이번 조사 세션의 증거/claim journal.

## Current Status

문제정의 pilot은 완료됐다. 현재 결론과 다음 작업은 [HANDOFF.md](HANDOFF.md)를 기준으로 본다. 첨부 논의에서 나온 선행연구명과 주장은 웹 검증 전까지 `candidate` 상태로 취급한다.
