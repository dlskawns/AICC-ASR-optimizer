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
#      uv run scripts/analyze_critical_span_preservation.py research/experiments/runs/aihub_119_pilot_review_packet/pilot_candidate_annotations.local.jsonl research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_medium.local.jsonl --output-dir research/experiments/runs/aihub_119_critical_span_preservation
# ──────────────────

"""Measure whether ASR preserves AICC-critical spans, and expose where the metric itself fails.

Unit-level dialect error rates say the surface moved. They do not say the business meaning moved.
This script scores annotated critical spans - negation, confirmation, intent cue, amount, date/time -
against the ASR hypothesis.

A naive substring check is not usable for Korean AICC spans and this script does not use one:

- Amount spans are written in Sino-Korean numerals in the reference and in Arabic numerals by the ASR,
  so substring matching reports near-total loss where the meaning is intact. Amounts are therefore
  compared by parsed numeric value.
- Single-syllable spans such as the negation marker `안` or the confirmation marker `네` occur inside
  unrelated words, so substring matching reports near-total preservation. Matches are therefore graded:
  an eojeol-initial hit counts as preserved, while a mid-word hit is reported as ambiguous rather than
  silently counted either way.

The critical spans come from weak preannotations, so every number here is a weak-label estimate, not gold.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Final, Literal, TypeAlias, assert_never

import numpy as np
import typer
from build_dialect_taxonomy import JsonValue, list_of_mappings, text_field
from rich.console import Console

JsonObject: TypeAlias = dict[str, JsonValue]
MatchType: TypeAlias = Literal[
    "numeral_equivalent",
    "eojeol_initial",
    "substring_only",
    "unresolved_numeral",
    "absent",
    "phantom_label",
]

BOOTSTRAP_DRAWS: Final[int] = 10000
RANDOM_SEED: Final[int] = 20260817
MIN_CONTRAST_SPANS: Final[int] = 10
MIN_CONTRAST_CLUSTERS: Final[int] = 5

SINO_DIGITS: Final[dict[str, int]] = {
    "영": 0, "공": 0, "일": 1, "이": 2, "삼": 3, "사": 4,
    "오": 5, "육": 6, "칠": 7, "팔": 8, "구": 9,
}
SINO_UNITS: Final[dict[str, int]] = {"십": 10, "백": 100, "천": 1000}
SINO_SCALES: Final[dict[str, int]] = {"만": 10**4, "억": 10**8, "조": 10**12}
NUMERAL_CHARS: Final[str] = "".join(SINO_DIGITS) + "".join(SINO_UNITS) + "".join(SINO_SCALES)
DIGIT_GROUP: Final[re.Pattern[str]] = re.compile(r"(\d[\d,]*)\s*([억만천])?")
SINO_GROUP: Final[re.Pattern[str]] = re.compile(f"[{NUMERAL_CHARS}]+")

app = typer.Typer(add_completion=False)
console = Console()


@dataclass(frozen=True, slots=True)
class SpanOutcome:
    review_id: str
    utterance_id: str
    cohort: str
    span_text: str
    category: str
    business_risk: str
    source: str
    dialect_marked: bool
    match_type: MatchType

    @property
    def scorable(self) -> bool:
        """False when the annotation itself is an artifact, so the span cannot score the ASR."""
        return self.match_type != "phantom_label"

    @property
    def preserved(self) -> bool:
        return self.match_type in {"numeral_equivalent", "eojeol_initial"}

    @property
    def ambiguous(self) -> bool:
        return self.match_type in {"substring_only", "unresolved_numeral"}

    @property
    def absent(self) -> bool:
        return self.match_type == "absent"


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


def normalized(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", text)


def parse_sino_numeral(text: str) -> int | None:
    """Parse a Sino-Korean numeral run such as `백삼십만` into 1300000.

    Returns None for runs this reader cannot resolve, notably bare digit sequences like `일이`
    that are a spoken list ("1, 2") rather than a single number.
    """
    total = 0
    section = 0
    digit = 0
    seen_digit = False
    for char in text:
        if char in SINO_DIGITS:
            if seen_digit:
                return None
            digit = SINO_DIGITS[char]
            seen_digit = True
        elif char in SINO_UNITS:
            section += (digit or 1) * SINO_UNITS[char]
            digit, seen_digit = 0, False
        elif char in SINO_SCALES:
            section += digit
            total += (section or 1) * SINO_SCALES[char]
            section, digit, seen_digit = 0, 0, False
        else:
            return None
    return total + section + digit


def numeric_values(text: str) -> set[int]:
    """Collect every number the text expresses, in Arabic digits or Sino-Korean numerals.

    Two guards keep this from inventing numbers. Digit groups are consumed first and blanked out, so
    the `만` in `80만원` is not re-read as a standalone 10000. Sino-Korean runs then count only when
    they carry a unit or scale character, because bare digit syllables such as `이` or `사` are ordinary
    Korean morphemes and reading them as numbers produces matches everywhere.
    """
    values: set[int] = set()
    for digits, scale in DIGIT_GROUP.findall(text):
        cleaned = digits.replace(",", "")
        if not cleaned:
            continue
        values.add(int(cleaned) * SINO_SCALES.get(scale, SINO_UNITS.get(scale, 1)))
    residual = DIGIT_GROUP.sub(" ", text)
    for run in SINO_GROUP.findall(residual):
        if not any(char in SINO_UNITS or char in SINO_SCALES for char in run):
            continue
        parsed = parse_sino_numeral(run)
        if parsed is not None and parsed > 0:
            values.add(parsed)
    return values


def eojeol_initial_hit(hypothesis: str, needle: str) -> bool:
    """True when some hypothesis eojeol starts with the span surface.

    Korean is agglutinative, so a critical marker normally opens its eojeol. Requiring the eojeol
    boundary stops `네` from matching inside `그러네요` and `안` from matching inside `안녕`-style
    mid-word positions, which is what makes single-syllable spans unusable under plain containment.
    """
    return any(normalized(token).startswith(needle) for token in hypothesis.split() if normalized(token))


def label_grounded(references: list[str], span_text: str) -> bool:
    """True when the span opens a real eojeol in the reference transcript.

    The weak preannotations were mined by substring, so a marker like the cancellation cue `해지`
    was also harvested from ordinary verbs such as `비슷해지면` or `피곤해지고`. Those labels never
    referred to a business event, so scoring an ASR against them measures nothing.
    """
    needle = normalized(span_text)
    if not needle:
        return False
    if numeric_values(span_text):
        return True
    return any(eojeol_initial_hit(reference, needle) for reference in references)


def classify_match(hypothesis: str, span_text: str, references: list[str]) -> MatchType:
    if not label_grounded(references, span_text):
        return "phantom_label"
    span_values = numeric_values(span_text)
    if span_values:
        return "numeral_equivalent" if span_values & numeric_values(hypothesis) else "absent"
    needle = normalized(span_text)
    if not needle:
        return "absent"
    if eojeol_initial_hit(hypothesis, needle):
        return "eojeol_initial"
    if needle in normalized(hypothesis):
        return "substring_only"
    # A span such as `일이 프로` reads as a spoken list, not a single number, so neither the numeral
    # path nor the surface path can settle it. Report that instead of scoring it as a loss.
    if any(char in SINO_DIGITS for char in span_text):
        return "unresolved_numeral"
    return "absent"


def overlaps(left: str, right: str) -> bool:
    """Treat a span and a dialect eojeol as linked when either surface contains the other."""
    a, b = normalized(left), normalized(right)
    return bool(a) and bool(b) and (a in b or b in a)


def dialect_surfaces(manifest_row: JsonObject) -> list[str]:
    return [text_field(unit, "dialect") for unit in list_of_mappings(manifest_row.get("dialect_units"))]


def span_rows(annotation: JsonObject) -> list[tuple[str, str, str, str]]:
    """Return (span_text, category, business_risk, source) for critical spans and slots."""
    rows = [
        (
            text_field(span, "span_text"),
            text_field(span, "category"),
            text_field(span, "business_risk"),
            "critical_span",
        )
        for span in list_of_mappings(annotation.get("critical_spans"))
    ]
    rows.extend(
        (text_field(slot, "span_text") or text_field(slot, "value"), text_field(slot, "name"), "unspecified", "slot")
        for slot in list_of_mappings(annotation.get("slots"))
    )
    return [row for row in rows if row[0]]


def build_outcomes(
    annotations: list[JsonObject],
    manifest_rows: list[JsonObject],
    asr_rows: list[JsonObject],
) -> tuple[list[SpanOutcome], int]:
    manifest_by_utterance = {text_field(row, "utterance_id"): row for row in manifest_rows}
    asr_by_review = {text_field(row, "review_id"): row for row in asr_rows}
    outcomes: list[SpanOutcome] = []
    skipped = 0
    for annotation in annotations:
        utterance_id = text_field(annotation, "utterance_id")
        manifest_row = manifest_by_utterance.get(utterance_id)
        if manifest_row is None:
            skipped += 1
            continue
        review_id = text_field(manifest_row, "review_id")
        asr_row = asr_by_review.get(review_id)
        if asr_row is None:
            skipped += 1
            continue
        hypothesis = text_field(asr_row, "hypothesis")
        surfaces = dialect_surfaces(manifest_row)
        references = [
            text_field(annotation, "dialect_transcript"),
            text_field(annotation, "standard_transcript"),
        ]
        for span_text, category, business_risk, source in span_rows(annotation):
            outcomes.append(
                SpanOutcome(
                    review_id=review_id,
                    utterance_id=utterance_id,
                    cohort=text_field(manifest_row, "cohort"),
                    span_text=span_text,
                    category=category,
                    business_risk=business_risk,
                    source=source,
                    dialect_marked=any(overlaps(span_text, surface) for surface in surfaces),
                    match_type=classify_match(hypothesis, span_text, references),
                ),
            )
    return outcomes, skipped


def strict_loss_rate(outcomes: list[SpanOutcome]) -> float:
    return sum(1 for row in outcomes if row.absent) / len(outcomes) if outcomes else math.nan


def inclusive_loss_rate(outcomes: list[SpanOutcome]) -> float:
    return sum(1 for row in outcomes if not row.preserved) / len(outcomes) if outcomes else math.nan


def cluster_arrays(outcomes: list[SpanOutcome], predicate: str) -> tuple[np.ndarray, np.ndarray]:
    by_utterance: dict[str, list[SpanOutcome]] = {}
    for row in outcomes:
        by_utterance.setdefault(row.review_id, []).append(row)
    hits = np.array(
        [sum(1 for row in rows if getattr(row, predicate)) for rows in by_utterance.values()],
        dtype=np.int64,
    )
    total = np.array([len(rows) for rows in by_utterance.values()], dtype=np.int64)
    return hits, total


def bootstrap_rate(
    outcomes: list[SpanOutcome],
    predicate: str,
    rng: np.random.Generator,
    draws: int,
) -> JsonObject:
    """Bootstrap over utterances, because one utterance contributes several spans."""
    hits, total = cluster_arrays(outcomes, predicate)
    if hits.size == 0:
        return {"low": None, "high": None, "clusters": 0, "draws": draws}
    picks = rng.integers(0, hits.size, size=(draws, hits.size))
    with np.errstate(divide="ignore", invalid="ignore"):
        rates = hits[picks].sum(axis=1) / total[picks].sum(axis=1)
    finite = rates[np.isfinite(rates)]
    low, high = np.percentile(finite, [2.5, 97.5])
    return {"low": float(low), "high": float(high), "clusters": int(hits.size), "draws": draws}


def group_stats(outcomes: list[SpanOutcome], key: str) -> JsonObject:
    grouped: dict[str, list[SpanOutcome]] = {}
    for row in outcomes:
        grouped.setdefault(getattr(row, key), []).append(row)
    return {
        name: {
            "labelled_spans": len(rows),
            "phantom_labels": sum(1 for row in rows if not row.scorable),
            "scorable_spans": sum(1 for row in rows if row.scorable),
            "preserved": sum(1 for row in rows if row.preserved),
            "ambiguous": sum(1 for row in rows if row.ambiguous),
            "absent": sum(1 for row in rows if row.absent),
            "strict_loss_rate": strict_loss_rate([row for row in rows if row.scorable]),
            "inclusive_loss_rate": inclusive_loss_rate([row for row in rows if row.scorable]),
        }
        for name, rows in sorted(grouped.items(), key=lambda item: -len(item[1]))
    }


def dialect_contrast(outcomes: list[SpanOutcome], rng: np.random.Generator, draws: int) -> JsonObject:
    marked = [row for row in outcomes if row.dialect_marked]
    plain = [row for row in outcomes if not row.dialect_marked]
    if not marked or not plain:
        return {"comparable": False, "dialect_marked_spans": len(marked), "plain_spans": len(plain)}

    def resample(rows: list[SpanOutcome]) -> np.ndarray:
        hits, total = cluster_arrays(rows, "absent")
        picks = rng.integers(0, hits.size, size=(draws, hits.size))
        with np.errstate(divide="ignore", invalid="ignore"):
            return hits[picks].sum(axis=1) / total[picks].sum(axis=1)

    difference = resample(marked) - resample(plain)
    finite = difference[np.isfinite(difference)]
    low, high = np.percentile(finite, [2.5, 97.5])
    marked_clusters = len({row.review_id for row in marked})
    # With a handful of spans in one arm the bootstrap can return an interval that excludes zero purely
    # because every resample repeats the same few observations. Say so rather than report a finding.
    underpowered = len(marked) < MIN_CONTRAST_SPANS or marked_clusters < MIN_CONTRAST_CLUSTERS
    return {
        "comparable": True,
        "metric": "strict_loss_rate",
        "underpowered": underpowered,
        "underpowered_rule": f"fewer_than_{MIN_CONTRAST_SPANS}_spans_or_{MIN_CONTRAST_CLUSTERS}_utterances_in_an_arm",
        "dialect_marked_utterances": marked_clusters,
        "dialect_marked_spans": len(marked),
        "dialect_marked_loss_rate": strict_loss_rate(marked),
        "plain_spans": len(plain),
        "plain_loss_rate": strict_loss_rate(plain),
        "difference": strict_loss_rate(marked) - strict_loss_rate(plain),
        "difference_ci95": {"low": float(low), "high": float(high)},
        "difference_crosses_zero": bool(low <= 0 <= high),
    }


def case_row(row: SpanOutcome) -> JsonObject:
    return {
        "review_id": row.review_id,
        "utterance_id": row.utterance_id,
        "cohort": row.cohort,
        "span_text": row.span_text,
        "category": row.category,
        "business_risk": row.business_risk,
        "source": row.source,
        "dialect_marked": row.dialect_marked,
        "match_type": row.match_type,
        "preserved": row.preserved,
    }


def summarize(outcomes: list[SpanOutcome], skipped: int, model: str, rng: np.random.Generator, draws: int) -> JsonObject:
    critical = [row for row in outcomes if row.source == "critical_span"]
    scorable = [row for row in critical if row.scorable]
    phantom = [row for row in critical if not row.scorable]
    slots = [row for row in outcomes if row.source == "slot"]
    return {
        "model": model,
        "label_status": "weak_preannotation_not_gold",
        "utterances": len({row.review_id for row in outcomes}),
        "skipped_annotations": skipped,
        "labelled_critical_spans": len(critical),
        "phantom_labels": len(phantom),
        "phantom_label_rate": len(phantom) / len(critical) if critical else math.nan,
        "phantom_label_category_counts": dict(Counter(row.category for row in phantom).most_common()),
        "scorable_critical_spans": len(scorable),
        "match_type_counts": dict(Counter(row.match_type for row in critical).most_common()),
        "strict_loss_rate": strict_loss_rate(scorable),
        "strict_loss_rate_ci95": bootstrap_rate(scorable, "absent", rng, draws),
        "inclusive_loss_rate": inclusive_loss_rate(scorable),
        "loss_by_category": group_stats(critical, "category"),
        "loss_by_cohort": group_stats(critical, "cohort"),
        "absent_span_category_counts": dict(Counter(row.category for row in scorable if row.absent).most_common()),
        "ambiguous_span_category_counts": dict(Counter(row.category for row in scorable if row.ambiguous).most_common()),
        "dialect_marked_contrast": dialect_contrast(scorable, rng, draws),
        "slot_spans": len(slots),
        "slot_phantom_labels": sum(1 for row in slots if not row.scorable),
        "slot_strict_loss_rate": strict_loss_rate([row for row in slots if row.scorable]),
        "match_rules": {
            "numeral_equivalent": "span and hypothesis express the same parsed number, across Sino-Korean and Arabic notation",
            "eojeol_initial": "some hypothesis eojeol starts with the span surface",
            "substring_only": "span surface appears mid-eojeol only, so the hit is not trustworthy",
            "unresolved_numeral": "span reads as a spoken number list that neither path can settle",
            "absent": "no match",
            "phantom_label": "the weak annotation never named a real eojeol in the reference, so the span cannot score anything",
        },
    }


def category_table(by_category: JsonObject) -> str:
    return "\n".join(
        f"| {name} | {stats['labelled_spans']} | {stats['phantom_labels']} | {stats['scorable_spans']} | "
        f"{stats['preserved']} | {stats['ambiguous']} | {stats['absent']} | "
        f"{float(stats['strict_loss_rate']):.3f} |"
        if isinstance(stats["strict_loss_rate"], float) and math.isfinite(float(stats["strict_loss_rate"]))
        else f"| {name} | {stats['labelled_spans']} | {stats['phantom_labels']} | {stats['scorable_spans']} | "
        f"{stats['preserved']} | {stats['ambiguous']} | {stats['absent']} | n/a |"
        for name, stats in by_category.items()
        if isinstance(stats, dict)
    )


def write_readme(output_dir: Path, report: JsonObject) -> None:
    contrast = report["dialect_marked_contrast"]
    ci = report["strict_loss_rate_ci95"]
    by_category = report["loss_by_category"]
    counts = report["match_type_counts"]
    assert isinstance(contrast, dict) and isinstance(ci, dict)
    assert isinstance(by_category, dict) and isinstance(counts, dict)
    contrast_lines = (
        (
            f"- Dialect-marked critical spans: {contrast['dialect_marked_spans']}, "
            f"strict loss rate {float(contrast['dialect_marked_loss_rate']):.3f}\n"
            f"- Other critical spans: {contrast['plain_spans']}, "
            f"strict loss rate {float(contrast['plain_loss_rate']):.3f}\n"
            f"- Difference: {float(contrast['difference']):.3f}, "
            f"utterance bootstrap 95% CI [{float(contrast['difference_ci95']['low']):.3f}, "
            f"{float(contrast['difference_ci95']['high']):.3f}]"
            f"{' — crosses zero' if contrast['difference_crosses_zero'] else ' — excludes zero'}\n"
            + (
                f"- **Underpowered.** Only {contrast['dialect_marked_spans']} dialect-marked spans across "
                f"{contrast['dialect_marked_utterances']} utterances survive the phantom-label filter, so the\n"
                "  interval reflects repeated resampling of a few observations, not a dialect effect. Do not cite it.\n"
                if contrast.get("underpowered")
                else ""
            )
        )
        if contrast.get("comparable")
        else "- Dialect-marked contrast is not computable in this subset.\n"
    )
    text = (
        "# AICC Critical Span Preservation\n\n"
        f"Model: `{report['model']}`\n\n"
        "Dialect unit error rates measure surface movement. This run measures something closer to the AICC task:\n"
        "whether the ASR hypothesis still carries the annotated business-critical spans - negation, confirmation,\n"
        "intent cue, amount, date/time.\n\n"
        f"**Label status: `{report['label_status']}`.** The critical spans come from weak preannotations that no\n"
        "human has reviewed, so these rates size the problem; they do not settle it.\n\n"
        "## Why Plain Substring Matching Was Rejected\n\n"
        "A first pass scored spans by substring containment and produced three artifacts:\n\n"
        "- Amount spans looked catastrophic. The reference transcribes amounts in Sino-Korean numerals while the\n"
        "  ASR emits Arabic numerals, so a string comparison reported loss where the value was identical.\n"
        "  Corrected, amount loss goes to zero.\n"
        "- Single-syllable spans looked perfect. Markers such as `안`, `네`, `못` occur inside unrelated words, so a\n"
        "  string comparison reported preservation that the audio does not support.\n"
        "- Some spans were never business events at all. The weak preannotations were themselves mined by\n"
        "  substring, so the cancellation cue `해지` was harvested out of ordinary `-해지다` verb forms that carry\n"
        "  no cancellation meaning. Those labels are reported here as `phantom_label` and excluded from every rate.\n\n"
        "This run parses numerals to values, checks that each label names a real eojeol in the reference, and\n"
        "grades every remaining match by eojeol boundary. A mid-eojeol hit is reported as `substring_only` rather\n"
        "than being counted as either preserved or lost. The correction is itself a finding: neither a Korean AICC\n"
        "span metric nor its label set can be built from raw string containment.\n\n"
        "## Headline\n\n"
        f"- Utterances: {report['utterances']}\n"
        f"- Labelled critical spans: {report['labelled_critical_spans']}\n"
        f"- Phantom labels removed: {report['phantom_labels']} "
        f"({float(report['phantom_label_rate']):.1%} of labelled spans)\n"
        f"- Scorable critical spans: {report['scorable_critical_spans']}\n"
        f"- Match types: {json.dumps(counts, ensure_ascii=False)}\n"
        f"- Strict loss rate (`absent` only): {float(report['strict_loss_rate']):.3f}, "
        f"utterance bootstrap 95% CI [{float(ci['low']):.3f}, {float(ci['high']):.3f}]\n"
        f"- Inclusive loss rate (`absent` plus ambiguous): {float(report['inclusive_loss_rate']):.3f}\n\n"
        "The two rates bound the damage. The truth needs audio review of the ambiguous spans.\n\n"
        "## Loss by Category\n\n"
        "| Category | Labelled | Phantom | Scorable | Preserved | Ambiguous | Absent | Strict loss rate |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|\n"
        f"{category_table(by_category)}\n\n"
        "## Dialect Marking Contrast\n\n"
        f"{contrast_lines}\n"
        "## Open Method Limits\n\n"
        "- An eojeol-initial hit still ignores position, so a marker recognised in the wrong clause counts as preserved.\n"
        "- Numeral equality ignores unit words, so an amount and a count sharing the same number compare equal.\n"
        "- The phantom-label filter only checks that the label names a real eojeol. It cannot tell whether that\n"
        "  eojeol carried a business meaning, and this corpus is spontaneous conversation rather than contact-centre\n"
        "  speech, so the surviving label set is still weak.\n"
        "- Confidence intervals resample utterances, not spans.\n\n"
        "The span-level case file is local-only because it carries transcript surfaces.\n"
    )
    (output_dir / "README.md").write_text(text, encoding="utf-8")


def write_outputs(outcomes: list[SpanOutcome], report: JsonObject, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "critical_span_cases.local.jsonl").open("w", encoding="utf-8") as file:
        for row in outcomes:
            _ = file.write(json.dumps(case_row(row), ensure_ascii=False) + "\n")
    (output_dir / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_readme(output_dir, report)


def model_label(asr_rows: list[JsonObject], path: Path) -> str:
    labels = Counter(text_field(row, "model") for row in asr_rows if text_field(row, "model"))
    return labels.most_common(1)[0][0] if labels else path.stem


@app.command()
def main(
    annotations_path: Annotated[Path, typer.Argument(help="Pilot candidate annotations local JSONL.")],
    manifest_path: Annotated[Path, typer.Argument(help="ASR input manifest local JSONL.")],
    asr_path: Annotated[Path, typer.Argument(help="ASR output local JSONL.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
    bootstrap_draws: Annotated[int, typer.Option("--bootstrap-draws", min=1000)] = BOOTSTRAP_DRAWS,
) -> None:
    for path in (annotations_path, manifest_path, asr_path):
        if not path.exists():
            console.print(f"Input not found: {path}")
            raise typer.Exit(code=2)
    asr_rows = load_jsonl(asr_path)
    outcomes, skipped = build_outcomes(load_jsonl(annotations_path), load_jsonl(manifest_path), asr_rows)
    if not outcomes:
        console.print("No critical spans could be linked to ASR output; nothing written.")
        raise typer.Exit(code=1)
    rng = np.random.default_rng(RANDOM_SEED)
    report = summarize(outcomes, skipped, model_label(asr_rows, asr_path), rng, bootstrap_draws)
    write_outputs(outcomes, report, output_dir)
    console.print(f"Scored {len(outcomes)} spans across {report['utterances']} utterances into {output_dir}")


if __name__ == "__main__":
    app()
