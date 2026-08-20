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
#      uv run scripts/run_dialect_attribution_probe.py research/experiments/runs/aihub_119_pilot_review_packet/pilot_review_manifest.jsonl --output-dir research/experiments/runs/aihub_119_dialect_attribution_probe
# 3. Or make executable and run:
#      chmod +x scripts/run_dialect_attribution_probe.py && ./scripts/run_dialect_attribution_probe.py research/experiments/runs/aihub_119_pilot_review_packet/pilot_review_manifest.jsonl --output-dir research/experiments/runs/aihub_119_dialect_attribution_probe
# ──────────────────

from __future__ import annotations

import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Annotated, TypeAlias, assert_never

import numpy as np
import typer
from build_dialect_taxonomy import (
    JsonValue,
    Pair,
    classify_pair,
    list_of_mappings,
    text_field,
)
from rich.console import Console
from semantic_review_pack import stable_hash

JsonObject: TypeAlias = dict[str, JsonValue]
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


def label_index(label_root: Path) -> dict[str, tuple[Path, str]]:
    members: dict[str, tuple[Path, str]] = {}
    zip_paths = [label_root] if label_root.is_file() and label_root.suffix == ".zip" else sorted(label_root.rglob("*.zip"))
    for zip_path in zip_paths:
        with zipfile.ZipFile(zip_path) as archive:
            for name in archive.namelist():
                if name.endswith(".json"):
                    members[Path(name).name] = (zip_path, name)
    return members


def payload_for(index: dict[str, tuple[Path, str]], source_file: str) -> JsonObject:
    zip_path, member = index[source_file]
    with zipfile.ZipFile(zip_path) as archive:
        payload = json.loads(archive.read(member).decode("utf-8"))
    match payload:
        case dict() as mapping:
            return mapping
        case str() | int() | float() | bool() | list() | None:
            msg = f"Label JSON root is not object: {source_file}"
            raise RuntimeError(msg)
        case unreachable:
            assert_never(unreachable)


def target_utterance(payload: JsonObject, utterance_id: str) -> JsonObject:
    for utterance in list_of_mappings(payload.get("utterance")):
        if text_field(utterance, "id") == utterance_id:
            return utterance
    msg = f"Utterance not found: {utterance_id}"
    raise RuntimeError(msg)


