#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "numpy",
#     "rich",
#     "typer",
# ]
# ///

# ─── How to run ───
# 1. Install uv (if not installed):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Run directly (no venv, no pip install needed):
#      uv run scripts/mine_critical_span_candidates.py data/raw/aihub_gyeongsang_119 research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz --output-dir research/experiments/runs/aihub_119_critical_span_candidates
# 3. Or make executable and run:
#      chmod +x scripts/mine_critical_span_candidates.py && ./scripts/mine_critical_span_candidates.py data/raw/aihub_gyeongsang_119 research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz --output-dir research/experiments/runs/aihub_119_critical_span_candidates
# ──────────────────

from __future__ import annotations

import json
import random
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, TypeAlias

import numpy as np
import typer
from build_dialect_taxonomy import (
    Category,
    JsonValue,
    cohort,
    list_of_mappings,
    manifest_slices,
    text_field,
)
from build_weak_semantic_preannotations import transcript_critical_spans
from rich.console import Console
from semantic_review_pack import (
    dialect_spans,
    load_payload,
    source_zips,
    speaker_region,
    stable_hash,
)

JsonObject: TypeAlias = dict[str, JsonValue]

app = typer.Typer(add_completion=False)
console = Console()


@dataclass(frozen=True, slots=True)
class CriticalCandidate:
    review_id: str
    source_file: str
    utterance_id: str
    cohort: str
    slice_label: str
    speaker_region: str
    speaker_age_band: str
    speaker_sex: str
    topic: str
    dialect_transcript: str
    standard_transcript: str
    primary_dialect_category: Category
    dialect_category_counts: dict[str, int]
    critical_candidates: list[JsonObject]


def critical_categories(candidate: CriticalCandidate) -> tuple[str, ...]:
    categories = {
        text_field(span, "category")
        for span in candidate.critical_candidates
        if text_field(span, "category")
    }
    return tuple(sorted(categories))


def make_candidate(
    source_file: str,
    metadata: JsonObject,
    speaker: JsonObject,
    utterance: JsonObject,
    slice_label: str,
) -> CriticalCandidate | None:
    cohort_label = cohort(slice_label)
    if cohort_label == "other":
        return None
    spans = dialect_spans(utterance)
    if not spans:
        return None
    dialect_text = text_field(utterance, "dialect_form") or text_field(utterance, "form")
    standard_text = text_field(utterance, "standard_form")
    critical = transcript_critical_spans(f"{standard_text} {dialect_text}")
    if not critical:
        return None
    category_counts: Counter[Category] = Counter(span.dialect_category for span in spans)
    utterance_id = text_field(utterance, "id")
    primary = category_counts.most_common(1)[0][0]
    return CriticalCandidate(
        f"critrev-{stable_hash(f'{source_file}:{utterance_id}:{primary}')}",
        source_file,
        utterance_id,
        cohort_label,
        slice_label,
        speaker_region(speaker),
        text_field(speaker, "age"),
        text_field(speaker, "sex"),
        text_field(metadata, "topic"),
        dialect_text,
        standard_text,
        primary,
        dict(category_counts.most_common()),
        critical,
    )


def collect_candidates(input_path: Path, manifest_path: Path) -> list[CriticalCandidate]:
    slices = manifest_slices(manifest_path)
    candidates: list[CriticalCandidate] = []
    for zip_path in source_zips(input_path):
        with zipfile.ZipFile(zip_path) as archive:
            for name in sorted(item for item in archive.namelist() if item.endswith(".json")):
                payload = load_payload(archive, name)
                metadata = payload.get("metadata")
                metadata_map = metadata if isinstance(metadata, dict) else {}
                speakers = {
                    text_field(speaker, "id"): speaker
                    for speaker in list_of_mappings(payload.get("speaker"))
                }
                candidates.extend(entry_candidates(name, metadata_map, speakers, payload, slices))
    return candidates


def entry_candidates(
    source_file: str,
    metadata: JsonObject,
    speakers: dict[str, JsonObject],
    payload: JsonObject,
    slices: dict[str, str],
) -> list[CriticalCandidate]:
    candidates: list[CriticalCandidate] = []
    for utterance in list_of_mappings(payload.get("utterance")):
        speaker = speakers.get(text_field(utterance, "speaker_id"))
        if speaker is None:
            continue
        key = f"{source_file}:{text_field(utterance, 'id')}"
        candidate = make_candidate(source_file, metadata, speaker, utterance, slices.get(key, "other"))
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def sample_candidates(
    candidates: list[CriticalCandidate],
    samples_per_cell: int,
    seed: int,
) -> tuple[list[CriticalCandidate], dict[str, int]]:
    groups: dict[tuple[str, str], list[CriticalCandidate]] = {}
    for candidate in candidates:
        for category in critical_categories(candidate):
            groups.setdefault((candidate.cohort, category), []).append(candidate)
    selected: dict[str, CriticalCandidate] = {}
    rng = random.Random(seed)
    pool_counts: dict[str, int] = {}
    for cohort_label, category in sorted(groups):
        pool = sorted(groups[(cohort_label, category)], key=lambda item: item.review_id)
        pool_counts[f"{cohort_label}:{category}"] = len(pool)
        chosen = rng.sample(pool, samples_per_cell) if len(pool) > samples_per_cell else pool
        selected.update((candidate.review_id, candidate) for candidate in chosen)
    return sorted(selected.values(), key=lambda item: item.review_id), pool_counts


