#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "numpy",
#     "pydantic",
#     "rich",
#     "typer",
# ]
# ///

# ─── How to run ───
# 1. Install uv (if not installed):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Run directly (no venv, no pip install needed):
#      uv run scripts/evaluate_semantic_critical.py GOLD.jsonl ASR.jsonl --output-dir runs/pilot
# 3. Or make executable and run:
#      chmod +x scripts/evaluate_semantic_critical.py && ./scripts/evaluate_semantic_critical.py GOLD.jsonl ASR.jsonl
# ──────────────────

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Final

import typer
from pydantic import BaseModel, ConfigDict
from rich.console import Console

app = typer.Typer(add_completion=False)
console = Console()


class Slot(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    value: str
    span_text: str | None = None


class CriticalSpan(BaseModel):
    model_config = ConfigDict(frozen=True)

    span_text: str
    category: str
    business_risk: str
    expected_asr_preservation: str | None = None


class GoldAnnotation(BaseModel):
    model_config = ConfigDict(frozen=True)

    utterance_id: str
    audio_path: str
    speaker_region: str | None = None
    speaker_age_band: str | None = None
    acoustic_condition: str
    dialect_transcript: str
    standard_transcript: str
    domain: str
    intent: str
    slots: tuple[Slot, ...] = ()
    critical_spans: tuple[CriticalSpan, ...]
    clarification_required: bool = False
    notes: str | None = None


class AsrOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    utterance_id: str
    model: str
    hypothesis: str
    intent_prediction: str
    slots: tuple[Slot, ...] = ()


@dataclass(slots=True)
class ModelStats:
    char_edits: int = 0
    char_total: int = 0
    word_edits: int = 0
    word_total: int = 0
    examples: int = 0
    intent_correct: int = 0
    slot_true_positive: int = 0
    slot_false_positive: int = 0
    slot_false_negative: int = 0
    critical_total: Counter[str] = field(default_factory=Counter)
    critical_errors: Counter[str] = field(default_factory=Counter)


def levenshtein(left: list[str], right: list[str]) -> int:
    previous = list(range(len(right) + 1))
    for left_index, left_item in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_item in enumerate(right, start=1):
            substitution_cost = 0 if left_item == right_item else 1
            current.append(
                min(
                    previous[right_index] + 1,
                    current[right_index - 1] + 1,
                    previous[right_index - 1] + substitution_cost,
                )
            )
        previous = current
    return previous[-1]


def chars(text: str) -> list[str]:
    return [char for char in text if not char.isspace()]


def words(text: str) -> list[str]:
    return text.split()


def slot_pairs(slots: tuple[Slot, ...]) -> set[tuple[str, str]]:
    return {(slot.name, slot.value) for slot in slots}


def read_gold(path: Path) -> dict[str, GoldAnnotation]:
    records: dict[str, GoldAnnotation] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        record = GoldAnnotation.model_validate_json(line)
        records[record.utterance_id] = record
    return records


def read_asr(path: Path) -> list[AsrOutput]:
    return [
        AsrOutput.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def update_stats(stats: ModelStats, gold: GoldAnnotation, output: AsrOutput) -> None:
    stats.examples += 1
    reference_chars = chars(gold.dialect_transcript)
    hypothesis_chars = chars(output.hypothesis)
    stats.char_edits += levenshtein(reference_chars, hypothesis_chars)
    stats.char_total += len(reference_chars)

    reference_words = words(gold.dialect_transcript)
    hypothesis_words = words(output.hypothesis)
    stats.word_edits += levenshtein(reference_words, hypothesis_words)
    stats.word_total += len(reference_words)

    if gold.intent == output.intent_prediction:
        stats.intent_correct += 1

    gold_slots = slot_pairs(gold.slots)
    predicted_slots = slot_pairs(output.slots)
    stats.slot_true_positive += len(gold_slots & predicted_slots)
    stats.slot_false_positive += len(predicted_slots - gold_slots)
    stats.slot_false_negative += len(gold_slots - predicted_slots)

    for span in gold.critical_spans:
        stats.critical_total[span.category] += 1
        if span.span_text not in output.hypothesis:
            stats.critical_errors[span.category] += 1


def ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def summarize_stats(stats_by_model: dict[str, ModelStats]) -> dict[str, dict[str, float | int]]:
    summary: dict[str, dict[str, float | int]] = {}
    for model_name, stats in sorted(stats_by_model.items()):
        slot_precision = ratio(
            stats.slot_true_positive,
            stats.slot_true_positive + stats.slot_false_positive,
        )
        slot_recall = ratio(
            stats.slot_true_positive,
            stats.slot_true_positive + stats.slot_false_negative,
        )
        slot_f1 = ratio(2 * slot_precision * slot_recall, slot_precision + slot_recall)
        critical_total = sum(stats.critical_total.values())
        critical_errors = sum(stats.critical_errors.values())
        summary[model_name] = {
            "examples": stats.examples,
            "cer": ratio(stats.char_edits, stats.char_total),
            "wer": ratio(stats.word_edits, stats.word_total),
            "intent_accuracy": ratio(stats.intent_correct, stats.examples),
            "slot_precision": slot_precision,
            "slot_recall": slot_recall,
            "slot_f1": slot_f1,
            "semantic_critical_error_rate": ratio(critical_errors, critical_total),
        }
        for category, total in sorted(stats.critical_total.items()):
            errors = stats.critical_errors[category]
            summary[model_name][f"{category}_error_rate"] = ratio(errors, total)
    return summary


def markdown_table(summary: dict[str, dict[str, float | int]]) -> str:
    columns: Final[tuple[str, ...]] = (
        "model",
        "examples",
        "cer",
        "wer",
        "intent_accuracy",
        "slot_f1",
        "semantic_critical_error_rate",
    )
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for model_name, metrics in summary.items():
        row = [model_name]
        for column in columns[1:]:
            value = metrics[column]
            match value:
                case int() as integer:
                    row.append(str(integer))
                case float() as number:
                    row.append(f"{number:.3f}")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


@app.command()
def main(
    gold_path: Annotated[Path, typer.Argument(help="Gold semantic annotations JSONL.")],
    asr_path: Annotated[Path, typer.Argument(help="ASR outputs JSONL.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
) -> None:
    gold_records = read_gold(gold_path)
    stats_by_model: dict[str, ModelStats] = defaultdict(ModelStats)
    for output in read_asr(asr_path):
        update_stats(stats_by_model[output.model], gold_records[output.utterance_id], output)

    summary = summarize_stats(stats_by_model)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "semantic_metrics_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "semantic_metrics_summary.md").write_text(
        markdown_table(summary) + "\n",
        encoding="utf-8",
    )
    console.print(markdown_table(summary))
    console.print(f"Wrote {output_dir}")


if __name__ == "__main__":
    app()
