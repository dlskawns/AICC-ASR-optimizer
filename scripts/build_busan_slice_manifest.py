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
#      uv run scripts/build_busan_slice_manifest.py data/raw/aihub_gyeongsang_119 --output-dir research/experiments/runs/aihub_119_busan_slice
# 3. Or make executable and run:
#      chmod +x scripts/build_busan_slice_manifest.py && ./scripts/build_busan_slice_manifest.py data/raw/aihub_gyeongsang_119 --output-dir research/experiments/runs/aihub_119_busan_slice
# ──────────────────

from __future__ import annotations

import gzip
import json
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Final, Literal, TypeAlias, assert_never

import numpy as np
import typer
from rich.console import Console

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
RegionField: TypeAlias = Literal["birthplace", "principal_residence", "current_residence"]
SliceLabel: TypeAlias = Literal[
    "busan_strict", "busan_residence", "busan_any", "gyeongsang_other", "other"
]

BUSAN: Final[str] = "부산"
GYEONGSANG_REGIONS: Final[frozenset[str]] = frozenset((BUSAN, "대구", "울산", "경북", "경남"))
REGION_FIELDS: Final[tuple[RegionField, ...]] = ("birthplace", "principal_residence", "current_residence")
SLICE_DESCRIPTIONS: Final[tuple[tuple[SliceLabel, str], ...]] = (
    ("busan_strict", "birthplace, principal residence, and current residence are 부산."),
    ("busan_residence", "principal residence or current residence is 부산."),
    ("busan_any", "birthplace is 부산, but the residence rule did not match."),
    ("gyeongsang_other", "대구/울산/경북/경남 appears, with no Busan rule match."),
    ("other", "no Gyeongsang-region rule match."),
)

app = typer.Typer(add_completion=False)
console = Console()


@dataclass(frozen=True, slots=True)
class EntryParts:
    source_file: str
    metadata: dict[str, JsonValue]
    speaker: dict[str, JsonValue]
    utterance: dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class SummaryCounters:
    slice_counts: Counter[str]
    dialect_eojeol_counts: Counter[str]
    utterance_counts_with_dialect_eojeol: Counter[str]
    topic_counts_by_slice: dict[str, Counter[str]]


@dataclass(frozen=True, slots=True)
class SummaryReport:
    source_zips: list[str]
    manifest_rows: int
    counters: SummaryCounters


def text_field(mapping: dict[str, JsonValue], key: str) -> str:
    match mapping.get(key):
        case str() as value:
            return value.strip()
        case int() | float() | bool() | list() | dict() | None:
            return ""
        case unreachable:
            assert_never(unreachable)


def int_field(mapping: dict[str, JsonValue], key: str) -> int:
    match mapping.get(key):
        case bool():
            return 0
        case int() as value:
            return value
        case str() | float() | list() | dict() | None:
            return 0
        case unreachable:
            assert_never(unreachable)


def bool_field(mapping: dict[str, JsonValue], key: str) -> bool:
    match mapping.get(key):
        case bool() as value:
            return value
        case str() | int() | float() | list() | dict() | None:
            return False
        case unreachable:
            assert_never(unreachable)


def list_of_mappings(value: JsonValue) -> list[dict[str, JsonValue]]:
    match value:
        case list() as items:
            mappings: list[dict[str, JsonValue]] = []
            for item in items:
                match item:
                    case dict() as mapping:
                        mappings.append(mapping)
                    case str() | int() | float() | bool() | list() | None:
                        continue
                    case unreachable:
                        assert_never(unreachable)
            return mappings
        case str() | int() | float() | bool() | dict() | None:
            return []
        case unreachable:
            assert_never(unreachable)


def source_zips(path: Path) -> list[Path]:
    if path.is_file() and path.suffix == ".zip":
        return [path]
    if path.is_dir():
        return sorted(path.rglob("*.zip"))
    return []


def slice_label(speaker: dict[str, JsonValue]) -> SliceLabel:
    regions = {field: text_field(speaker, field) for field in REGION_FIELDS}
    birth = regions["birthplace"]
    principal = regions["principal_residence"]
    current = regions["current_residence"]

    if birth == BUSAN and principal == BUSAN and current == BUSAN:
        return "busan_strict"
    if principal == BUSAN or current == BUSAN:
        return "busan_residence"
    if birth == BUSAN:
        return "busan_any"
    if any(region in GYEONGSANG_REGIONS for region in regions.values()):
        return "gyeongsang_other"
    return "other"


def dialect_eojeol_count(utterance: dict[str, JsonValue]) -> tuple[int, int]:
    eojeols = list_of_mappings(utterance.get("eojeolList"))
    dialect_count = 0
    for eojeol in eojeols:
        match eojeol.get("isDialect"):
            case True:
                dialect_count += 1
            case False | str() | int() | float() | list() | dict() | None:
                continue
            case unreachable:
                assert_never(unreachable)
    return dialect_count, len(eojeols)


