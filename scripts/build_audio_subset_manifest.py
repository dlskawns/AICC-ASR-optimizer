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
#      uv run scripts/build_audio_subset_manifest.py research/experiments/runs/aihub_119_gold_review/gold_review_queue.local.jsonl --output-dir research/experiments/runs/aihub_119_audio_subset_request --include-unreviewed
# 3. Or make executable and run:
#      chmod +x scripts/build_audio_subset_manifest.py && ./scripts/build_audio_subset_manifest.py research/experiments/runs/aihub_119_gold_review/gold_review_queue.local.jsonl --output-dir research/experiments/runs/aihub_119_audio_subset_request --include-unreviewed
# ──────────────────

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Annotated, TypeAlias, assert_never

import numpy as np
import typer
from build_dialect_taxonomy import JsonValue, text_field
from rich.console import Console
from semantic_review_pack import stable_hash

JsonObject: TypeAlias = dict[str, JsonValue]

VALIDATION_AUDIO_FILEKEY = "572714"
VALIDATION_AUDIO_ARCHIVE = "(비식별화완료)경상도_2.zip"
VALIDATION_AUDIO_SIZE = "28 GB"

app = typer.Typer(add_completion=False)
console = Console()


def load_rows(path: Path) -> list[JsonObject]:
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


def annotation(row: JsonObject) -> JsonObject:
    value = row.get("final_annotation")
    match value:
        case dict() as mapping:
            return mapping
        case str() | int() | float() | bool() | list() | None:
            return row
        case unreachable:
            assert_never(unreachable)


def selected_rows(rows: list[JsonObject], include_unreviewed: bool) -> list[JsonObject]:
    if include_unreviewed:
        return rows
    return [row for row in rows if text_field(row, "review_status") == "accepted"]


def manifest_row(row: JsonObject) -> JsonObject:
    ann = annotation(row)
    source_file = text_field(row, "source_file")
    utterance_id = text_field(row, "utterance_id") or text_field(ann, "utterance_id")
    return {
        "review_id": text_field(row, "review_id"),
        "source_file": source_file,
        "utterance_id": utterance_id,
        "utterance_hash": stable_hash(f"{source_file}:{utterance_id}"),
        "review_status": text_field(row, "review_status"),
        "speaker_region": text_field(ann, "speaker_region"),
        "domain": text_field(ann, "domain"),
        "aihub_dataset_id": "119",
        "required_audio_filekey": VALIDATION_AUDIO_FILEKEY,
        "required_audio_archive": VALIDATION_AUDIO_ARCHIVE,
        "required_audio_archive_size": VALIDATION_AUDIO_SIZE,
        "download_status": "not_downloaded",
    }


def write_outputs(rows: list[JsonObject], output_dir: Path, include_unreviewed: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    picked = selected_rows(rows, include_unreviewed)
    with (output_dir / "audio_subset_request_manifest.jsonl").open("w", encoding="utf-8") as file:
        for row in picked:
            _ = file.write(json.dumps(manifest_row(row), ensure_ascii=False) + "\n")
    summary = {
        "input_rows": len(rows),
        "manifest_rows": len(picked),
        "include_unreviewed": include_unreviewed,
        "review_status_counts": dict(Counter(text_field(row, "review_status") for row in picked).most_common()),
        "required_audio_filekey": VALIDATION_AUDIO_FILEKEY,
        "required_audio_archive": VALIDATION_AUDIO_ARCHIVE,
        "required_audio_archive_size": VALIDATION_AUDIO_SIZE,
        "download_decision": "stop_before_download_large_archive",
        "numpy_version": np.__version__,
    }
    _ = (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_readme(output_dir, summary)


def write_readme(output_dir: Path, summary: JsonObject) -> None:
    text = (
        "# Audio Subset Request\n\n"
        f"- Manifest rows: {summary['manifest_rows']}\n"
        f"- Required filekey: `{summary['required_audio_filekey']}`\n"
        f"- Required archive: `{summary['required_audio_archive']}`\n"
        f"- Archive size: {summary['required_audio_archive_size']}\n\n"
        "This manifest does not download audio. Downloading this archive is the large-download stop point.\n"
    )
    (output_dir / "README.md").write_text(text, encoding="utf-8")


@app.command()
def main(
    review_queue_path: Annotated[Path, typer.Argument(help="Gold review queue local JSONL.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
    include_unreviewed: Annotated[bool, typer.Option("--include-unreviewed")] = False,
) -> None:
    if not review_queue_path.exists():
        console.print(f"Review queue not found: {review_queue_path}")
        raise typer.Exit(code=2)
    write_outputs(load_rows(review_queue_path), output_dir, include_unreviewed)
    console.print(f"Wrote {output_dir}")


if __name__ == "__main__":
    app()
