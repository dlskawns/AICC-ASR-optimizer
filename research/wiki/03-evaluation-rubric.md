# Evaluation Rubric

각 연구 아이디어 또는 실험 proposal은 5점 척도로 평가한다.

## 1. Problem Fit

| Score | Meaning |
| --- | --- |
| 1 | 부산 사투리 데모 수준이다. |
| 3 | 방언 ASR 문제는 다루지만 AICC relevance가 약하다. |
| 5 | AICC에서 실제 업무 실패를 만드는 speech understanding 문제를 직접 겨냥한다. |

## 2. Novelty

| Score | Meaning |
| --- | --- |
| 1 | 이미 있는 accent/dialect fine-tuning 반복이다. |
| 3 | 한국어/부산 데이터 적용은 새롭지만 방법이나 평가는 평범하다. |
| 5 | Korean dialect x telephone condition x semantic-critical downstream task 중 적어도 두 축 이상이 선행연구와 분명히 다르다. |

## 3. Experimental Validity

| Score | Meaning |
| --- | --- |
| 1 | WER/CER만 보고 끝난다. |
| 3 | 방언/잡음/전화환경 조건별 ASR 평가는 있다. |
| 5 | ASR 오류 taxonomy와 downstream TA 성능, ablation, significance까지 있다. |

## 4. Method Strength

| Score | Meaning |
| --- | --- |
| 1 | pretrained ASR fine-tuning만 한다. |
| 3 | adapter/LoRA/MoE 등 알려진 방법을 합리적으로 적용한다. |
| 5 | semantic-critical loss, selective phonological auxiliary task, uncertainty-aware reranking/clarification처럼 문제 구조를 반영한다. |

## 5. Paper Readiness

| Score | Meaning |
| --- | --- |
| 1 | 포트폴리오 프로젝트다. |
| 3 | workshop 수준의 평가 논문 가능성이 있다. |
| 5 | ACL/EMNLP/Interspeech/ICASSP main 또는 Findings급 문제 정의와 실험 설계를 갖춘다. |

## Red Flags

- "Busan dialect is hard"를 데이터 없이 주장한다.
- synthetic telephone/noise만 쓰고 실제 AICC relevance를 과장한다.
- standard transcript만 평가하고 dialect-preserving transcript, semantic normalization, downstream task를 분리하지 않는다.
- LLM rewriting으로 ASR에서 사라진 정보를 복구할 수 있다고 가정한다.
- accent/dialect LoRA를 novelty로 과장한다.

## Green Flags

- 동일 WER의 두 모델이 semantic-critical error에서 다름을 보인다.
- dialect phonology analysis가 실제 ASR 오류 taxonomy와 연결된다.
- selective allophone/phonological auxiliary task가 ablation에서 의미 있게 작동한다.
- N-best/confidence를 사용해 TA 실행 전 clarification이 필요한 상황을 검출한다.
- 데이터셋 한계를 명시하고, 실제 AICC 조건에 대한 외적 타당성 실험을 둔다.
