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
#      uv run scripts/inspect_aihub_metadata.py data/fixtures/aihub_sample --output report.json
# 3. Or make executable and run:
#      chmod +x scripts/inspect_aihub_metadata.py && ./scripts/inspect_aihub_metadata.py data/fixtures/aihub_sample
# ──────────────────

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Annotated, Final, TypeAlias, assert_never

import numpy as np
import typer
from rich.console import Console

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

REGION_FIELDS: Final[tuple[str, ...]] = (
    "birthplace",
    "principal_residence",
    "current_residence",
)
DIALECT_FIELDS: Final[tuple[str, ...]] = (
    "dialect_form",
    "standard_form",
    "eojeolList",
)

app = typer.Typer(add_completion=False)
console = Console()


def normalize_json_value(value: JsonValue) -> JsonValue:
    match value:
        case dict() as mapping:
            normalized: dict[str, JsonValue] = {}
            for key, child in mapping.items():
                match key:
                    case str() as text_key:
                        normalized[text_key] = normalize_json_value(child)
                    case int() | float() | bool() | list() | dict() | None:
                        continue
                    case unreachable:
                        assert_never(unreachable)
            return normalized
        case list() as items:
            return [normalize_json_value(item) for item in items]
        case str() | int() | float() | bool() | None:
            return value
        case unreachable:
            assert_never(unreachable)


def load_json(path: Path) -> JsonValue:
    return normalize_json_value(json.loads(path.read_text(encoding="utf-8")))



def walk_objects(value: JsonValue) -> list[dict[str, JsonValue]]:
    match value:
        case dict() as mapping:
            children: list[dict[str, JsonValue]] = [mapping]
            for child in mapping.values():
                children.extend(walk_objects(child))
            return children
        case list() as items:
            children = []
            for item in items:
                children.extend(walk_objects(item))
            return children
        case str() | int() | float() | bool() | None:
            return []
        case unreachable:
            assert_never(unreachable)


def text_value(mapping: dict[str, JsonValue], key: str) -> str | None:
    match mapping.get(key):
        case str() as value:
            stripped = value.strip()
            return stripped if stripped else None
        case int() | float() | bool() | list() | dict() | None:
            return None
        case unreachable:
            assert_never(unreachable)


def json_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".json":
            files.append(path)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.json")))
    return sorted(set(files))


def summarize(paths: list[Path]) -> dict[str, JsonValue]:
    files = json_files(paths)
    region_counts: dict[str, Counter[str]] = {
        field: Counter() for field in REGION_FIELDS
    }
    field_counts: Counter[str] = Counter()
    speaker_ids: set[str] = set()
    utterance_ids: set[str] = set()
    dialect_eojeols = 0
    total_eojeols = 0

    for file_path in files:
        for mapping in walk_objects(load_json(file_path)):
            for field in REGION_FIELDS:
                value = text_value(mapping, field)
                if value is not None:
                    region_counts[field][value] += 1
            for field in DIALECT_FIELDS:
                if field in mapping:
                    field_counts[field] += 1
            speaker_id = text_value(mapping, "speaker_id") or text_value(mapping, "id")
            if speaker_id is not None and any(
                text_value(mapping, field) is not None for field in REGION_FIELDS
            ):
                speaker_ids.add(speaker_id)
            utterance_id = text_value(mapping, "id")
            if utterance_id is not None and (
                "dialect_form" in mapping or "standard_form" in mapping
            ):
                utterance_ids.add(utterance_id)
            if "isDialect" in mapping:
                total_eojeols += 1
                match mapping.get("isDialect"):
                    case True:
                        dialect_eojeols += 1
                    case False | str() | int() | float() | list() | dict() | None:
                        pass
                    case unreachable:
                        assert_never(unreachable)

    return {
        "numpy_version": np.__version__,
        "file_count": len(files),
        "speaker_count_with_region": len(speaker_ids),
        "utterance_count_with_transcript": len(utterance_ids),
        "region_counts": {
            field: dict(counter.most_common()) for field, counter in region_counts.items()
        },
        "field_counts": dict(field_counts.most_common()),
        "total_eojeols_seen": total_eojeols,
        "dialect_eojeols_seen": dialect_eojeols,
    }


@app.command()
def main(
    paths: Annotated[list[Path], typer.Argument(help="JSON file or directory paths.")],
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    summary = summarize(paths)
    rendered = json.dumps(summary, ensure_ascii=False, indent=2)
    if output is None:
        console.print(rendered)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(f"{rendered}\n", encoding="utf-8")
    console.print(f"Wrote {output}")


if __name__ == "__main__":
    app()
