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
#      uv run scripts/build_dialect_audio_review_packet.py research/experiments/runs/aihub_119_dialect_attribution_probe/dialect_asr_text_audit.local.jsonl research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl --output-dir research/experiments/runs/aihub_119_dialect_audio_review
# ──────────────────

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, TypeAlias, assert_never

import typer
from build_dialect_taxonomy import JsonValue, text_field
from rich.console import Console
from semantic_review_pack import stable_hash

JsonObject: TypeAlias = dict[str, JsonValue]

# Text-only audit statuses that a human must confirm against the audio.
AUDIO_REVIEW_STATUSES = (
    "potentially_harmful_semantic_shift",
    "low_impact_discourse_or_hedge_loss",
)

# Allowed values for the `reviewer_decision` column.
REVIEWER_DECISIONS = ("harmful", "acceptable", "artifact", "unclear")

app = typer.Typer(add_completion=False)
console = Console()


@dataclass(frozen=True, slots=True)
class ReviewUnit:
    audit_row: JsonObject
    manifest_row: JsonObject
    clip_row: JsonObject


def load_jsonl(path: Path) -> list[JsonObject]:
    rows: list[JsonObject] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
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


def int_field(mapping: JsonObject, key: str) -> int:
    match mapping.get(key):
        case bool():
            return 0
        case int() | float() as value:
            return int(value)
        case str() | list() | dict() | None:
            return 0
        case unreachable:
            assert_never(unreachable)


def numeric_text(mapping: JsonObject, key: str) -> str:
    match mapping.get(key):
        case bool():
            return ""
        case int() | float() as value:
            return f"{float(value):.2f}"
        case str() | list() | dict() | None:
            return ""
        case unreachable:
            assert_never(unreachable)


def string_list(value: JsonValue) -> list[str]:
    match value:
        case list() as items:
            return [item for item in items if isinstance(item, str)]
        case str() | int() | float() | bool() | dict() | None:
            return []
        case unreachable:
            assert_never(unreachable)


def select_units(
    audit_rows: list[JsonObject],
    manifest_rows: list[JsonObject],
    clip_rows: list[JsonObject],
) -> list[ReviewUnit]:
    manifest_by_id = row_index(manifest_rows)
    clip_by_id = row_index(clip_rows)
    selected = [row for row in audit_rows if text_field(row, "text_audit_status") in AUDIO_REVIEW_STATUSES]
    units: list[ReviewUnit] = []
    for row in selected:
        review_id = text_field(row, "review_id")
        if review_id not in manifest_by_id:
            msg = f"Audit row has no ASR input manifest entry: {review_id}"
            raise RuntimeError(msg)
        units.append(ReviewUnit(row, manifest_by_id[review_id], clip_by_id.get(review_id, {})))
    order = {status: index for index, status in enumerate(AUDIO_REVIEW_STATUSES)}
    return sorted(
        units,
        key=lambda unit: (
            order[text_field(unit.audit_row, "text_audit_status")],
            text_field(unit.audit_row, "review_id"),
            int_field(unit.audit_row, "unit_index"),
        ),
    )


def clip_path(unit: ReviewUnit) -> Path:
    return Path(text_field(unit.manifest_row, "clip_path"))


