#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "jsonschema",
#     "numpy",
#     "rich",
#     "typer",
# ]
# ///

# ─── How to run ───
# 1. Install uv (if not installed):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Run directly (no venv, no pip install needed):
#      uv run scripts/freeze_gold_annotations.py research/experiments/runs/aihub_119_gold_review/gold_review_queue.local.jsonl --output-dir research/experiments/runs/aihub_119_gold_freeze
# 3. Or make executable and run:
#      chmod +x scripts/freeze_gold_annotations.py && ./scripts/freeze_gold_annotations.py research/experiments/runs/aihub_119_gold_review/gold_review_queue.local.jsonl --output-dir research/experiments/runs/aihub_119_gold_freeze
# ──────────────────

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Annotated, TypeAlias, assert_never

import numpy as np
import typer
from build_dialect_taxonomy import JsonValue, list_of_mappings, text_field
from rich.console import Console
from semantic_review_pack import stable_hash
from validate_semantic_annotations import load_schema, validation_issues

JsonObject: TypeAlias = dict[str, JsonValue]

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


def final_annotation(row: JsonObject) -> JsonObject | None:
    if text_field(row, "review_status") != "accepted":
        return None
    candidate = row.get("final_annotation")
    match candidate:
        case dict() as mapping:
            return mapping
        case str() | int() | float() | bool() | list() | None:
            return None
        case unreachable:
            assert_never(unreachable)


def accepted_annotations(rows: list[JsonObject]) -> list[JsonObject]:
    return [annotation for row in rows if (annotation := final_annotation(row)) is not None]


def manifest_row(row: JsonObject) -> JsonObject | None:
    annotation = final_annotation(row)
    if annotation is None:
        return None
    source_file = text_field(row, "source_file")
    utterance_id = text_field(annotation, "utterance_id")
    return {
        "review_id": text_field(row, "review_id"),
        "source_file": source_file,
        "utterance_id": utterance_id,
        "utterance_hash": stable_hash(f"{source_file}:{utterance_id}"),
        "audio_path_present": bool(text_field(annotation, "audio_path")),
        "domain": text_field(annotation, "domain"),
        "critical_span_count": len(list_of_mappings(annotation.get("critical_spans"))),
    }


def summary_json(rows: list[JsonObject], accepted: list[JsonObject], errors: int) -> JsonObject:
    return {
        "input_rows": len(rows),
        "accepted_rows": len(accepted),
        "schema_error_count": errors,
        "review_status_counts": dict(Counter(text_field(row, "review_status") for row in rows).most_common()),
        "domain_counts": dict(Counter(text_field(row, "domain") for row in accepted).most_common()),
        "critical_span_counts": dict(
            Counter(
                text_field(span, "category")
                for row in accepted
                for span in list_of_mappings(row.get("critical_spans"))
            ).most_common(),
        ),
        "rows_with_audio_path": sum(1 for row in accepted if text_field(row, "audio_path")),
        "gold_status": "frozen_gold" if accepted and errors == 0 else "no_frozen_gold_rows",
        "numpy_version": np.__version__,
    }


def write_outputs(rows: list[JsonObject], schema: JsonObject, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    accepted = accepted_annotations(rows)
    issues = validation_issues(accepted, schema)
    if accepted:
        with (output_dir / "gold_semantic_annotations.local.jsonl").open("w", encoding="utf-8") as file:
            for row in accepted:
                _ = file.write(json.dumps(row, ensure_ascii=False) + "\n")
        with (output_dir / "gold_manifest.jsonl").open("w", encoding="utf-8") as file:
            for row in rows:
                manifest = manifest_row(row)
                if manifest is not None:
                    _ = file.write(json.dumps(manifest, ensure_ascii=False) + "\n")
    summary = summary_json(rows, accepted, len(issues))
    _ = (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_readme(output_dir, summary)


def write_readme(output_dir: Path, summary: JsonObject) -> None:
    text = (
        "# Gold Freeze\n\n"
        f"- Input rows: {summary['input_rows']}\n"
        f"- Accepted rows: {summary['accepted_rows']}\n"
        f"- Schema errors: {summary['schema_error_count']}\n"
        f"- Rows with audio path: {summary['rows_with_audio_path']}\n\n"
        "Only rows with `review_status=accepted` are frozen as gold.\n"
    )
    (output_dir / "README.md").write_text(text, encoding="utf-8")


@app.command()
def main(
    review_queue_path: Annotated[Path, typer.Argument(help="Reviewed gold queue local JSONL.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
    schema_path: Annotated[Path, typer.Option("--schema")] = Path("research/evaluation/semantic_critical_schema.json"),
) -> None:
    if not review_queue_path.exists():
        console.print(f"Review queue not found: {review_queue_path}")
        raise typer.Exit(code=2)
    write_outputs(load_rows(review_queue_path), load_schema(schema_path), output_dir)
    console.print(f"Wrote {output_dir}")


if __name__ == "__main__":
    app()
