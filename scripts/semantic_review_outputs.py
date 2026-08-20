from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import numpy as np
from build_dialect_taxonomy import JsonValue
from semantic_review_pack import ReviewCandidate, stable_hash


def local_review_row(candidate: ReviewCandidate) -> dict[str, JsonValue]:
    return {
        "review_id": candidate.review_id,
        "annotation_status": "needs_human_review",
        "source_file": candidate.source_file,
        "utterance_id": candidate.utterance_id,
        "audio_path": "",
        "speaker_region": candidate.speaker_region,
        "speaker_age_band": candidate.speaker_age_band,
        "speaker_sex": candidate.speaker_sex,
        "acoustic_condition": "unknown",
        "source_topic": candidate.topic,
        "dialect_transcript": candidate.dialect_transcript,
        "standard_transcript": candidate.standard_transcript,
        "domain": "other",
        "intent": "",
        "slots": [],
        "critical_spans": [],
        "clarification_required": False,
        "primary_dialect_category": candidate.primary_category,
        "category_counts": candidate.category_counts,
        "candidate_critical_spans": [asdict(span) for span in candidate.spans],
        "notes": "",
    }


def manifest_row(candidate: ReviewCandidate) -> dict[str, JsonValue]:
    return {
        "review_id": candidate.review_id,
        "utterance_hash": stable_hash(f"{candidate.source_file}:{candidate.utterance_id}"),
        "source_file_hash": stable_hash(candidate.source_file),
        "cohort": candidate.cohort,
        "slice_label": candidate.slice_label,
        "speaker_region": candidate.speaker_region,
        "speaker_age_band": candidate.speaker_age_band,
        "speaker_sex": candidate.speaker_sex,
        "topic": candidate.topic,
        "primary_dialect_category": candidate.primary_category,
        "category_counts": candidate.category_counts,
        "dialect_eojeol_count": len(candidate.spans),
        "dialect_transcript_char_length": len(candidate.dialect_transcript),
        "standard_transcript_char_length": len(candidate.standard_transcript),
    }


def write_outputs(
    selected: list[ReviewCandidate],
    pool_counts: dict[str, int],
    output_dir: Path,
    samples_per_group: int,
    seed: int,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "semantic_review_queue.local.jsonl").open("w", encoding="utf-8") as file:
        for candidate in selected:
            _ = file.write(json.dumps(local_review_row(candidate), ensure_ascii=False) + "\n")
    with (output_dir / "semantic_review_manifest.jsonl").open("w", encoding="utf-8") as file:
        for candidate in selected:
            _ = file.write(json.dumps(manifest_row(candidate), ensure_ascii=False) + "\n")
    summary = {
        "selected_rows": len(selected),
        "samples_per_group": samples_per_group,
        "seed": seed,
        "candidate_pool_counts": pool_counts,
        "selected_counts": dict(
            Counter(f"{candidate.cohort}:{candidate.primary_category}" for candidate in selected).most_common(),
        ),
        "raw_text_policy": "Raw transcript text is stored only in semantic_review_queue.local.jsonl.",
        "numpy_version": np.__version__,
    }
    _ = (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_readme(output_dir, summary)


def write_readme(output_dir: Path, summary: dict[str, JsonValue]) -> None:
    lines = [
        "# Semantic Review Pack",
        "",
        f"- Selected rows: {summary['selected_rows']}",
        f"- Samples per cohort/category group: {summary['samples_per_group']}",
        "- Local raw-text queue: `semantic_review_queue.local.jsonl`",
        "- Shareable manifest: `semantic_review_manifest.jsonl`",
        "",
        "The `.local.jsonl` file includes AI-Hub transcript text for internal annotation only.",
        "Do not commit, publish, or paste raw rows from that file.",
        "",
        "Reviewer task: fill `domain`, `intent`, `slots`, and `critical_spans`.",
        "The `candidate_critical_spans` field is a hint, not a gold label.",
    ]
    (output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
