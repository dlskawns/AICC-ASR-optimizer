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
#      uv run scripts/analyze_dialect_asr_errors.py research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_medium.local.jsonl --output-dir research/experiments/runs/aihub_119_dialect_attribution_probe
# 3. Or make executable and run:
#      chmod +x scripts/analyze_dialect_asr_errors.py && ./scripts/analyze_dialect_asr_errors.py MANIFEST.local.jsonl ASR.local.jsonl --output-dir OUTPUT_DIR
# ──────────────────

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Final, Literal, TypeAlias

import numpy as np
import typer
from build_dialect_taxonomy import JsonValue, list_of_mappings, text_field
from rich.console import Console
from run_dialect_attribution_probe import carries, load_jsonl, write_jsonl

JsonObject: TypeAlias = dict[str, JsonValue]
DialectOutcome: TypeAlias = Literal["surface_preserved", "standard_normalized", "missing_or_substituted"]
PlainOutcome: TypeAlias = Literal["standard_preserved", "plain_error"]

SUMMARY_NAME: Final[str] = "dialect_asr_error_analysis_summary.json"
LOCAL_CASES_NAME: Final[str] = "dialect_asr_error_cases.local.jsonl"
SHAREABLE_CASES_NAME: Final[str] = "dialect_asr_error_manifest.jsonl"

app = typer.Typer(add_completion=False)
console = Console()


@dataclass(frozen=True, slots=True)
class ErrorTable:
    dialect_error: int
    dialect_ok: int
    plain_error: int
    plain_ok: int


def asr_index(path: Path) -> dict[str, JsonObject]:
    indexed: dict[str, JsonObject] = {}
    for row in load_jsonl(path):
        review_id = text_field(row, "review_id")
        utterance_id = text_field(row, "utterance_id")
        if review_id:
            indexed[review_id] = row
        if utterance_id:
            indexed[utterance_id] = row
    return indexed


def dialect_outcome(unit: JsonObject, hypothesis: str) -> DialectOutcome:
    if carries(hypothesis, text_field(unit, "dialect")):
        return "surface_preserved"
    if carries(hypothesis, text_field(unit, "standard")):
        return "standard_normalized"
    return "missing_or_substituted"


def plain_outcome(unit: JsonObject, hypothesis: str) -> PlainOutcome:
    if carries(hypothesis, text_field(unit, "standard")):
        return "standard_preserved"
    return "plain_error"


def dialect_unit_records(row: JsonObject, hypothesis: str) -> list[JsonObject]:
    records: list[JsonObject] = []
    for unit in list_of_mappings(row.get("dialect_units")):
        outcome = dialect_outcome(unit, hypothesis)
        records.append(
            {
                "dialect": text_field(unit, "dialect"),
                "standard": text_field(unit, "standard"),
                "category": text_field(unit, "category"),
                "outcome": outcome,
            },
        )
    return records


def plain_unit_records(row: JsonObject, hypothesis: str) -> list[JsonObject]:
    records: list[JsonObject] = []
    for unit in list_of_mappings(row.get("plain_units")):
        records.append(
            {
                "standard": text_field(unit, "standard"),
                "outcome": plain_outcome(unit, hypothesis),
            },
        )
    return records


def update_dialect_counts(counters: Counter[str], row: JsonObject, records: list[JsonObject]) -> None:
    cohort = text_field(row, "cohort")
    for record in records:
        outcome = text_field(record, "outcome")
        category = text_field(record, "category")
        counters["dialect_total"] += 1
        counters[f"dialect:{outcome}"] += 1
        counters[f"cohort:{cohort}:dialect:{outcome}"] += 1
        counters[f"category:{category}:dialect:{outcome}"] += 1


def update_plain_counts(counters: Counter[str], row: JsonObject, records: list[JsonObject]) -> None:
    cohort = text_field(row, "cohort")
    for record in records:
        outcome = text_field(record, "outcome")
        counters["plain_total"] += 1
        counters[f"plain:{outcome}"] += 1
        counters[f"cohort:{cohort}:plain:{outcome}"] += 1


def case_row(row: JsonObject, output: JsonObject) -> JsonObject:
    hypothesis = text_field(output, "hypothesis")
    dialect_records = dialect_unit_records(row, hypothesis)
    plain_records = plain_unit_records(row, hypothesis)
    return {
        "review_id": text_field(row, "review_id"),
        "utterance_id": text_field(row, "utterance_id"),
        "cohort": text_field(row, "cohort"),
        "clip_path": text_field(row, "clip_path"),
        "model": text_field(output, "model"),
        "hypothesis": hypothesis,
        "dialect_transcript": text_field(row, "dialect_transcript"),
        "standard_transcript": text_field(row, "standard_transcript"),
        "dialect_unit_outcomes": dialect_records,
        "plain_unit_outcomes": [record for record in plain_records if text_field(record, "outcome") == "plain_error"],
    }


def shareable_case(row: JsonObject) -> JsonObject:
    dialect_counts = Counter(text_field(unit, "outcome") for unit in list_of_mappings(row.get("dialect_unit_outcomes")))
    plain_error_count = len(list_of_mappings(row.get("plain_unit_outcomes")))
    return {
        "review_id": text_field(row, "review_id"),
        "utterance_id": text_field(row, "utterance_id"),
        "cohort": text_field(row, "cohort"),
        "model": text_field(row, "model"),
        "dialect_outcome_counts": dict(dialect_counts.most_common()),
        "plain_error_count": plain_error_count,
    }


def ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def odds_ratio(table: ErrorTable) -> float:
    if table.dialect_ok == 0 or table.plain_error == 0:
        return 0.0
    return (table.dialect_error * table.plain_ok) / (table.dialect_ok * table.plain_error)


def odds_ratio_ci95(table: ErrorTable) -> JsonObject:
    if min(table.dialect_error, table.dialect_ok, table.plain_error, table.plain_ok) == 0:
        return {"low": 0.0, "high": 0.0}
    log_or = math.log(odds_ratio(table))
    se = math.sqrt(
        (1 / table.dialect_error)
        + (1 / table.dialect_ok)
        + (1 / table.plain_error)
        + (1 / table.plain_ok),
    )
    return {"low": math.exp(log_or - (1.96 * se)), "high": math.exp(log_or + (1.96 * se))}


def two_proportion_z(table: ErrorTable) -> float:
    dialect_total = table.dialect_error + table.dialect_ok
    plain_total = table.plain_error + table.plain_ok
    pooled = (table.dialect_error + table.plain_error) / (dialect_total + plain_total)
    se = math.sqrt(pooled * (1 - pooled) * ((1 / dialect_total) + (1 / plain_total)))
    if se == 0:
        return 0.0
    return (ratio(table.dialect_error, dialect_total) - ratio(table.plain_error, plain_total)) / se


def two_sided_normal_p(z_score: float) -> float:
    return math.erfc(abs(z_score) / math.sqrt(2))


def build_summary(counters: Counter[str], evaluated: int, missing: int, model_counts: Counter[str]) -> JsonObject:
    dialect_errors = counters["dialect:missing_or_substituted"]
    dialect_total = counters["dialect_total"]
    plain_errors = counters["plain:plain_error"]
    plain_total = counters["plain_total"]
    dialect_error_rate = ratio(dialect_errors, dialect_total)
    plain_error_rate = ratio(plain_errors, plain_total)
    error_table = ErrorTable(
        dialect_error=dialect_errors,
        dialect_ok=dialect_total - dialect_errors,
        plain_error=plain_errors,
        plain_ok=plain_total - plain_errors,
    )
    z_score = two_proportion_z(error_table)
    return {
        "evaluated_utterances": evaluated,
        "missing_asr_outputs": missing,
        "dialect_units": dialect_total,
        "plain_units": plain_total,
        "dialect_surface_preservation_rate": ratio(counters["dialect:surface_preserved"], dialect_total),
        "dialect_standard_normalization_rate": ratio(counters["dialect:standard_normalized"], dialect_total),
        "dialect_unit_error_rate": dialect_error_rate,
        "plain_unit_error_rate": plain_error_rate,
        "dialect_plain_error_rate_difference": dialect_error_rate - plain_error_rate,
        "dialect_to_plain_error_rate_ratio": ratio(round(dialect_error_rate * 1_000_000), round(plain_error_rate * 1_000_000)),
        "dialect_plain_odds_ratio": odds_ratio(error_table),
        "dialect_plain_odds_ratio_ci95": odds_ratio_ci95(error_table),
        "dialect_plain_two_proportion_z": z_score,
        "dialect_plain_two_sided_p_approx": two_sided_normal_p(z_score),
        "model_counts": dict(model_counts.most_common()),
        "outcome_counts": dict(counters.most_common()),
        "numpy_version": np.__version__,
    }


def analyze(manifest_rows: list[JsonObject], outputs: dict[str, JsonObject]) -> tuple[list[JsonObject], JsonObject]:
    counters: Counter[str] = Counter()
    model_counts: Counter[str] = Counter()
    cases: list[JsonObject] = []
    missing = 0
    for row in manifest_rows:
        output = outputs.get(text_field(row, "review_id")) or outputs.get(text_field(row, "utterance_id"))
        if output is None:
            missing += 1
            continue
        record = case_row(row, output)
        update_dialect_counts(counters, row, list_of_mappings(record.get("dialect_unit_outcomes")))
        update_plain_counts(counters, row, plain_unit_records(row, text_field(output, "hypothesis")))
        model_counts[text_field(output, "model")] += 1
        cases.append(record)
    return cases, build_summary(counters, len(cases), missing, model_counts)


@app.command()
def main(
    manifest_path: Annotated[Path, typer.Argument(help="Local dialect attribution ASR input manifest.")],
    asr_path: Annotated[Path, typer.Argument(help="Local ASR outputs JSONL.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
) -> None:
    if not manifest_path.exists():
        console.print(f"Manifest not found: {manifest_path}")
        raise typer.Exit(code=2)
    if not asr_path.exists():
        console.print(f"ASR output not found: {asr_path}")
        raise typer.Exit(code=2)
    output_dir.mkdir(parents=True, exist_ok=True)
    cases, summary = analyze(load_jsonl(manifest_path), asr_index(asr_path))
    write_jsonl(cases, output_dir / LOCAL_CASES_NAME)
    write_jsonl([shareable_case(row) for row in cases], output_dir / SHAREABLE_CASES_NAME)
    (output_dir / SUMMARY_NAME).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    console.print(f"Wrote {output_dir / SUMMARY_NAME}")


if __name__ == "__main__":
    app()
