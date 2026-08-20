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
#      uv run scripts/build_weak_semantic_preannotations.py research/experiments/runs/aihub_119_semantic_review_pack/semantic_review_queue.local.jsonl --output-dir research/experiments/runs/aihub_119_semantic_preannotations
# 3. Or make executable and run:
#      chmod +x scripts/build_weak_semantic_preannotations.py && ./scripts/build_weak_semantic_preannotations.py research/experiments/runs/aihub_119_semantic_review_pack/semantic_review_queue.local.jsonl --output-dir research/experiments/runs/aihub_119_semantic_preannotations
# ──────────────────

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Annotated, Final, Literal, TypeAlias, assert_never

import numpy as np
import typer
from build_dialect_taxonomy import JsonValue, list_of_mappings, text_field
from rich.console import Console

Domain: TypeAlias = Literal[
    "cancellation",
    "billing",
    "delivery",
    "reservation",
    "plan_change",
    "complaint",
    "technical_support",
    "other",
]
CriticalCategory: TypeAlias = Literal[
    "negation",
    "amount",
    "date_time",
    "entity",
    "intent_cue",
    "confirmation",
    "other",
]
RISK: Final[dict[CriticalCategory, str]] = {
    "negation": "high",
    "amount": "high",
    "date_time": "high",
    "entity": "medium",
    "intent_cue": "high",
    "confirmation": "high",
    "other": "medium",
}
AMOUNT_RE: Final[re.Pattern[str]] = re.compile(r"[0-9일이삼사오육칠팔구십백천만억]+ ?(?:원|만원|천원|프로|%)")
DATE_TIME_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:오늘|내일|모레|어제|오전|오후|다음 ?주|이번 ?주|[0-9]+월|[0-9]+일|[0-9]+시|[0-9]+분)",
)
TEXT_CUES: Final[tuple[tuple[CriticalCategory, tuple[str, ...]], ...]] = (
    ("negation", ("안", "못", "없", "아니", "불가")),
    ("intent_cue", ("가입", "결제", "문의", "배송", "변경", "예약", "요금", "취소", "환불", "해지")),
    ("confirmation", ("네", "예", "맞", "아니", "그렇")),
)
DOMAIN_CUES: Final[tuple[tuple[Domain, tuple[str, ...]], ...]] = (
    ("cancellation", ("해지", "취소")),
    ("billing", ("결제", "요금", "납부", "환불", "원")),
    ("delivery", ("배송", "택배")),
    ("reservation", ("예약", "일정")),
    ("plan_change", ("변경", "가입", "요금제")),
    ("complaint", ("불만", "민원", "항의")),
    ("technical_support", ("오류", "고장", "안되", "인터넷")),
)
INTENT_BY_DOMAIN: Final[dict[Domain, str]] = {
    "cancellation": "handle_cancellation",
    "billing": "handle_billing_or_refund",
    "delivery": "handle_delivery_status",
    "reservation": "handle_reservation",
    "plan_change": "handle_plan_change",
    "complaint": "handle_complaint",
    "technical_support": "handle_technical_support",
    "other": "other_aicc_intent",
}

console = Console()
app = typer.Typer(add_completion=False)


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def load_rows(path: Path) -> list[dict[str, JsonValue]]:
    rows: list[dict[str, JsonValue]] = []
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


def hints(span: dict[str, JsonValue]) -> list[CriticalCategory]:
    categories: list[CriticalCategory] = []
    for hint in list_of_mappings(span.get("semantic_category_hints")):
        category = text_field(hint, "value")
        match category:
            case "negation" | "amount" | "date_time" | "entity" | "intent_cue" | "confirmation" | "other":
                categories.append(category)
            case "":
                continue
            case _:
                continue
    if categories:
        return categories
    value = span.get("semantic_category_hints")
    match value:
        case list() as items:
            for item in items:
                match item:
                    case "negation" | "amount" | "date_time" | "entity" | "intent_cue" | "confirmation" | "other":
                        categories.append(item)
                    case str() | int() | float() | bool() | list() | dict() | None:
                        continue
                    case unreachable:
                        assert_never(unreachable)
        case str() | int() | float() | bool() | dict() | None:
            return []
        case unreachable:
            assert_never(unreachable)
    return list(dict.fromkeys(category for category in categories if category != "other"))


def infer_domain(text: str) -> Domain:
    for domain, cues in DOMAIN_CUES:
        if any(cue in text for cue in cues):
            return domain
    return "other"


def critical_spans(row: dict[str, JsonValue]) -> list[dict[str, JsonValue]]:
    spans: list[dict[str, JsonValue]] = []
    for span in local_span_candidates(row):
        span_text = text_field(span, "span_text")
        if not span_text:
            continue
        for category in hints(span):
            spans.append(critical_span_row(span_text, category))
    transcript = f"{text_field(row, 'standard_transcript')} {text_field(row, 'dialect_transcript')}"
    spans.extend(transcript_critical_spans(transcript))
    return unique_spans(spans)


