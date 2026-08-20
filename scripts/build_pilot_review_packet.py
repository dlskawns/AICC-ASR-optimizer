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
#      uv run scripts/build_pilot_review_packet.py research/experiments/runs/aihub_119_pilot_audio_subset/pilot_gold_review_queue.local.jsonl research/experiments/runs/aihub_119_pilot_audio_subset/pilot_audio_manifest.local.jsonl --output-dir research/experiments/runs/aihub_119_pilot_review_packet
# 3. Or make executable and run:
#      chmod +x scripts/build_pilot_review_packet.py && ./scripts/build_pilot_review_packet.py research/experiments/runs/aihub_119_pilot_audio_subset/pilot_gold_review_queue.local.jsonl research/experiments/runs/aihub_119_pilot_audio_subset/pilot_audio_manifest.local.jsonl --output-dir research/experiments/runs/aihub_119_pilot_review_packet
# ──────────────────

from __future__ import annotations

import csv
import json
import wave
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, TypeAlias, assert_never

import numpy as np
import typer
from build_dialect_taxonomy import JsonValue, list_of_mappings, text_field
from rich.console import Console
from semantic_review_pack import stable_hash

JsonObject: TypeAlias = dict[str, JsonValue]
CLIP_DIR = Path("data/interim/aihub_119_pilot_clips")

app = typer.Typer(add_completion=False)
console = Console()


@dataclass(frozen=True, slots=True)
class ClipWindow:
    start_seconds: float
    end_seconds: float


@dataclass(frozen=True, slots=True)
class ClipRequest:
    source_path: Path
    output_path: Path
    window: ClipWindow
    padding_seconds: float


@dataclass(frozen=True, slots=True)
class PreparedRow:
    review_row: JsonObject
    audio_row: JsonObject
    annotation: JsonObject
    window: ClipWindow
    clip_path: Path
    clip_duration_seconds: float


def load_jsonl(path: Path) -> list[JsonObject]:
    rows: list[JsonObject] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        payload = json.loads(line)
        match payload:
            case dict() as mapping:
                rows.append(mapping)
            case str() | int() | float() | bool() | list() | None:
                continue
            case unreachable:
                assert_never(unreachable)
    return rows


def row_index(rows: list[JsonObject]) -> dict[str, JsonObject]:
    return {text_field(row, "review_id"): row for row in rows}


def annotation(row: JsonObject) -> JsonObject:
    value = row.get("final_annotation")
    match value:
        case dict() as mapping:
            return mapping
        case str() | int() | float() | bool() | list() | None:
            return {}
        case unreachable:
            assert_never(unreachable)


def numeric_field(mapping: JsonObject, key: str) -> float:
    match mapping.get(key):
        case bool():
            return 0.0
        case int() | float() as value:
            return float(value)
        case str() | list() | dict() | None:
            return 0.0
        case unreachable:
            assert_never(unreachable)


def label_member_index(label_root: Path) -> dict[str, tuple[Path, str]]:
    members: dict[str, tuple[Path, str]] = {}
    zip_paths = [label_root] if label_root.is_file() and label_root.suffix == ".zip" else sorted(label_root.rglob("*.zip"))
    for zip_path in zip_paths:
        with zipfile.ZipFile(zip_path) as archive:
            for name in archive.namelist():
                if name.endswith(".json"):
                    members[Path(name).name] = (zip_path, name)
    return members


def label_payload(index: dict[str, tuple[Path, str]], source_file: str) -> JsonObject:
    zip_path, member = index[source_file]
    with zipfile.ZipFile(zip_path) as archive:
        payload = json.loads(archive.read(member).decode("utf-8"))
    match payload:
        case dict() as mapping:
            return mapping
        case str() | int() | float() | bool() | list() | None:
            msg = f"JSON root is not an object: {source_file}"
            raise RuntimeError(msg)
        case unreachable:
            assert_never(unreachable)


