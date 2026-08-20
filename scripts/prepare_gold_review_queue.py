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
#      uv run scripts/prepare_gold_review_queue.py research/experiments/runs/aihub_119_critical_span_candidates/critical_span_review_queue.local.jsonl --output-dir research/experiments/runs/aihub_119_gold_review
# 3. Or make executable and run:
#      chmod +x scripts/prepare_gold_review_queue.py && ./scripts/prepare_gold_review_queue.py research/experiments/runs/aihub_119_critical_span_candidates/critical_span_review_queue.local.jsonl --output-dir research/experiments/runs/aihub_119_gold_review
# ──────────────────

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Annotated, TypeAlias, assert_never

import numpy as np
import typer
from build_dialect_taxonomy import JsonValue, text_field
from build_weak_semantic_preannotations import preannotation
from rich.console import Console
from semantic_review_pack import stable_hash

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


def review_row(row: JsonObject) -> JsonObject | None:
    seed = preannotation(row)
    if seed is None:
        return None
    review_id = text_field(row, "review_id") or f"review-{stable_hash(text_field(row, 'utterance_id'))}"
    return {
        "review_id": review_id,
        "source_file": text_field(row, "source_file"),
        "utterance_id": text_field(row, "utterance_id"),
        "review_status": "unreviewed",
        "reviewer_id": "",
        "review_notes": "",
        "reject_reason": "",
        "final_annotation": seed,
    }


def manifest_row(row: JsonObject) -> JsonObject:
    source_file = text_field(row, "source_file")
    utterance_id = text_field(row, "utterance_id")
    return {
        "review_id": text_field(row, "review_id"),
        "source_file": source_file,
        "utterance_id": utterance_id,
        "utterance_hash": stable_hash(f"{source_file}:{utterance_id}"),
        "review_status": text_field(row, "review_status"),
    }


def write_outputs(rows: list[JsonObject], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    review_rows = [candidate for row in rows if (candidate := review_row(row)) is not None]
    with (output_dir / "gold_review_queue.local.jsonl").open("w", encoding="utf-8") as file:
        for row in review_rows:
            _ = file.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (output_dir / "gold_review_manifest.jsonl").open("w", encoding="utf-8") as file:
        for row in review_rows:
            _ = file.write(json.dumps(manifest_row(row), ensure_ascii=False) + "\n")
    summary = {
        "input_rows": len(rows),
        "review_rows": len(review_rows),
        "review_status_counts": dict(Counter(text_field(row, "review_status") for row in review_rows).most_common()),
        "raw_text_policy": "Raw transcript text is stored only in gold_review_queue.local.jsonl.",
        "gold_status": "not_gold_until_review_status_is_accepted",
        "numpy_version": np.__version__,
    }
    _ = (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_readme(output_dir, summary)


def write_readme(output_dir: Path, summary: JsonObject) -> None:
    text = (
        "# Gold Review Queue\n\n"
        f"- Input rows: {summary['input_rows']}\n"
        f"- Review rows: {summary['review_rows']}\n"
        "- Local queue: `gold_review_queue.local.jsonl`\n"
        "- Shareable manifest: `gold_review_manifest.jsonl`\n\n"
        "Set `review_status` to `accepted` only after human review. Edit `final_annotation` before freeze.\n"
    )
    (output_dir / "README.md").write_text(text, encoding="utf-8")


@app.command()
def main(
    input_path: Annotated[Path, typer.Argument(help="Critical span review queue local JSONL.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
) -> None:
    if not input_path.exists():
        console.print(f"Review queue not found: {input_path}")
        raise typer.Exit(code=2)
    write_outputs(load_rows(input_path), output_dir)
    console.print(f"Wrote {output_dir}")


if __name__ == "__main__":
    app()