def normalized(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", text)


def contains(hypothesis: str, value: str) -> bool:
    needle = normalized(value)
    return bool(needle) and needle in normalized(hypothesis)


def analysis_units(row: JsonObject, utterance: JsonObject, clip_dir: Path) -> JsonObject:
    dialect_units: list[JsonObject] = []
    plain_units: list[JsonObject] = []
    for eojeol in list_of_mappings(utterance.get("eojeolList")):
        standard = text_field(eojeol, "standard")
        dialect = text_field(eojeol, "eojeol")
        unit = {
            "dialect": dialect,
            "standard": standard,
            "category": classify_pair(Pair(standard, dialect)),
        }
        if eojeol.get("isDialect") is True:
            dialect_units.append(unit)
        else:
            plain_units.append(unit)
    return {
        "review_id": text_field(row, "review_id"),
        "source_file": text_field(row, "source_file"),
        "utterance_id": text_field(row, "utterance_id"),
        "cohort": text_field(row, "cohort"),
        "clip_path": str(clip_dir / f"{text_field(row, 'review_id')}.wav"),
        "dialect_transcript": text_field(utterance, "dialect_form"),
        "standard_transcript": text_field(utterance, "standard_form"),
        "dialect_units": dialect_units,
        "plain_units": plain_units,
        "utterance_hash": stable_hash(f"{text_field(row, 'source_file')}:{text_field(row, 'utterance_id')}"),
    }


def build_manifest(rows: list[JsonObject], label_root: Path, clip_dir: Path) -> list[JsonObject]:
    index = label_index(label_root)
    return [
        analysis_units(row, target_utterance(payload_for(index, text_field(row, "source_file")), text_field(row, "utterance_id")), clip_dir)
        for row in rows
    ]


def asr_index(path: Path) -> dict[str, JsonObject]:
    indexed: dict[str, JsonObject] = {}
    for row in load_jsonl(path):
        key = text_field(row, "review_id") or text_field(row, "utterance_id")
        indexed[key] = row
    return indexed


def update_counts(counters: Counter[str], manifest: JsonObject, hypothesis: str) -> None:
    cohort = text_field(manifest, "cohort")
    dialect_units = list_of_mappings(manifest.get("dialect_units"))
    counters[f"{cohort}:utterances"] += 1
    for unit in dialect_units:
        category = text_field(unit, "category")
        dialect = text_field(unit, "dialect")
        standard = text_field(unit, "standard")
        counters[f"{cohort}:dialect_total"] += 1
        counters[f"category:{category}:total"] += 1
        if contains(hypothesis, dialect):
            counters[f"{cohort}:dialect_surface_preserved"] += 1
            continue
        if contains(hypothesis, standard):
            counters[f"{cohort}:dialect_standard_normalized"] += 1
            continue
        counters[f"{cohort}:dialect_error"] += 1
        counters[f"category:{category}:error"] += 1
    for unit in list_of_mappings(manifest.get("plain_units")):
        standard = text_field(unit, "standard")
        counters[f"{cohort}:plain_total"] += 1
        if not contains(hypothesis, standard):
            counters[f"{cohort}:plain_error"] += 1


def evaluate(manifest_rows: list[JsonObject], asr_path: Path) -> JsonObject:
    outputs = asr_index(asr_path)
    counters: Counter[str] = Counter()
    missing = 0
    for row in manifest_rows:
        output = outputs.get(text_field(row, "review_id")) or outputs.get(text_field(row, "utterance_id"))
        if output is None:
            missing += 1
            continue
        update_counts(counters, row, text_field(output, "hypothesis"))
    dialect_total = counters["busan:dialect_total"] + counters["gyeongsang_other:dialect_total"]
    dialect_error = counters["busan:dialect_error"] + counters["gyeongsang_other:dialect_error"]
    dialect_surface = counters["busan:dialect_surface_preserved"] + counters["gyeongsang_other:dialect_surface_preserved"]
    plain_total = counters["busan:plain_total"] + counters["gyeongsang_other:plain_total"]
    plain_error = counters["busan:plain_error"] + counters["gyeongsang_other:plain_error"]
    return {
        "evaluated_utterances": counters["busan:utterances"] + counters["gyeongsang_other:utterances"],
        "missing_asr_outputs": missing,
        "dialect_unit_error_rate": dialect_error / dialect_total if dialect_total else 0.0,
        "dialect_surface_change_rate": 1 - (dialect_surface / dialect_total) if dialect_total else 0.0,
        "plain_unit_error_rate": plain_error / plain_total if plain_total else 0.0,
        "attribution_counts": dict(counters.most_common()),
        "problem_definition_status": "asr_outputs_evaluated",
    }


def write_jsonl(rows: list[JsonObject], path: Path) -> None:
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            _ = file.write(json.dumps(row, ensure_ascii=False) + "\n")


def shareable_rows(rows: list[JsonObject]) -> list[JsonObject]:
    return [
        {
            "review_id": text_field(row, "review_id"),
            "utterance_hash": text_field(row, "utterance_hash"),
            "cohort": text_field(row, "cohort"),
            "dialect_unit_count": len(list_of_mappings(row.get("dialect_units"))),
            "plain_unit_count": len(list_of_mappings(row.get("plain_units"))),
        }
        for row in rows
    ]


def write_readme(output_dir: Path, summary: JsonObject) -> None:
    text = (
        "# Dialect Attribution Probe\n\n"
        f"- Manifest rows: {summary['manifest_rows']}\n"
        f"- Dialect units: {summary['dialect_units']}\n"
        f"- Plain units: {summary['plain_units']}\n"
        f"- Status: `{summary['problem_definition_status']}`\n\n"
        "This probe tests whether ASR errors concentrate on dialect-marked eojeols before making AICC claims.\n"
    )
    (output_dir / "README.md").write_text(text, encoding="utf-8")


def write_outputs(rows: list[JsonObject], output_dir: Path, asr_path: Path | None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(rows, output_dir / "asr_input_manifest.local.jsonl")
    write_jsonl(shareable_rows(rows), output_dir / "probe_manifest.jsonl")
    summary = {
        "manifest_rows": len(rows),
        "dialect_units": sum(len(list_of_mappings(row.get("dialect_units"))) for row in rows),
        "plain_units": sum(len(list_of_mappings(row.get("plain_units"))) for row in rows),
        "cohort_counts": dict(Counter(text_field(row, "cohort") for row in rows).most_common()),
        "problem_definition_status": "awaiting_asr_outputs",
        "numpy_version": np.__version__,
    }
    if asr_path is not None:
        summary.update(evaluate(rows, asr_path))
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_readme(output_dir, summary)


@app.command()
def main(
    pilot_manifest_path: Annotated[Path, typer.Argument(help="Pilot review manifest JSONL.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
    asr_path: Annotated[Path | None, typer.Option("--asr")] = None,
    label_root: Annotated[Path, typer.Option("--label-root")] = Path("data/raw/aihub_gyeongsang_119"),
    clip_dir: Annotated[Path, typer.Option("--clip-dir")] = Path("data/interim/aihub_119_pilot_clips"),
) -> None:
    if not pilot_manifest_path.exists():
        console.print(f"Pilot manifest not found: {pilot_manifest_path}")
        raise typer.Exit(code=2)
    if asr_path is not None and not asr_path.exists():
        console.print(f"ASR output not found: {asr_path}")
        raise typer.Exit(code=2)
    write_outputs(build_manifest(load_jsonl(pilot_manifest_path), label_root, clip_dir), output_dir, asr_path)
    console.print(f"Wrote {output_dir}")


if __name__ == "__main__":
    app()
