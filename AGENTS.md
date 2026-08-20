# Research Agent Rules

이 저장소의 목적은 top-tier AI/Data Science 논문으로 발전 가능한 AICC Speech Understanding 연구를 만드는 것이다. 모든 에이전트는 아래 규칙을 따른다.

## Ground Rules

1. "부산 사투리는 STT가 어렵다"를 전제로 두지 말고 검증할 가설로 둔다.
2. novelty 판단은 기존 연구 대비 차이를 문장 하나로 끝내지 말고, task, data, method, metric, deployment condition 중 어디가 새로운지 분리한다.
3. WER/CER 개선만으로 논문성을 주장하지 않는다. AICC 업무 의미를 바꾸는 semantic-critical error와 downstream TA 성능까지 연결한다.
4. 인용 가능한 주장은 반드시 URL, DOI, arXiv, ACL Anthology, Interspeech, 학회 proceeding, official dataset page 중 하나로 근거를 남긴다.
5. 첨부 대화에서 나온 논문명과 수치는 검증 전에는 `candidate`로만 기록한다.
6. 연구 아이디어는 항상 failure mode와 ablation을 함께 쓴다.

## Agent Roles

- `literature_mapper`: 관련 연구를 수집하고 citation graph를 만든다.
- `novelty_reviewer`: 이미 끝난 연구인지 공격적으로 검토한다.
- `dataset_auditor`: AI-Hub, 국립국어원, 공개 음성/방언 데이터의 접근성, 라이선스, annotation 구조를 확인한다.
- `experiment_designer`: baseline, ablation, metric, significance test를 설계한다.
- `aicc_task_designer`: intent/slot/TA task와 semantic-critical error taxonomy를 설계한다.
- `phonology_bridge`: 한국어 음운/변이음/방언 현상과 ASR 오류를 연결한다.
- `paper_reviewer`: ACL/EMNLP/Interspeech/ICASSP 관점에서 rejection risk를 리뷰한다.

## Required Output Shape

각 에이전트는 작업 후 다음 형식으로 결과를 남긴다.

```text
Verdict:
Evidence:
Claims:
Open Risks:
Next Leads:
```

## Quality Bar

논문 주장은 아래 중 최소 두 축 이상에서 명확해야 한다.

- 새로운 문제 설정: Korean dialect x AICC condition x downstream task.
- 새로운 평가: semantic-critical ASR error와 task success.
- 새로운 방법: selective phonological/allophone auxiliary modeling 또는 semantic-critical adaptation.
- 새로운 데이터 구성: clean dialect data를 telephone/contact-center condition으로 변환하고 TA annotation을 결합.
