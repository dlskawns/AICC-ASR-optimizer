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
#      uv run scripts/prepare_pilot_audio_subset.py research/experiments/runs/aihub_119_gold_review/gold_review_queue.local.jsonl research/experiments/runs/aihub_119_critical_span_candidates/critical_span_manifest.jsonl --output-dir research/experiments/runs/aihub_119_pilot_audio_subset
# 3. Or make executable and run:
#      chmod +x scripts/prepare_pilot_audio_subset.py && ./scripts/prepare_pilot_audio_subset.py research/experiments/runs/aihub_119_gold_review/gold_review_queue.local.jsonl research/experiments/runs/aihub_119_critical_span_candidates/critical_span_manifest.jsonl --output-dir research/experiments/runs/aihub_119_pilot_audio_subset
# ──────────────────

from __future__ import annotations

import json
import zipfile
from collections import Counter
from pathlib import Path
from typing import Annotated, TypeAlias, assert_never

import numpy as np
import typer
from build_dialect_taxonomy import JsonValue, text_field
from rich.console import Console

JsonObject: TypeAlias = dict[str, JsonValue]
PILOT_AUDIO_DIR = Path("data/interim/aihub_119_pilot_audio")
COHORTS = ("busan", "gyeongsang_other")
CATEGORIES = ("negation", "confirmation", "amount", "date_time", "intent_cue")

app = typer.Typer(add_completion=False)
console = Console()


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


def audio_zip_path() -> Path:
    roots = list(Path("data/raw/aihub_gyeongsang_119_validation_audio").rglob("*.zip"))
    if len(roots) != 1:
        msg = f"Expected one validation audio zip, found {len(roots)}"
        raise RuntimeError(msg)
    return roots[0]


def review_index(rows: list[JsonObject]) -> dict[str, JsonObject]:
    return {text_field(row, "review_id"): row for row in rows}


def manifest_index(rows: list[JsonObject]) -> dict[str, JsonObject]:
    return {text_field(row, "review_id"): row for row in rows}


def row_categories(manifest: JsonObject) -> list[str]:
    values = manifest.get("critical_categories")
    match values:
        case list() as items:
            return [item for item in items if isinstance(item, str)]
        case str() | int() | float() | bool() | dict() | None:
            return []
        case unreachable:
            assert_never(unreachable)


