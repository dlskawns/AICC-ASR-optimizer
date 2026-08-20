# First Related-Work Sweep

Observed at: 2026-08-11 KST

## Verdict

이 주제는 타당하지만, 약한 버전은 이미 선행연구에 많이 걸린다. `부산 사투리 Whisper fine-tuning`, `dialect-specific LoRA`, `ASR-robust SLU`, `N-best correction`, `Korean ASR error taxonomy`, `Korean contact-center ASR corpus`는 각각 선행연구가 존재한다.

살아남는 강한 novelty는 다음 조합이다.

```text
Korean Busan/Gyeongsang dialect
  x telephone/contact-center acoustic condition
  x semantic-critical ASR error
  x downstream AICC TA task success
  x selective phonological/allophone-aware or uncertainty-aware method
```

## Verified Dataset Findings

### AI-Hub 한국어 방언 발화(경상도)

Official page: https://aihub.or.kr/aidata/33981

Verified:

- Gyeongsang dialect everyday conversation data.
- Clean recording target.
- 2,000+ speakers and 3,000+ hours.
- 500k+ dialect/standard word-level pairs.
- JSON includes `dialect_form`, `standard_form`, and word-level `eojeolList` with `standard` and `isDialect`.
- Official performance indicators list Conformer CER 5.28% and WER 14.68%.

Implication:

- Good starting data for dialect-preserving transcript and standard-form mapping.
- Not enough by itself for AICC because it is clean, not telephone/contact-center speech.

### AI-Hub 중·노년층 한국어 방언 데이터(강원도, 경상도)

Official page: https://www.aihub.or.kr/aihubdata/data/view.do?aihubDataSe=realm&currMenu=&dataSetSn=71517&topMenu=

Verified:

- 50+ speaker dialect dataset.
- Total 2,004.3 hours.
- Gyeongsang subset 1,202.9 hours.
- WAV plus JSON.
- Includes read-aloud, question-answer, and two-person dialogue types.

Implication:

- Useful for age/dialect robustness.
- Risky if used as proxy for contemporary Busan AICC without demographic caveats.

### ClovaCall

Paper: https://arxiv.org/abs/2004.09367
Code/data: https://github.com/clovaai/ClovaCall

Verified:

- Korean goal-oriented call speech corpus for contact-center ASR.
- Restaurant reservation domain.
- More than 11,000 speakers and roughly 60k short sentence/utterance pairs.

Implication:

- Korean AICC/call ASR is not empty territory.
- Busan-AICC should combine ClovaCall-style call condition with dialect/semantic-critical evaluation, not claim Korean call ASR as new.

## Verified Prior-Work Threats

| Area | Key source | Threat | How Busan-AICC should differ |
| --- | --- | --- | --- |
| Korean dialect Whisper error analysis | Yoon, Kwon, Han 2026, Phonetics and Speech Sciences, https://www.eksss.org/archive/view_article?pid=pss-18-1-55 | Gyeongsang vs Seoul Whisper phonological error analysis already exists. | Move from complex-coda analysis to AICC semantic-critical failures and telephone domain shift. |
| Spoken dialect QA | SD-QA 2021, https://arxiv.org/abs/2109.12072 | Speech -> ASR -> downstream QA with Korean dialect varieties already exists. | Use AICC TA/intent/slot/task success, not QA; add Busan/contact-center condition. |
| ASR-robust SLU | Chang & Chen 2022, https://www.isca-archive.org/interspeech_2022/chang22c_interspeech.html | Contrastive ASR-robust SLU exists. | Tie robustness to Korean dialect and semantic-critical business errors. |
| ASR-robust SLU attention | C²A-SLU 2023, https://www.isca-archive.org/interspeech_2023/cheng23c_interspeech.html | Clean-vs-ASR transcript contrast is already modeled. | Compare as downstream baseline; do not present as novelty. |
| ASR-robust SLU MoE | MoE-SLU 2024, https://aclanthology.org/2024.findings-acl.882/ | Mixture-of-experts for ASR-robust SLU exists. | Proposed MoE must be dialect/phonology/semantic-critical, not generic transcript mixture. |
| Accent adapter | Bhatia et al. 2023, https://www.isca-archive.org/interspeech_2023/bhatia23_interspeech.html | Accent-specific residual adapters are established. | Use adapters only as baseline unless method is substantially changed. |
| MAS-LoRA | Bagat et al. 2025, https://arxiv.org/abs/2505.20006 | Mixture of accent-specific LoRAs exists. | `Busan LoRA` alone is low novelty. |
| Accent MoE-CTC | Lee, Kim, Lee 2026, https://aclanthology.org/2026.acl-long.1194/ | Accent-aware routing plus intermediate CTC supervision exists. | Avoid generic accent-aware MoE; introduce semantic-critical or selective phonological objective. |
| Geographical LoRA | GLoRIA 2026, https://arxiv.org/html/2603.02464v1 | Geo-metadata-gated dialect LoRA exists. | Korean region metadata is not enough; need downstream TA gap or Busan-specific evaluation. |
| N-best correction | N-best T5 2023, https://www.isca-archive.org/interspeech_2023/ma23e_interspeech.html | N-best/lattice-based ASR correction exists. | Use N-best for critical-span ambiguity and clarification policy. |
| Korean ASR explainability | KEBAP 2023, https://aclanthology.org/2023.emnlp-main.292/ | Korean fine-grained ASR error benchmark exists. | Define AICC semantic-critical errors and dialect-specific propagation. |
| Semantic ASR metrics | Rugayan et al. 2023, https://www.isca-archive.org/interspeech_2023/rugayan23_interspeech.html | WER insufficiency and semantic metrics are known. | Use task-specific critical errors, not generic semantic distance only. |
| Korean allophone ASR | Hong, Kim, Chung 2008, https://www.isca-archive.org/interspeech_2008/hong08_interspeech.html | Korean allophone units in ASR are old prior art. | Novelty must be selective, dialect-error-driven, and auxiliary in modern encoders. |

## Research Position After Wave 1

The best paper framing is not:

```text
We improve Korean dialect ASR.
```

It should be:

```text
We show that Korean dialect + contact-center acoustic shift creates semantic-critical ASR errors
that WER underweights, then reduce those errors with a dialect/phonology-aware and
uncertainty-aware speech-to-TA pipeline.
```

## Open Risks

- Busan-specific data is not yet verified. Gyeongsang must not be treated as Busan.
- AI-Hub clean dialect data needs a defensible telephone/contact-center transformation or a real held-out call set.
- If selective allophone modeling improves WER but not semantic-critical errors, the AICC claim weakens.
- If N-best does not retain the correct negation/number/entity hypothesis, downstream reranking cannot recover the lost meaning.

## Next Leads

1. Download or obtain AI-Hub dataset guides to verify city-level metadata and license terms.
2. Search for Busan-specific corpora or collect a small IRB-safe Busan AICC-style held-out set.
3. Read full PDFs for KEBAP, SD-QA, Korean Whisper coda, MoE-CTC, MAS-LoRA, and C²A-SLU.
4. Build a baseline evaluation protocol: Whisper + Conformer/FastConformer on clean vs telephone-transformed Gyeongsang vs standard Korean.
5. Define AICC semantic-critical annotation schema and create a small synthetic/gold pilot set.
