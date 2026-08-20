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
#      uv run scripts/validate_semantic_annotations.py research/experiments/runs/aihub_119_semantic_preannotations/weak_semantic_preannotations.local.jsonl --output-dir research/experiments/runs/aihub_119_semantic_preannotations
# 3. Or make executable and run:
#      chmod +x scripts/validate_semantic_annotations.py && ./scripts/validate_semantic_annotations.py research/experiments/runs/aihub_119_semantic_preannotations/weak_semantic_preannotations.local.jsonl --output-dir research/experiments/runs/aihub_119_semantic_preannotations
# ──────────────────

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated, TypeAlias, assert_never

import numpy as np
import typer
from build_dialect_taxonomy import JsonValue, list_of_mappings, text_field
from jsonschema import Draft202012Validator
from rich.console import Console

JsonObject: TypeAlias = dict[str, JsonValue]

app = typer.Typer(add_completion=False)
console = Console()


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    row_index: int
    json_path: str
    message: str


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


def load_schema(path: Path) -> JsonObject:
    payload = json.loads(path.read_text(encoding="utf-8"))
    match payload:
        case dict() as mapping:
            return mapping
        case str() | int() | float() | bool() | list() | None:
            msg = f"Schema root is not an object: {path}"
            raise RuntimeError(msg)
        case unreachable:
            assert_never(unreachable)


def validation_issues(rows: list[JsonObject], schema: JsonObject) -> list[ValidationIssue]:
    validator = Draft202012Validator(schema)
    issues: list[ValidationIssue] = []
    for row_index, row in enumerate(rows):
        for error in validator.iter_errors(row):
            path = ".".join(str(part) for part in error.absolute_path)
            issues.append(ValidationIssue(row_index, path, error.message))
    return issues


def coverage_summary(rows: list[JsonObject], issues: list[ValidationIssue]) -> JsonObject:
    invalid_rows = {issue.row_index for issue in issues}
    return {
        "rows": len(rows),
        "valid_rows": len(rows) - len(invalid_rows),
        "invalid_rows": len(invalid_rows),
        "schema_error_count": len(issues),
        "first_error": asdict(issues[0]) if issues else None,
        "domain_counts": dict(Counter(text_field(row, "domain") for row in rows).most_common()),
        "acoustic_condition_counts": dict(
            Counter(text_field(row, "acoustic_condition") for row in rows).most_common(),
        ),
        "critical_span_counts": dict(
            Counter(
                text_field(span, "category")
                for row in rows
                for span in list_of_mappings(row.get("critical_spans"))
            ).most_common(),
        ),
        "slot_name_counts": dict(
            Counter(
                text_field(slot, "name")
                for row in rows
                for slot in list_of_mappings(row.get("slots"))
            ).most_common(),
        ),
        "rows_with_audio_path": sum(1 for row in rows if text_field(row, "audio_path")),
        "gold_status": "candidate_only_until_human_review",
        "numpy_version": np.__version__,
    }


def write_markdown(summary: JsonObject, output_path: Path) -> None:
    lines = [
        "# Semantic Annotation Validation",
        "",
        f"- Rows: {summary['rows']}",
        f"- Valid rows: {summary['valid_rows']}",
        f"- Invalid rows: {summary['invalid_rows']}",
        f"- Schema errors: {summary['schema_error_count']}",
        f"- Rows with audio path: {summary['rows_with_audio_path']}",
        "",
        "This report contains counts only and no transcript text.",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_annotations(annotations_path: Path, schema_path: Path, output_dir: Path) -> None:
    rows = load_jsonl(annotations_path)
    summary = coverage_summary(rows, validation_issues(rows, load_schema(schema_path)))
    output_dir.mkdir(parents=True, exist_ok=True)
    _ = (output_dir / "validation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(summary, output_dir / "validation_summary.md")


@app.command()
def main(
    annotations_path: Annotated[Path, typer.Argument(help="Semantic annotation JSONL.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
    schema_path: Annotated[
        Path,
        typer.Option("--schema"),
    ] = Path("research/evaluation/semantic_critical_schema.json"),
) -> None:
    if not annotations_path.exists():
        console.print(f"Annotations file not found: {annotations_path}")
        raise typer.Exit(code=2)
    try:
        validate_annotations(annotations_path, schema_path, output_dir)
    except RuntimeError as error:
        console.print(str(error))
        raise typer.Exit(code=2) from error
    console.print(f"Wrote {output_dir}")


if __name__ == "__main__":
    app()