def select_review_ids(manifests: list[JsonObject], max_rows: int) -> list[str]:
    selected: list[str] = []
    seen: set[str] = set()
    target_per_cell = max(1, max_rows // (len(COHORTS) * len(CATEGORIES)))
    for cohort in COHORTS:
        cohort_rows = [row for row in manifests if text_field(row, "cohort") == cohort]
        for category in CATEGORIES:
            category_count = 0
            for row in cohort_rows:
                review_id = text_field(row, "review_id")
                if review_id in seen or category not in row_categories(row):
                    continue
                selected.append(review_id)
                seen.add(review_id)
                category_count += 1
                if category_count >= target_per_cell:
                    break
    for row in manifests:
        review_id = text_field(row, "review_id")
        if len(selected) >= max_rows:
            break
        if review_id and review_id not in seen:
            selected.append(review_id)
            seen.add(review_id)
    return selected[:max_rows]


def wav_member_name(archive: zipfile.ZipFile, source_file: str) -> str:
    target = f"{Path(source_file).stem}.wav"
    for name in archive.namelist():
        if Path(name).name == target:
            return name
    msg = f"Audio member not found for {source_file}"
    raise RuntimeError(msg)


def attach_audio_path(row: JsonObject, audio_path: Path) -> JsonObject:
    updated = dict(row)
    annotation = updated.get("final_annotation")
    match annotation:
        case dict() as mapping:
            final_annotation = dict(mapping)
            final_annotation["audio_path"] = str(audio_path)
            updated["final_annotation"] = final_annotation
        case str() | int() | float() | bool() | list() | None:
            updated["audio_path"] = str(audio_path)
        case unreachable:
            assert_never(unreachable)
    return updated


def extract_subset(rows: list[JsonObject]) -> list[JsonObject]:
    PILOT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    extracted: list[JsonObject] = []
    with zipfile.ZipFile(audio_zip_path()) as archive:
        for row in rows:
            source_file = text_field(row, "source_file")
            member = wav_member_name(archive, source_file)
            audio_path = PILOT_AUDIO_DIR / Path(member).name
            if not audio_path.exists():
                audio_path.write_bytes(archive.read(member))
            extracted.append(attach_audio_path(row, audio_path))
    return extracted


def manifest_row(row: JsonObject, manifest: JsonObject) -> JsonObject:
    annotation = row.get("final_annotation")
    categories = row_categories(manifest)
    match annotation:
        case dict() as mapping:
            audio_path = text_field(mapping, "audio_path")
        case str() | int() | float() | bool() | list() | None:
            audio_path = ""
        case unreachable:
            assert_never(unreachable)
    return {
        "review_id": text_field(row, "review_id"),
        "source_file": text_field(row, "source_file"),
        "utterance_id": text_field(row, "utterance_id"),
        "cohort": text_field(manifest, "cohort"),
        "critical_categories": categories,
        "audio_path": audio_path,
        "audio_present": Path(audio_path).exists(),
    }


def write_outputs(rows: list[JsonObject], manifests: dict[str, JsonObject], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "pilot_gold_review_queue.local.jsonl").open("w", encoding="utf-8") as file:
        for row in rows:
            _ = file.write(json.dumps(row, ensure_ascii=False) + "\n")
    manifest_rows = [manifest_row(row, manifests[text_field(row, "review_id")]) for row in rows]
    with (output_dir / "pilot_audio_manifest.local.jsonl").open("w", encoding="utf-8") as file:
        for row in manifest_rows:
            _ = file.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = {
        "pilot_rows": len(rows),
        "audio_present_rows": sum(1 for row in manifest_rows if row["audio_present"] is True),
        "unique_audio_files": len({text_field(row, "audio_path") for row in manifest_rows}),
        "cohort_counts": dict(Counter(text_field(row, "cohort") for row in manifest_rows).most_common()),
        "critical_category_counts": dict(
            Counter(category for row in manifest_rows for category in row["critical_categories"]).most_common(),
        ),
        "audio_dir": str(PILOT_AUDIO_DIR),
        "gold_status": "pilot_review_only_not_frozen_gold",
        "numpy_version": np.__version__,
    }
    _ = (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_readme(output_dir, summary)


def write_readme(output_dir: Path, summary: JsonObject) -> None:
    text = (
        "# Pilot Audio Subset\n\n"
        f"- Pilot rows: {summary['pilot_rows']}\n"
        f"- Audio-present rows: {summary['audio_present_rows']}\n"
        f"- Unique WAV files: {summary['unique_audio_files']}\n"
        f"- Cohort counts: `{json.dumps(summary['cohort_counts'], ensure_ascii=False)}`\n"
        "- Critical category counts: "
        f"`{json.dumps(summary['critical_category_counts'], ensure_ascii=False)}`\n"
        f"- Audio dir: `{summary['audio_dir']}`\n\n"
        "This is a local review/ASR pilot subset, not frozen gold.\n"
    )
    (output_dir / "README.md").write_text(text, encoding="utf-8")


@app.command()
def main(
    review_queue_path: Annotated[
        Path,
        typer.Argument(help="Gold review queue local JSONL.", exists=True, dir_okay=False, readable=True),
    ],
    critical_manifest_path: Annotated[
        Path,
        typer.Argument(help="Critical span manifest JSONL.", exists=True, dir_okay=False, readable=True),
    ],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
    max_rows: Annotated[int, typer.Option("--max-rows", min=1)] = 50,
) -> None:
    review_rows = review_index(load_jsonl(review_queue_path))
    critical_rows = load_jsonl(critical_manifest_path)
    manifests = manifest_index(critical_rows)
    selected = [review_rows[review_id] for review_id in select_review_ids(critical_rows, max_rows)]
    write_outputs(extract_subset(selected), manifests, output_dir)
    console.print(f"Wrote {output_dir}")


if __name__ == "__main__":
    app()