def utterance_window(payload: JsonObject, utterance_id: str) -> ClipWindow:
    for row in list_of_mappings(payload.get("utterance")):
        if text_field(row, "id") != utterance_id:
            continue
        return ClipWindow(numeric_field(row, "start"), numeric_field(row, "end"))
    msg = f"Utterance not found in label payload: {utterance_id}"
    raise RuntimeError(msg)


def write_clip(request: ClipRequest) -> float:
    request.output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(request.source_path), "rb") as source:
        frame_rate = source.getframerate()
        frame_count = source.getnframes()
        start = max(0, int((request.window.start_seconds - request.padding_seconds) * frame_rate))
        end = min(frame_count, int((request.window.end_seconds + request.padding_seconds) * frame_rate))
        if end <= start:
            msg = f"Invalid clip window for {request.source_path}: {request.window}"
            raise RuntimeError(msg)
        source.setpos(start)
        frames = source.readframes(end - start)
        params = source.getparams()
    with wave.open(str(request.output_path), "wb") as target:
        target.setparams(params)
        target.writeframes(frames)
    return (end - start) / frame_rate


def categories(annotation_row: JsonObject) -> list[str]:
    return [text_field(span, "category") for span in list_of_mappings(annotation_row.get("critical_spans"))]


def prepare_rows(
    review_rows: list[JsonObject],
    audio_rows: list[JsonObject],
    label_root: Path,
    padding_seconds: float,
) -> list[PreparedRow]:
    audio_by_id = row_index(audio_rows)
    labels = label_member_index(label_root)
    prepared: list[PreparedRow] = []
    for row in review_rows:
        review_id = text_field(row, "review_id")
        audio_row = audio_by_id[review_id]
        ann = annotation(row)
        source_file = text_field(row, "source_file")
        utterance_id = text_field(row, "utterance_id")
        window = utterance_window(label_payload(labels, source_file), utterance_id)
        clip_path = CLIP_DIR / f"{review_id}.wav"
        duration = write_clip(
            ClipRequest(Path(text_field(audio_row, "audio_path")), clip_path, window, padding_seconds),
        )
        prepared.append(PreparedRow(row, audio_row, ann, window, clip_path, duration))
    return prepared


def tsv_row(row: PreparedRow) -> dict[str, str]:
    spans = list_of_mappings(row.annotation.get("critical_spans"))
    slots = list_of_mappings(row.annotation.get("slots"))
    return {
        "review_id": text_field(row.review_row, "review_id"),
        "review_status": text_field(row.review_row, "review_status"),
        "cohort": text_field(row.audio_row, "cohort"),
        "source_file": text_field(row.review_row, "source_file"),
        "utterance_id": text_field(row.review_row, "utterance_id"),
        "clip_path": str(row.clip_path),
        "recording_path": text_field(row.audio_row, "audio_path"),
        "start_sec": f"{row.window.start_seconds:.2f}",
        "end_sec": f"{row.window.end_seconds:.2f}",
        "clip_duration_sec": f"{row.clip_duration_seconds:.2f}",
        "speaker_region": text_field(row.annotation, "speaker_region"),
        "speaker_age_band": text_field(row.annotation, "speaker_age_band"),
        "domain": text_field(row.annotation, "domain"),
        "intent": text_field(row.annotation, "intent"),
        "critical_categories": json.dumps(categories(row.annotation), ensure_ascii=False, separators=(",", ":")),
        "critical_spans": json.dumps(spans, ensure_ascii=False, separators=(",", ":")),
        "slots": json.dumps(slots, ensure_ascii=False, separators=(",", ":")),
        "clarification_required": str(row.annotation.get("clarification_required")),
        "dialect_transcript": text_field(row.annotation, "dialect_transcript"),
        "standard_transcript": text_field(row.annotation, "standard_transcript"),
        "reviewer_decision": "",
        "reviewer_notes": "",
    }


