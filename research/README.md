# Research Workspace

이 폴더는 논문 아이디어, 선행연구, 실험 설계, 평가 기준을 관리한다.

현재 세션 handoff는 [../HANDOFF.md](../HANDOFF.md)를 먼저 본다.

## Workflow

1. `wiki/01-problem-framing.md`에서 연구 질문과 claim을 갱신한다.
2. `papers/related-work.yaml`에 선행연구를 `candidate`, `verified`, `refuted`, `needs_reading` 상태로 기록한다.
3. `wiki/02-agent-harness.md`에 어떤 agent가 어떤 질문을 담당하는지 남긴다.
4. `wiki/03-evaluation-rubric.md`으로 연구 적절성, novelty, 실험 타당성을 점검한다.
5. 실험을 시작하면 `experiments/` 아래에 dataset card, baseline protocol, metric script를 추가한다.
