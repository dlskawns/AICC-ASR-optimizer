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
#      uv run scripts/remine_critical_spans.py research/experiments/runs/aihub_119_pilot_review_packet/pilot_candidate_annotations.local.jsonl --output-dir research/experiments/runs/aihub_119_critical_span_remine
# ──────────────────

"""Re-mine AICC critical spans with eojeol-boundary rules instead of raw substring hits.

The original miner in `build_weak_semantic_preannotations.py` tests `cue in transcript` and matches an
amount pattern anywhere in the string. Both ignore the eojeol boundary, which is the only thing that
separates a business cue from an ordinary word in Korean:

- a cancellation cue matched inside `-해지다` verb forms that describe no cancellation at all;
- an amount matched across an eojeol break, turning an ordinary noun-plus-particle sequence into money.

This miner requires every cue to open a real eojeol, matches amounts token-wise, and declares per cue
whether it may attach to a following stem or must stand alone. It emits the same annotation schema, so
the output can be fed straight into `analyze_critical_span_preservation.py`.

Output is still weak labelling. It is more precise, not gold.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Final, Literal, TypeAlias, assert_never

import numpy as np
import typer
from analyze_critical_span_preservation import label_grounded
from build_dialect_taxonomy import JsonValue, list_of_mappings, text_field
from build_weak_semantic_preannotations import RISK, CriticalCategory
from rich.console import Console

JsonObject: TypeAlias = dict[str, JsonValue]
MatchMode: TypeAlias = Literal["exact", "prefix"]

# `exact` cues must stand alone as their own eojeol. A single syllable glued to a stem is far more
# often an ordinary morpheme than a business marker, so attaching them is not worth the precision loss.
# `prefix` cues may open an eojeol and carry inflection after them.
CUE_RULES: Final[tuple[tuple[CriticalCategory, MatchMode, tuple[str, ...]], ...]] = (
    ("negation", "exact", ("안", "못")),
    ("negation", "prefix", ("없", "아니", "불가")),
    ("intent_cue", "prefix", ("가입", "결제", "문의", "배송", "변경", "예약", "요금", "취소", "환불", "해지")),
    ("confirmation", "exact", ("네", "예")),
    ("confirmation", "prefix", ("아니", "맞", "그렇")),
)
DATE_TIME_CUES: Final[tuple[str, ...]] = ("오늘", "내일", "모레", "어제", "오전", "오후")
DATE_TIME_RE: Final[re.Pattern[str]] = re.compile(r"^(?:[0-9]+월|[0-9]+일|[0-9]+시|[0-9]+분)")
NUMERAL_RUN: Final[re.Pattern[str]] = re.compile(r"^[0-9,일이삼사오육칠팔구십백천만억]+$")
AMOUNT_UNIT: Final[re.Pattern[str]] = re.compile(r"^(?:원|만원|천원|프로|%)")
AMOUNT_TOKEN: Final[re.Pattern[str]] = re.compile(r"^[0-9,일이삼사오육칠팔구십백천만억]+\s?(?:원|만원|천원|프로|%)")
SLOT_CATEGORIES: Final[frozenset[str]] = frozenset({"amount", "date_time", "intent_cue", "confirmation", "entity"})

app = typer.Typer(add_completion=False)
console = Console()


@dataclass(frozen=True, slots=True)
class Remined:
    annotation: JsonObject
    old_spans: list[JsonObject]
    new_spans: list[JsonObject]


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


def clean(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣%,]", "", text)


def tokens(transcript: str) -> list[str]:
    return [token for token in (clean(part) for part in transcript.split()) if token]


def span_row(span_text: str, category: CriticalCategory, evidence: str) -> JsonObject:
    return {
        "span_text": span_text,
        "category": category,
        "business_risk": RISK[category],
        "expected_asr_preservation": f"preserve {category} meaning",
        "evidence_eojeol": evidence,
    }


def cue_spans(transcript: str) -> list[JsonObject]:
    found: list[JsonObject] = []
    for token in tokens(transcript):
        for category, mode, cues in CUE_RULES:
            for cue in cues:
                hit = token == cue if mode == "exact" else token.startswith(cue)
                if hit:
                    found.append(span_row(cue, category, token))
    return found


def date_time_spans(transcript: str) -> list[JsonObject]:
    found: list[JsonObject] = []
    for token in tokens(transcript):
        for cue in DATE_TIME_CUES:
            if token.startswith(cue):
                found.append(span_row(cue, "date_time", token))
        match = DATE_TIME_RE.match(token)
        if match:
            found.append(span_row(match.group(0), "date_time", token))
    return found


def amount_spans(transcript: str) -> list[JsonObject]:
    """Match amounts token-wise so a numeral cannot be read across an eojeol break.

    The old pattern scanned the raw string, so a noun ending in a numeral syllable followed by a word
    starting with the currency character produced a phantom amount. Requiring the numeral run to open
    its own eojeol removes that entire failure class.
    """
    found: list[JsonObject] = []
    parts = tokens(transcript)
    for index, token in enumerate(parts):
        inline = AMOUNT_TOKEN.match(token)
        if inline:
            found.append(span_row(inline.group(0), "amount", token))
            continue
        if not NUMERAL_RUN.match(token) or index + 1 >= len(parts):
            continue
        unit = AMOUNT_UNIT.match(parts[index + 1])
        if unit:
            found.append(span_row(f"{token} {unit.group(0)}", "amount", f"{token} {parts[index + 1]}"))
    return found


def dedupe(spans: list[JsonObject]) -> list[JsonObject]:
    seen: set[tuple[str, str]] = set()
    unique: list[JsonObject] = []
    for span in spans:
        key = (text_field(span, "span_text"), text_field(span, "category"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(span)
    return unique


def mine(transcript: str) -> list[JsonObject]:
    return dedupe(amount_spans(transcript) + date_time_spans(transcript) + cue_spans(transcript))


def slot_rows(spans: list[JsonObject]) -> list[JsonObject]:
    return [
        {
            "name": text_field(span, "category"),
            "value": text_field(span, "span_text"),
            "span_text": text_field(span, "span_text"),
        }
        for span in spans
        if text_field(span, "category") in SLOT_CATEGORIES
    ]


def reference_text(row: JsonObject) -> str:
    return f"{text_field(row, 'standard_transcript')} {text_field(row, 'dialect_transcript')}".strip()


def grounded(row: JsonObject, span_text: str) -> bool:
    """Delegate to the preservation audit so both runs count phantom labels the same way."""
    references = [text_field(row, "standard_transcript"), text_field(row, "dialect_transcript")]
    return label_grounded(references, span_text)


def remine_rows(rows: list[JsonObject]) -> list[Remined]:
    remined: list[Remined] = []
    for row in rows:
        transcript = reference_text(row)
        new_spans = mine(transcript)
        annotation = dict(row)
        annotation["critical_spans"] = list(new_spans)
        annotation["slots"] = slot_rows(new_spans)
        annotation["notes"] = f"{text_field(row, 'notes')}; remined_with=eojeol_boundary_rules_v2".strip("; ")
        remined.append(Remined(annotation, list_of_mappings(row.get("critical_spans")), new_spans))
    return remined


def category_counts(rows: list[Remined], selector: str) -> JsonObject:
    counter: Counter[str] = Counter()
    for row in rows:
        spans = row.old_spans if selector == "old" else row.new_spans
        counter.update(text_field(span, "category") for span in spans)
    return dict(counter.most_common())


def phantom_report(rows: list[Remined], selector: str) -> JsonObject:
    total = 0
    phantom = 0
    by_category: Counter[str] = Counter()
    for row in rows:
        spans = row.old_spans if selector == "old" else row.new_spans
        total += len(spans)
        for span in spans:
            if not grounded(row.annotation, text_field(span, "span_text")):
                phantom += 1
                by_category[text_field(span, "category")] += 1
    return {
        "spans": total,
        "phantom_labels": phantom,
        "phantom_rate": phantom / total if total else 0.0,
        "phantom_by_category": dict(by_category.most_common()),
    }


def summarize(rows: list[Remined]) -> JsonObject:
    return {
        "analysis": "critical_span_remine_with_eojeol_boundary_rules",
        "label_status": "weak_preannotation_not_gold",
        "utterances": len(rows),
        "old_rule": {
            "description": "substring containment anywhere in the transcript",
            "category_counts": category_counts(rows, "old"),
            **phantom_report(rows, "old"),
        },
        "new_rule": {
            "description": "eojeol-initial cue match with per-cue exact/prefix mode, token-wise amount matching",
            "category_counts": category_counts(rows, "new"),
            **phantom_report(rows, "new"),
        },
        "cue_rules": {
            f"{category}:{mode}": list(cues) for category, mode, cues in CUE_RULES
        },
        "numpy_version": np.__version__,
    }


def rate(report: JsonObject, key: str) -> float:
    value = report[key]
    return float(value) if isinstance(value, (int, float)) else 0.0


def write_readme(output_dir: Path, summary: JsonObject) -> None:
    old = summary["old_rule"]
    new = summary["new_rule"]
    assert isinstance(old, dict) and isinstance(new, dict)
    text = (
        "# Critical Span Re-mining\n\n"
        "The weak AICC critical-span labels were mined by raw substring containment. Two failure classes\n"
        "followed from ignoring the eojeol boundary:\n\n"
        "- A business cue was harvested from ordinary inflected verbs that carry no business event.\n"
        "- An amount pattern was matched across an eojeol break, turning a noun-plus-particle sequence into money.\n\n"
        "This run re-mines the same utterances with boundary-aware rules. Every cue must open a real eojeol,\n"
        "single-syllable markers must stand alone, and amounts are matched token-wise.\n\n"
        f"**Label status: `{summary['label_status']}`.** More precise is not gold.\n\n"
        "## Result\n\n"
        "| Rule | Spans | Phantom labels | Phantom rate |\n"
        "|---|---:|---:|---:|\n"
        f"| old, substring | {old['spans']} | {old['phantom_labels']} | {rate(old, 'phantom_rate'):.3f} |\n"
        f"| new, eojeol boundary | {new['spans']} | {new['phantom_labels']} | {rate(new, 'phantom_rate'):.3f} |\n\n"
        f"- Old category counts: {json.dumps(old['category_counts'], ensure_ascii=False)}\n"
        f"- New category counts: {json.dumps(new['category_counts'], ensure_ascii=False)}\n"
        f"- Old phantom labels by category: {json.dumps(old['phantom_by_category'], ensure_ascii=False)}\n"
        f"- New phantom labels by category: {json.dumps(new['phantom_by_category'], ensure_ascii=False)}\n\n"
        "## What This Does Not Fix\n\n"
        "The boundary rule proves a label names a real eojeol. It cannot prove that eojeol carried a business\n"
        "event. This corpus is spontaneous conversation, so a cue that opens a real eojeol may still describe\n"
        "something unrelated to contact-centre work. Human review remains required before any of this is gold.\n\n"
        "Recall also drops on purpose. Single-syllable negation markers fused to a following stem are no longer\n"
        "collected, because keeping them costs more precision than the extra recall is worth.\n\n"
        "The re-mined annotation file carries transcript text and is local-only.\n"
    )
    (output_dir / "README.md").write_text(text, encoding="utf-8")


def write_outputs(rows: list[Remined], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "remined_annotations.local.jsonl").open("w", encoding="utf-8") as file:
        for row in rows:
            _ = file.write(json.dumps(row.annotation, ensure_ascii=False) + "\n")
    summary = summarize(rows)
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_readme(output_dir, summary)


@app.command()
def main(
    annotations_path: Annotated[Path, typer.Argument(help="Pilot candidate annotations local JSONL.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
) -> None:
    if not annotations_path.exists():
        console.print(f"Input not found: {annotations_path}")
        raise typer.Exit(code=2)
    rows = remine_rows(load_jsonl(annotations_path))
    if not rows:
        console.print("No annotations to re-mine.")
        raise typer.Exit(code=1)
    write_outputs(rows, output_dir)
    console.print(f"Re-mined {len(rows)} utterances into {output_dir}")


if __name__ == "__main__":
    app()