def region_entry(parts: EntryParts) -> dict[str, JsonValue]:
    dialect_count, eojeol_count = dialect_eojeol_count(parts.utterance)
    dialect_form = text_field(parts.utterance, "dialect_form")
    standard_form = text_field(parts.utterance, "standard_form")

    return {
        "source_file": parts.source_file,
        "utterance_id": text_field(parts.utterance, "id"),
        "speaker_local_id": text_field(parts.speaker, "id"),
        "slice_label": slice_label(parts.speaker),
        "birthplace": text_field(parts.speaker, "birthplace"),
        "principal_residence": text_field(parts.speaker, "principal_residence"),
        "current_residence": text_field(parts.speaker, "current_residence"),
        "age": text_field(parts.speaker, "age"),
        "sex": text_field(parts.speaker, "sex"),
        "topic": text_field(parts.metadata, "topic"),
        "dialect_form_char_length": len(dialect_form),
        "standard_form_char_length": len(standard_form),
        "dialect_eojeol_count": dialect_count,
        "eojeol_count": eojeol_count,
        "has_dialect_eojeol": dialect_count > 0,
    }


def update_summary(counters: SummaryCounters, entry: dict[str, JsonValue]) -> None:
    label = text_field(entry, "slice_label")
    counters.slice_counts[label] += 1
    counters.dialect_eojeol_counts[label] += int_field(entry, "dialect_eojeol_count")
    if bool_field(entry, "has_dialect_eojeol"):
        counters.utterance_counts_with_dialect_eojeol[label] += 1
    topic = text_field(entry, "topic")
    if topic:
        counters.topic_counts_by_slice.setdefault(label, Counter())[topic] += 1


def load_payload(archive: zipfile.ZipFile, name: str) -> dict[str, JsonValue]:
    payload = json.loads(archive.read(name).decode("utf-8"))
    match payload:
        case dict() as mapping:
            return mapping
        case str() | int() | float() | bool() | list() | None:
            msg = f"JSON root is not an object: {name}"
            raise RuntimeError(msg)
        case unreachable:
            assert_never(unreachable)


def summary_json(report: SummaryReport) -> dict[str, JsonValue]:
    return {
        "source_zip_count": len(report.source_zips),
        "source_zips": report.source_zips,
        "manifest_rows": report.manifest_rows,
        "slice_counts": dict(report.counters.slice_counts.most_common()),
        "dialect_eojeol_counts": dict(report.counters.dialect_eojeol_counts.most_common()),
        "utterance_counts_with_dialect_eojeol": dict(
            report.counters.utterance_counts_with_dialect_eojeol.most_common(),
        ),
        "topic_counts_by_slice": {
            label: dict(counter.most_common())
            for label, counter in report.counters.topic_counts_by_slice.items()
        },
        "numpy_version": np.__version__,
    }


def write_markdown(report: SummaryReport, output_path: Path) -> None:
    labels = sorted(report.counters.slice_counts)
    lines = [
        "# Busan Slice Manifest Summary",
        "",
        f"- Source zip count: {len(report.source_zips)}",
        f"- Manifest rows: {report.manifest_rows}",
        "",
        "## Slice Counts",
        "",
        "| slice_label | utterances | dialect_eojeols |",
        "|---|---:|---:|",
    ]
    for label in labels:
        lines.append(
            f"| {label} | {report.counters.slice_counts[label]} | "
            f"{report.counters.dialect_eojeol_counts[label]} |",
        )
    lines.extend(("", "## Slice Definitions", ""))
    lines.extend(f"- `{label}`: {description}" for label, description in SLICE_DESCRIPTIONS)
    lines.extend(("", "Manifest rows exclude utterance text."))
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@app.command()
def main(
    input_path: Annotated[Path, typer.Argument(help="AI-Hub label zip or directory.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
) -> None:
    zips = source_zips(input_path)
    if not zips:
        console.print(f"No zip files found under {input_path}")
        raise typer.Exit(code=2)

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.jsonl.gz"
    summary_path = output_dir / "summary.json"
    markdown_path = output_dir / "summary.md"
    rows = 0
    counters = SummaryCounters(Counter(), Counter(), Counter(), {})

    with gzip.open(manifest_path, "wt", encoding="utf-8") as manifest:
        for zip_path in zips:
            with zipfile.ZipFile(zip_path) as archive:
                json_names = sorted(name for name in archive.namelist() if name.endswith(".json"))
                for name in json_names:
                    payload = load_payload(archive, name)
                    metadata = payload.get("metadata")
                    speakers = {
                        text_field(speaker, "id"): speaker
                        for speaker in list_of_mappings(payload.get("speaker"))
                    }
                    for utterance in list_of_mappings(payload.get("utterance")):
                        speaker = speakers.get(text_field(utterance, "speaker_id"))
                        if speaker is None:
                            continue
                        metadata_map = metadata if isinstance(metadata, dict) else {}
                        parts = EntryParts(name, metadata_map, speaker, utterance)
                        entry = region_entry(parts)
                        _ = manifest.write(json.dumps(entry, ensure_ascii=False) + "\n")
                        rows += 1
                        update_summary(counters, entry)

    report = SummaryReport([str(path) for path in zips], rows, counters)
    _ = summary_path.write_text(
        json.dumps(summary_json(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, markdown_path)
    console.print(f"Wrote {manifest_path}")
    console.print(f"Wrote {summary_path}")
    console.print(f"Wrote {markdown_path}")


if __name__ == "__main__":
    app()
