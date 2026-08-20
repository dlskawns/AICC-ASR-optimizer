# Problem Framing

## 사용자 논의에서 도출한 핵심 판단

첨부 논의의 강한 버전은 다음과 같다.

> Robust Speech AI / Speech Understanding for AICC: 방언, 잡음, 통화환경에서도 STT -> TA -> Agent가 안정적으로 동작하게 만드는 연구.

단순히 부산 사투리를 표준어로 rewriting하는 접근은 ASR 첫 단계에서 의미 정보가 소실되면 복구할 수 없다. 따라서 첫 연구 문제는 **방언 robust ASR 및 오류 전파 분석**이어야 한다.

## Strong Research Framing

**Dialect-Robust Speech Understanding for Korean Contact Centers**

Pipeline:

```text
Audio
  -> dialect-robust ASR
  -> dialect-preserving transcript
  -> semantic normalization
  -> intent / slot / TA
  -> task success or clarification
```

## Why This Is More Research-Worthy

약한 주제:

```text
Busan dialect Whisper fine-tuning improves WER.
```

강한 주제:

```text
In Korean contact-center speech, dialect and telephone-domain shift create semantic-critical ASR errors.
Optimizing only WER misses errors that change business outcomes.
Selective phonological/dialect-aware modeling and uncertainty-aware downstream reasoning reduce task-level failure.
```

## Hypotheses

| ID | Hypothesis | Current status |
| --- | --- | --- |
| H1 | 부산/경상도 방언은 표준어보다 ASR 오류가 더 많다. | risky; must verify, not assume |
| H2 | clean dialect data 성능은 telephone/AICC condition에서 유지되지 않는다. | plausible; needs evidence |
| H3 | WER가 비슷해도 negation, number, entity 오류율은 크게 다를 수 있다. | plausible; central claim |
| H4 | ASR 오류는 downstream intent/slot/TA 성능으로 전파된다. | supported by known SLU/QA direction, needs citations |
| H5 | selective allophone/phonological auxiliary loss가 방언 ASR 오류를 줄일 수 있다. | method candidate |
| H6 | N-best/confidence-aware reranking 또는 clarification policy가 AICC task success를 높일 수 있다. | method/system candidate |

## Rejection Risks

- 선행연구가 이미 accent-aware LoRA/MoE, ASR-robust SLU, N-best correction을 다루었기 때문에 단순 조합은 novelty가 약하다.
- "경상도 방언이라서 ASR이 나쁘다"는 가정은 일부 선행 결과와 충돌할 수 있다.
- AI-Hub 데이터가 실제 AICC 전화환경과 다르면 synthetic telephone/noise 변환만으로는 외적 타당성이 약할 수 있다.
- TA task annotation을 직접 만들지 않으면 downstream claim이 평가되지 않는다.

## Promising Novelty Direction

**Semantic-Critical Dialect ASR**

WER 최소화 대신 아래 오류를 별도로 정의하고 줄인다.

- Negation Error: 안, 못, 없다, 아니다, 불가, 해지 불가 등.
- Number/Date Error: 금액, 날짜, 시간, 계좌/주문 번호.
- Entity Error: 상품명, 지명, 사람명, 기관명.
- Intent-Flip Error: 문의, 취소, 해지, 변경, 불만, 결제 등 의도 반전.
- Clarification Trigger Error: low confidence나 N-best ambiguity를 보고 재확인이 필요한 상황.