def tsv_row(unit: ReviewUnit) -> dict[str, str]:
    return {
        "review_id": text_field(unit.audit_row, "review_id"),
        "unit_index": str(int_field(unit.audit_row, "unit_index")),
        "utterance_id": text_field(unit.audit_row, "utterance_id"),
        "cohort": text_field(unit.audit_row, "cohort"),
        "category": text_field(unit.audit_row, "category"),
        "dialect_unit": text_field(unit.audit_row, "dialect"),
        "standard_unit": text_field(unit.audit_row, "standard"),
        "automatic_outcome": text_field(unit.audit_row, "automatic_outcome"),
        "text_audit_status": text_field(unit.audit_row, "text_audit_status"),
        "text_audit_reason": text_field(unit.audit_row, "text_audit_reason"),
        "text_audit_note": text_field(unit.audit_row, "text_audit_note"),
        "clip_path": str(clip_path(unit)),
        "clip_present": str(clip_path(unit).exists()),
        "start_sec": numeric_text(unit.clip_row, "start_sec"),
        "end_sec": numeric_text(unit.clip_row, "end_sec"),
        "clip_duration_sec": numeric_text(unit.clip_row, "clip_duration_sec"),
        "domain": text_field(unit.clip_row, "domain"),
        "intent": text_field(unit.clip_row, "intent"),
        "critical_categories": json.dumps(
            string_list(unit.clip_row.get("critical_categories")),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "dialect_transcript": text_field(unit.manifest_row, "dialect_transcript"),
        "standard_transcript": text_field(unit.manifest_row, "standard_transcript"),
        "asr_hypothesis": text_field(unit.audit_row, "hypothesis"),
        "reviewer_decision": "",
        "reviewer_confidence": "",
        "reviewer_notes": "",
    }


def queue_row(unit: ReviewUnit) -> JsonObject:
    row = tsv_row(unit)
    return {
        **row,
        "unit_index": int_field(unit.audit_row, "unit_index"),
        "clip_present": clip_path(unit).exists(),
        "critical_categories": string_list(unit.clip_row.get("critical_categories")),
        "allowed_reviewer_decisions": list(REVIEWER_DECISIONS),
        "review_status": "unreviewed",
    }


def manifest_row(unit: ReviewUnit) -> JsonObject:
    """Shareable row: metadata only, no transcript text and no dialect surface forms."""
    utterance_id = text_field(unit.audit_row, "utterance_id")
    return {
        "review_id": text_field(unit.audit_row, "review_id"),
        "unit_index": int_field(unit.audit_row, "unit_index"),
        "utterance_hash": stable_hash(f"{utterance_id}:{int_field(unit.audit_row, 'unit_index')}"),
        "cohort": text_field(unit.audit_row, "cohort"),
        "category": text_field(unit.audit_row, "category"),
        "automatic_outcome": text_field(unit.audit_row, "automatic_outcome"),
        "text_audit_status": text_field(unit.audit_row, "text_audit_status"),
        "text_audit_reason": text_field(unit.audit_row, "text_audit_reason"),
        "domain": text_field(unit.clip_row, "domain"),
        "intent": text_field(unit.clip_row, "intent"),
        "critical_categories": string_list(unit.clip_row.get("critical_categories")),
        "clip_duration_sec": numeric_text(unit.clip_row, "clip_duration_sec"),
        "clip_present": clip_path(unit).exists(),
        "review_status": "unreviewed",
    }


def summary(units: list[ReviewUnit], audit_rows: list[JsonObject]) -> JsonObject:
    status_counts = Counter(text_field(unit.audit_row, "text_audit_status") for unit in units)
    return {
        "packet_type": "human_audio_review_of_text_audit_candidates",
        "audited_units_total": len(audit_rows),
        "review_units": len(units),
        "status_counts": dict(status_counts.most_common()),
        "cohort_counts": dict(Counter(text_field(unit.audit_row, "cohort") for unit in units).most_common()),
        "category_counts": dict(Counter(text_field(unit.audit_row, "category") for unit in units).most_common()),
        "utterance_counts": len({text_field(unit.audit_row, "review_id") for unit in units}),
        "clips_present": sum(1 for unit in units if clip_path(unit).exists()),
        "clips_missing": sum(1 for unit in units if not clip_path(unit).exists()),
        "allowed_reviewer_decisions": list(REVIEWER_DECISIONS),
        "review_status": "unreviewed",
        "gold_status": "not_gold_until_human_audio_review_completed",
    }


def write_tsv(units: list[ReviewUnit], path: Path) -> None:
    fieldnames = list(tsv_row(units[0]).keys()) if units else []
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for unit in units:
            writer.writerow(tsv_row(unit))


def write_jsonl(rows: list[JsonObject], path: Path) -> None:
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            _ = file.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_readme(output_dir: Path, report: JsonObject) -> None:
    status_counts = report["status_counts"]
    harmful = status_counts["potentially_harmful_semantic_shift"] if isinstance(status_counts, dict) else 0
    low_impact = status_counts["low_impact_discourse_or_hedge_loss"] if isinstance(status_counts, dict) else 0
    text = (
        "# Dialect ASR Audio Review Packet\n\n"
        "Human/audio confirmation of the text-only semantic audit. Text-only audit is not gold; "
        "a dialect unit is only counted as an AICC-harmful ASR failure after a reviewer has heard the clip.\n\n"
        "## Scope\n\n"
        f"- Audited dialect units in the pilot: {report['audited_units_total']}\n"
        f"- Units in this packet: {report['review_units']}\n"
        f"- `potentially_harmful_semantic_shift`: {harmful}\n"
        f"- `low_impact_discourse_or_hedge_loss`: {low_impact}\n"
        f"- Distinct utterances: {report['utterance_counts']}\n"
        f"- Clips present: {report['clips_present']}, missing: {report['clips_missing']}\n\n"
        "`meaning_preserved_or_acceptable_normalization` units are excluded on purpose. They are the audit's "
        "low-risk bulk and would dominate reviewer time without changing the harmful-case count.\n\n"
        "## Files\n\n"
        "- `dialect_audio_review_sheet.local.tsv`: reviewer sheet, restricted, git-ignored.\n"
        "- `dialect_audio_review_queue.local.jsonl`: same rows as JSONL, restricted, git-ignored.\n"
        "- `dialect_audio_review_manifest.jsonl`: shareable metadata only, no transcript text and no dialect surface forms.\n"
        "- `summary.json`: shareable counts.\n\n"
        "## Reviewer Protocol\n\n"
        "1. Play `clip_path` before reading `asr_hypothesis`, so the decision is anchored on audio.\n"
        "2. Compare `dialect_unit` against what the ASR hypothesis says at that position.\n"
        "3. Fill `reviewer_decision` with exactly one of:\n"
        "   - `harmful`: the ASR output changes AICC-relevant meaning (negation, amount, date/time, entity, intent cue, slot).\n"
        "   - `acceptable`: meaning survives; the difference is spelling, register, or a harmless normalization.\n"
        "   - `artifact`: the reference label, the clip window, or the audio itself is at fault, not the ASR system.\n"
        "   - `unclear`: audio is not decidable; do not guess.\n"
        "4. Fill `reviewer_confidence` with `high`, `medium`, or `low`.\n"
        "5. Use `reviewer_notes` for the AICC field at risk when the decision is `harmful`.\n\n"
        "Leave a row blank rather than guessing. Blank rows stay `unreviewed` and are excluded from any harmful-case count.\n\n"
        "## After Review\n\n"
        "Summarize confirmed `harmful` units, then decide whether to freeze pilot semantic annotations. "
        "Until then, the paper-safe claim stays at the text-audit level: many dialect surface mismatches are "
        "acceptable normalizations, so AICC evaluation must isolate harmful semantic shifts rather than treat "
        "every dialect-surface mismatch as task failure.\n"
    )
    (output_dir / "README.md").write_text(text, encoding="utf-8")


def write_outputs(units: list[ReviewUnit], audit_rows: list[JsonObject], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(units, output_dir / "dialect_audio_review_sheet.local.tsv")
    write_jsonl([queue_row(unit) for unit in units], output_dir / "dialect_audio_review_queue.local.jsonl")
    write_jsonl([manifest_row(unit) for unit in units], output_dir / "dialect_audio_review_manifest.jsonl")
    report = summary(units, audit_rows)
    (output_dir / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_readme(output_dir, report)


@app.command()
def main(
    text_audit_path: Annotated[Path, typer.Argument(help="Dialect ASR text audit local JSONL.")],
    asr_input_manifest_path: Annotated[Path, typer.Argument(help="ASR input manifest local JSONL.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
    review_manifest_path: Annotated[Path, typer.Option("--review-manifest")] = Path(
        "research/experiments/runs/aihub_119_pilot_review_packet/pilot_review_manifest.jsonl",
    ),
) -> None:
    for path in (text_audit_path, asr_input_manifest_path):
        if not path.exists():
            console.print(f"Input not found: {path}")
            raise typer.Exit(code=2)
    clip_rows = load_jsonl(review_manifest_path) if review_manifest_path.exists() else []
    if not clip_rows:
        console.print(f"Review manifest not found, clip timing columns will be empty: {review_manifest_path}")
    audit_rows = load_jsonl(text_audit_path)
    units = select_units(audit_rows, load_jsonl(asr_input_manifest_path), clip_rows)
    if not units:
        console.print("No units require audio review; nothing written.")
        raise typer.Exit(code=1)
    write_outputs(units, audit_rows, output_dir)
    console.print(f"Wrote {len(units)} review units to {output_dir}")


if __name__ == "__main__":
    app()
