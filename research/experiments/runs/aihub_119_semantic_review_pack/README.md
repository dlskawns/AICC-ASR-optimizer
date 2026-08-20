# Semantic Review Pack

- Selected rows: 510
- Samples per cohort/category group: 50
- Local raw-text queue: `semantic_review_queue.local.jsonl`
- Shareable manifest: `semantic_review_manifest.jsonl`

The `.local.jsonl` file includes AI-Hub transcript text for internal annotation only.
Do not commit, publish, or paste raw rows from that file.

Reviewer task: fill `domain`, `intent`, `slots`, and `critical_spans`.
The `candidate_critical_spans` field is a hint, not a gold label.