def public_manifest_row(row: PreparedRow) -> JsonObject:
    source_file = text_field(row.review_row, "source_file")
    utterance_id = text_field(row.review_row, "utterance_id")
    return {
        "review_id": text_field(row.review_row, "review_id"),
        "utterance_hash": stable_hash(f"{source_file}:{utterance_id}"),
        "source_file": source_file,
        "utterance_id": utterance_id,
        "cohort": text_field(row.audio_row, "cohort"),
        "start_sec": row.window.start_seconds,
        "end_sec": row.window.end_seconds,
        "clip_duration_sec": round(row.clip_duration_seconds, 3),
        "review_status": text_field(row.review_row, "review_status"),
        "domain": text_field(row.annotation, "domain"),
        "intent": text_field(row.annotation, "intent"),
        "critical_categories": categories(row.annotation),
        "critical_span_count": len(list_of_mappings(row.annotation.get("critical_spans"))),
        "slot_count": len(list_of_mappings(row.annotation.get("slots"))),
        "clip_present": row.clip_path.exists(),
    }


def write_tsv(rows: list[PreparedRow], path: Path) -> None:
    fieldnames = list(tsv_row(rows[0]).keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(tsv_row(row))


def write_jsonl(rows: list[JsonObject], path: Path) -> None:
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            _ = file.write(json.dumps(row, ensure_ascii=False) + "\n")


def summary(rows: list[PreparedRow]) -> JsonObject:
    accepted = sum(1 for row in rows if text_field(row.review_row, "review_status") == "accepted")
    category_counts = Counter(category for row in rows for category in categories(row.annotation))
    return {
        "review_rows": len(rows),
        "accepted_rows": accepted,
        "clip_rows": sum(1 for row in rows if row.clip_path.exists()),
        "clip_dir": str(CLIP_DIR),
        "total_clip_duration_minutes": round(sum(row.clip_duration_seconds for row in rows) / 60, 2),
        "cohort_counts": dict(Counter(text_field(row.audio_row, "cohort") for row in rows).most_common()),
        "critical_category_counts": dict(category_counts.most_common()),
        "baseline_status": "ready_for_asr_after_gold_review" if accepted else "blocked_by_unreviewed_gold",
        "numpy_version": np.__version__,
    }


def write_readme(output_dir: Path, report: JsonObject) -> None:
    text = (
        "# Pilot Review Packet\n\n"
        f"- Review rows: {report['review_rows']}\n"
        f"- Accepted rows: {report['accepted_rows']}\n"
        f"- Clip rows: {report['clip_rows']}\n"
        f"- Clip dir: `{report['clip_dir']}`\n"
        f"- Total clip duration: {report['total_clip_duration_minutes']} minutes\n\n"
        "Use `pilot_reviewer_sheet.local.tsv` for manual review. It contains restricted transcript text and is git-ignored.\n"
        "Do not mark rows accepted until the annotation and clip have both been checked.\n"
    )
    (output_dir / "README.md").write_text(text, encoding="utf-8")


def write_outputs(rows: list[PreparedRow], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(rows, output_dir / "pilot_reviewer_sheet.local.tsv")
    write_jsonl([row.annotation for row in rows], output_dir / "pilot_candidate_annotations.local.jsonl")
    write_jsonl([public_manifest_row(row) for row in rows], output_dir / "pilot_review_manifest.jsonl")
    report = summary(rows)
    (output_dir / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_readme(output_dir, report)


@app.command()
def main(
    review_queue_path: Annotated[Path, typer.Argument(help="Pilot gold review queue local JSONL.")],
    audio_manifest_path: Annotated[Path, typer.Argument(help="Pilot audio manifest local JSONL.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
    label_root: Annotated[Path, typer.Option("--label-root")] = Path("data/raw/aihub_gyeongsang_119"),
    padding_seconds: Annotated[float, typer.Option("--padding-seconds", min=0.0)] = 0.25,
) -> None:
    if not review_queue_path.exists():
        console.print(f"Review queue not found: {review_queue_path}")
        raise typer.Exit(code=2)
    if not audio_manifest_path.exists():
        console.print(f"Audio manifest not found: {audio_manifest_path}")
        raise typer.Exit(code=2)
    rows = prepare_rows(load_jsonl(review_queue_path), load_jsonl(audio_manifest_path), label_root, padding_seconds)
    write_outputs(rows, output_dir)
    console.print(f"Wrote {output_dir}")


if __name__ == "__main__":
    app()