def local_span_candidates(row: dict[str, JsonValue]) -> list[dict[str, JsonValue]]:
    review_pack_spans = list_of_mappings(row.get("candidate_critical_spans"))
    if review_pack_spans:
        return review_pack_spans
    return list_of_mappings(row.get("critical_span_candidates"))


def critical_span_row(span_text: str, category: CriticalCategory) -> dict[str, JsonValue]:
    return {
        "span_text": span_text,
        "category": category,
        "business_risk": RISK[category],
        "expected_asr_preservation": f"preserve {category} meaning",
    }


def transcript_critical_spans(transcript: str) -> list[dict[str, JsonValue]]:
    spans: list[dict[str, JsonValue]] = []
    spans.extend(critical_span_row(match.group(0), "amount") for match in AMOUNT_RE.finditer(transcript))
    spans.extend(critical_span_row(match.group(0), "date_time") for match in DATE_TIME_RE.finditer(transcript))
    for category, cues in TEXT_CUES:
        spans.extend(critical_span_row(cue, category) for cue in cues if cue in transcript)
    return spans


def unique_spans(spans: list[dict[str, JsonValue]]) -> list[dict[str, JsonValue]]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, JsonValue]] = []
    for span in spans:
        key = (text_field(span, "span_text"), text_field(span, "category"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(span)
    return unique


def slot_rows(spans: list[dict[str, JsonValue]]) -> list[dict[str, JsonValue]]:
    slots: list[dict[str, JsonValue]] = []
    for span in spans:
        category = text_field(span, "category")
        span_text = text_field(span, "span_text")
        match category:
            case "amount" | "date_time" | "intent_cue" | "confirmation" | "entity":
                slots.append({"name": category, "value": span_text, "span_text": span_text})
            case "negation" | "other" | "":
                continue
            case _:
                continue
    return slots


def preannotation(row: dict[str, JsonValue]) -> dict[str, JsonValue] | None:
    spans = critical_spans(row)
    if not spans:
        return None
    transcript = f"{text_field(row, 'standard_transcript')} {text_field(row, 'dialect_transcript')}"
    domain = infer_domain(transcript)
    utterance_id = text_field(row, "utterance_id")
    return {
        "utterance_id": utterance_id,
        "audio_path": text_field(row, "audio_path"),
        "speaker_region": text_field(row, "speaker_region"),
        "speaker_age_band": text_field(row, "speaker_age_band"),
        "acoustic_condition": text_field(row, "acoustic_condition"),
        "dialect_transcript": text_field(row, "dialect_transcript"),
        "standard_transcript": text_field(row, "standard_transcript"),
        "domain": domain,
        "intent": INTENT_BY_DOMAIN[domain],
        "slots": slot_rows(spans),
        "critical_spans": spans,
        "clarification_required": True,
        "notes": f"weak_preannotation_id={stable_hash(utterance_id)}; human_review_required=true",
    }


def write_outputs(rows: list[dict[str, JsonValue]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    annotations = [annotation for row in rows if (annotation := preannotation(row)) is not None]
    with (output_dir / "weak_semantic_preannotations.local.jsonl").open("w", encoding="utf-8") as file:
        for annotation in annotations:
            _ = file.write(json.dumps(annotation, ensure_ascii=False) + "\n")
    summary = {
        "input_rows": len(rows),
        "preannotated_rows": len(annotations),
        "domain_counts": dict(Counter(text_field(row, "domain") for row in annotations).most_common()),
        "critical_span_counts": dict(
            Counter(
                text_field(span, "category")
                for row in annotations
                for span in list_of_mappings(row.get("critical_spans"))
            ).most_common(),
        ),
        "raw_text_policy": "Weak preannotations are local-only and contain transcript text.",
        "gold_status": "not_gold_human_review_required",
        "numpy_version": np.__version__,
    }
    _ = (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_readme(output_dir, summary)


def write_readme(output_dir: Path, summary: dict[str, JsonValue]) -> None:
    lines = [
        "# Weak Semantic Preannotations",
        "",
        f"- Input rows: {summary['input_rows']}",
        f"- Preannotated rows: {summary['preannotated_rows']}",
        "- Output: `weak_semantic_preannotations.local.jsonl`",
        "",
        "These rows are schema-shaped review seeds, not gold annotations.",
        "They contain restricted transcript text and must stay local.",
    ]
    (output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


@app.command()
def main(
    review_queue_path: Annotated[Path, typer.Argument(help="semantic_review_queue.local.jsonl")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
) -> None:
    if not review_queue_path.exists():
        console.print(f"Review queue not found: {review_queue_path}")
        raise typer.Exit(code=2)
    write_outputs(load_rows(review_queue_path), output_dir)
    console.print(f"Wrote {output_dir}")


if __name__ == "__main__":
    app()