def local_row(candidate: CriticalCandidate) -> JsonObject:
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
        "primary_dialect_category": candidate.primary_dialect_category,
        "dialect_category_counts": candidate.dialect_category_counts,
        "critical_span_candidates": candidate.critical_candidates,
        "notes": "",
    }


def manifest_row(candidate: CriticalCandidate) -> JsonObject:
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
        "primary_dialect_category": candidate.primary_dialect_category,
        "dialect_category_counts": candidate.dialect_category_counts,
        "critical_categories": list(critical_categories(candidate)),
        "dialect_transcript_char_length": len(candidate.dialect_transcript),
        "standard_transcript_char_length": len(candidate.standard_transcript),
    }


def write_outputs(
    selected: list[CriticalCandidate],
    pool_counts: dict[str, int],
    output_dir: Path,
    samples_per_cell: int,
    seed: int,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "critical_span_review_queue.local.jsonl").open("w", encoding="utf-8") as file:
        for candidate in selected:
            _ = file.write(json.dumps(local_row(candidate), ensure_ascii=False) + "\n")
    with (output_dir / "critical_span_manifest.jsonl").open("w", encoding="utf-8") as file:
        for candidate in selected:
            _ = file.write(json.dumps(manifest_row(candidate), ensure_ascii=False) + "\n")
    summary = summary_json(selected, pool_counts, samples_per_cell, seed)
    _ = (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_readme(output_dir, summary)


def summary_json(
    selected: list[CriticalCandidate],
    pool_counts: dict[str, int],
    samples_per_cell: int,
    seed: int,
) -> JsonObject:
    span_counts = Counter(
        text_field(span, "category")
        for candidate in selected
        for span in candidate.critical_candidates
    )
    return {
        "selected_rows": len(selected),
        "samples_per_cell": samples_per_cell,
        "seed": seed,
        "candidate_pool_counts": pool_counts,
        "selected_critical_span_counts": dict(span_counts.most_common()),
        "selected_cohort_counts": dict(Counter(candidate.cohort for candidate in selected).most_common()),
        "selected_primary_dialect_counts": dict(Counter(candidate.primary_dialect_category for candidate in selected).most_common()),
        "raw_text_policy": "Raw transcript text is stored only in critical_span_review_queue.local.jsonl.",
        "numpy_version": np.__version__,
    }


def write_readme(output_dir: Path, summary: JsonObject) -> None:
    text = (
        "# Critical Span Candidates\n\n"
        f"- Selected rows: {summary['selected_rows']}\n"
        f"- Samples per cohort/critical-category cell: {summary['samples_per_cell']}\n"
        "- Local raw-text queue: `critical_span_review_queue.local.jsonl`\n"
        "- Shareable manifest: `critical_span_manifest.jsonl`\n\n"
        "This batch fills semantic-critical coverage gaps before audio download.\n"
        "The local queue is for human review only and is not gold.\n"
    )
    (output_dir / "README.md").write_text(text, encoding="utf-8")


@app.command()
def main(
    input_path: Annotated[Path, typer.Argument(help="AI-Hub label zip or directory.")],
    manifest_path: Annotated[Path, typer.Argument(help="Busan slice manifest jsonl.gz.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
    samples_per_cell: Annotated[int, typer.Option("--samples-per-cell")] = 40,
    seed: Annotated[int, typer.Option("--seed")] = 119,
) -> None:
    if not source_zips(input_path):
        console.print(f"No zip files found under {input_path}")
        raise typer.Exit(code=2)
    if not manifest_path.exists():
        console.print(f"Manifest not found: {manifest_path}")
        raise typer.Exit(code=2)
    selected, pool_counts = sample_candidates(collect_candidates(input_path, manifest_path), samples_per_cell, seed)
    write_outputs(selected, pool_counts, output_dir, samples_per_cell, seed)
    console.print(f"Wrote {output_dir}")


if __name__ == "__main__":
    app()
