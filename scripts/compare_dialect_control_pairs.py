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
#      uv run scripts/compare_dialect_control_pairs.py research/experiments/runs/aihub_119_dialect_control_pairs/pair_manifest.jsonl --case-dir research/experiments/runs/aihub_119_speaker_independent_split --case-annotations research/experiments/runs/aihub_119_holdout_critical_spans/remined_annotations.local.jsonl --control-dir research/experiments/runs/aihub_119_dialect_control_pairs --output-dir research/experiments/runs/aihub_119_dialect_control_comparison
# ──────────────────

"""Test whether dialect marking raises AICC critical-span loss, paired within speaker.

Each pair is one speaker in one recording: a dialect-bearing utterance and a length-matched
dialect-free utterance, both carrying critical spans. Because speaker, channel, and session are
identical inside a pair, the paired difference removes speaker-level ability and recording quality,
which the earlier span-overlap design could not do.

Two quantities are reported per model:

- critical-span loss, the AICC-facing number;
- non-dialect unit error, a placebo. The two arms should not differ much there. If they do, the pairs
  differ in something other than dialect marking and the critical-span result cannot be trusted.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Final, TypeAlias, assert_never

import numpy as np
import typer
from analyze_critical_span_preservation import classify_match
from build_dialect_taxonomy import JsonValue, list_of_mappings, text_field
from rich.console import Console

JsonObject: TypeAlias = dict[str, JsonValue]

BOOTSTRAP_DRAWS: Final[int] = 10000
PERMUTATION_DRAWS: Final[int] = 20000
RANDOM_SEED: Final[int] = 20260818
MODELS: Final[tuple[str, ...]] = ("faster_whisper_medium", "faster_whisper_large_v3", "wav2vec2_korean")

app = typer.Typer(add_completion=False)
console = Console()


@dataclass(frozen=True, slots=True)
class ArmOutcome:
    spans_total: int
    spans_lost: int
    plain_total: int
    plain_error: int


@dataclass(frozen=True, slots=True)
class PairOutcome:
    speaker_key: str
    cohort: str
    case: ArmOutcome
    control: ArmOutcome


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


def index_by(rows: list[JsonObject], key: str) -> dict[str, JsonObject]:
    return {text_field(row, key): row for row in rows}


def normalized(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", text)


def carries(hypothesis: str, value: str) -> bool:
    """True when some hypothesis eojeol opens with this reference surface.

    Plain substring containment was the original rule and it is not safe here. Half of the dialect
    units and a fifth of the non-dialect units are a single syllable, and a single syllable turns up
    inside unrelated words constantly, so containment credits recognitions that never happened.
    Requiring the eojeol boundary removes that.
    """
    needle = normalized(value)
    return bool(needle) and any(normalized(token).startswith(needle) for token in hypothesis.split() if normalized(token))


def arm_outcome(manifest_row: JsonObject, annotation: JsonObject, hypothesis: str) -> ArmOutcome:
    references = [
        text_field(annotation, "standard_transcript") or text_field(manifest_row, "standard_transcript"),
        text_field(annotation, "dialect_transcript") or text_field(manifest_row, "dialect_transcript"),
    ]
    spans = list_of_mappings(annotation.get("critical_spans"))
    scorable = 0
    lost = 0
    for span in spans:
        match_type = classify_match(hypothesis, text_field(span, "span_text"), references)
        if match_type == "phantom_label":
            continue
        scorable += 1
        if match_type == "absent":
            lost += 1
    plain_units = list_of_mappings(manifest_row.get("plain_units"))
    plain_error = sum(1 for unit in plain_units if not carries(hypothesis, text_field(unit, "standard")))
    return ArmOutcome(scorable, lost, len(plain_units), plain_error)


def build_pairs(
    pair_rows: list[JsonObject],
    case_manifest: dict[str, JsonObject],
    case_annotations: dict[str, JsonObject],
    case_asr: dict[str, JsonObject],
    control_manifest: dict[str, JsonObject],
    control_annotations: dict[str, JsonObject],
    control_asr: dict[str, JsonObject],
) -> list[PairOutcome]:
    pairs: list[PairOutcome] = []
    for row in pair_rows:
        case_id = text_field(row, "case_review_id")
        control_id = text_field(row, "control_review_id")
        if case_id not in case_asr or control_id not in control_asr:
            continue
        case_row = case_manifest[case_id]
        control_row = control_manifest[control_id]
        case_annotation = case_annotations.get(text_field(case_row, "utterance_id"), {})
        control_annotation = control_annotations.get(text_field(control_row, "utterance_id"), {})
        pairs.append(
            PairOutcome(
                speaker_key=text_field(row, "speaker_key"),
                cohort=text_field(row, "cohort"),
                case=arm_outcome(case_row, case_annotation, text_field(case_asr[case_id], "hypothesis")),
                control=arm_outcome(control_row, control_annotation, text_field(control_asr[control_id], "hypothesis")),
            ),
        )
    return pairs


def rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else math.nan


def paired_bootstrap(
    pairs: list[PairOutcome],
    numerator: str,
    denominator: str,
    rng: np.random.Generator,
    draws: int,
) -> JsonObject:
    """Resample whole pairs, so a speaker's two utterances always move together."""
    case_num = np.array([getattr(pair.case, numerator) for pair in pairs], dtype=np.float64)
    case_den = np.array([getattr(pair.case, denominator) for pair in pairs], dtype=np.float64)
    ctrl_num = np.array([getattr(pair.control, numerator) for pair in pairs], dtype=np.float64)
    ctrl_den = np.array([getattr(pair.control, denominator) for pair in pairs], dtype=np.float64)
    picks = rng.integers(0, len(pairs), size=(draws, len(pairs)))
    with np.errstate(divide="ignore", invalid="ignore"):
        difference = (case_num[picks].sum(axis=1) / case_den[picks].sum(axis=1)) - (
            ctrl_num[picks].sum(axis=1) / ctrl_den[picks].sum(axis=1)
        )
    finite = difference[np.isfinite(difference)]
    low, high = np.percentile(finite, [2.5, 97.5])
    observed = rate(int(case_num.sum()), int(case_den.sum())) - rate(int(ctrl_num.sum()), int(ctrl_den.sum()))
    return {
        "case_rate": rate(int(case_num.sum()), int(case_den.sum())),
        "control_rate": rate(int(ctrl_num.sum()), int(ctrl_den.sum())),
        "difference": observed,
        "difference_ci95": {"low": float(low), "high": float(high)},
        "crosses_zero": bool(low <= 0 <= high),
        "draws": draws,
    }


def sign_flip_permutation(
    pairs: list[PairOutcome],
    numerator: str,
    denominator: str,
    rng: np.random.Generator,
    draws: int,
) -> JsonObject:
    """Swap the two arms inside randomly chosen pairs.

    Under the null that dialect marking does nothing, which member of a pair is labelled the dialect
    arm is arbitrary, so swapping arms within a pair generates the null distribution directly.
    """
    case_num = np.array([getattr(pair.case, numerator) for pair in pairs], dtype=np.float64)
    case_den = np.array([getattr(pair.case, denominator) for pair in pairs], dtype=np.float64)
    ctrl_num = np.array([getattr(pair.control, numerator) for pair in pairs], dtype=np.float64)
    ctrl_den = np.array([getattr(pair.control, denominator) for pair in pairs], dtype=np.float64)
    swap = rng.integers(0, 2, size=(draws, len(pairs))).astype(bool)
    arm_a_num = np.where(swap, ctrl_num, case_num)
    arm_a_den = np.where(swap, ctrl_den, case_den)
    arm_b_num = np.where(swap, case_num, ctrl_num)
    arm_b_den = np.where(swap, case_den, ctrl_den)
    with np.errstate(divide="ignore", invalid="ignore"):
        null = (arm_a_num.sum(axis=1) / arm_a_den.sum(axis=1)) - (arm_b_num.sum(axis=1) / arm_b_den.sum(axis=1))
    observed = rate(int(case_num.sum()), int(case_den.sum())) - rate(int(ctrl_num.sum()), int(ctrl_den.sum()))
    finite = null[np.isfinite(null)]
    extreme = int(np.sum(np.abs(finite) >= abs(observed) - 1e-12))
    return {
        "test": "within_pair_arm_swap_permutation",
        "draws": int(finite.size),
        "extreme_draws": extreme,
        "two_sided_p_value": (extreme + 1) / (finite.size + 1),
        "p_note": "resolution_floor_reached" if extreme == 0 else "add_one_estimator",
    }


def discordant_pairs(pairs: list[PairOutcome]) -> JsonObject:
    """Count pairs where exactly one arm lost a span, the paired signal McNemar would use."""
    case_only = sum(1 for p in pairs if p.case.spans_lost > 0 and p.control.spans_lost == 0)
    control_only = sum(1 for p in pairs if p.control.spans_lost > 0 and p.case.spans_lost == 0)
    both = sum(1 for p in pairs if p.case.spans_lost > 0 and p.control.spans_lost > 0)
    neither = sum(1 for p in pairs if p.case.spans_lost == 0 and p.control.spans_lost == 0)
    discordant = case_only + control_only
    statistic = ((abs(case_only - control_only) - 1) ** 2) / discordant if discordant else math.nan
    return {
        "dialect_arm_only_lost": case_only,
        "control_arm_only_lost": control_only,
        "both_lost": both,
        "neither_lost": neither,
        "discordant_pairs": discordant,
        "mcnemar_chi2_continuity_corrected": statistic,
        "mcnemar_p_approx": math.erfc(math.sqrt(statistic / 2)) if discordant and statistic >= 0 else None,
    }


def analyze(pairs: list[PairOutcome], model: str) -> JsonObject:
    rng = np.random.default_rng(RANDOM_SEED)
    return {
        "model": model,
        "pairs": len(pairs),
        "distinct_speakers": len({pair.speaker_key for pair in pairs}),
        "cohort_counts": dict(Counter(pair.cohort for pair in pairs).most_common()),
        "dialect_arm_spans": sum(pair.case.spans_total for pair in pairs),
        "control_arm_spans": sum(pair.control.spans_total for pair in pairs),
        "critical_span_loss": paired_bootstrap(pairs, "spans_lost", "spans_total", rng, BOOTSTRAP_DRAWS),
        "critical_span_permutation": sign_flip_permutation(pairs, "spans_lost", "spans_total", rng, PERMUTATION_DRAWS),
        "mcnemar": discordant_pairs(pairs),
        "placebo_plain_unit_error": paired_bootstrap(pairs, "plain_error", "plain_total", rng, BOOTSTRAP_DRAWS),
    }


def format_block(result: JsonObject) -> str:
    loss = result["critical_span_loss"]
    placebo = result["placebo_plain_unit_error"]
    permutation = result["critical_span_permutation"]
    mcnemar = result["mcnemar"]
    assert isinstance(loss, dict) and isinstance(placebo, dict)
    assert isinstance(permutation, dict) and isinstance(mcnemar, dict)
    ci = loss["difference_ci95"]
    placebo_ci = placebo["difference_ci95"]
    assert isinstance(ci, dict) and isinstance(placebo_ci, dict)
    return "\n".join(
        [
            f"## {result['model']}",
            "",
            f"- Pairs: {result['pairs']} across {result['distinct_speakers']} speakers",
            f"- Scorable critical spans: {result['dialect_arm_spans']} dialect arm, "
            f"{result['control_arm_spans']} control arm",
            f"- Critical-span loss: {float(loss['case_rate']):.3f} dialect vs "
            f"{float(loss['control_rate']):.3f} control",
            f"- Paired difference: {float(loss['difference']):+.3f}, "
            f"95% CI [{float(ci['low']):.3f}, {float(ci['high']):.3f}]"
            f"{' — crosses zero' if loss['crosses_zero'] else ' — excludes zero'}",
            f"- Arm-swap permutation p: "
            f"{'<' if permutation['extreme_draws'] == 0 else ''}"
            f"{float(permutation['two_sided_p_value']):.3e}",
            f"- Discordant pairs: {mcnemar['dialect_arm_only_lost']} dialect-only vs "
            f"{mcnemar['control_arm_only_lost']} control-only"
            + (
                f", McNemar p {float(mcnemar['mcnemar_p_approx']):.3f}"
                if mcnemar.get("mcnemar_p_approx") is not None
                else ""
            ),
            f"- Placebo, non-dialect unit error: {float(placebo['case_rate']):.3f} vs "
            f"{float(placebo['control_rate']):.3f}, difference {float(placebo['difference']):+.3f} "
            f"95% CI [{float(placebo_ci['low']):.3f}, {float(placebo_ci['high']):.3f}]"
            f"{' — crosses zero' if placebo['crosses_zero'] else ' — EXCLUDES ZERO, matching is suspect'}",
            "",
        ],
    )


def write_readme(output_dir: Path, results: list[JsonObject]) -> None:
    header = (
        "# Dialect Control Pair Comparison\n\n"
        "Does dialect marking in an utterance raise AICC critical-span loss? Earlier rounds asked this by\n"
        "checking whether a critical span's surface sat on a dialect eojeol, which never had more than five\n"
        "usable observations. This asks it at utterance level, paired within speaker.\n\n"
        "Each pair is one speaker in one recording: a dialect-bearing utterance and a length-matched\n"
        "dialect-free utterance, both carrying critical spans. The paired difference removes speaker ability\n"
        "and recording quality.\n\n"
        "Read the placebo line first. Non-dialect unit error should be similar in both arms; if it is not,\n"
        "the pairs differ in something beyond dialect marking and the critical-span number means little.\n\n"
        "Labels are weak preannotations that no human has reviewed.\n\n"
    )
    (output_dir / "README.md").write_text(header + "\n".join(format_block(result) for result in results), encoding="utf-8")


def write_outputs(results: list[JsonObject], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary: JsonObject = {
        "analysis": "within_speaker_paired_dialect_versus_control",
        "random_seed": RANDOM_SEED,
        "label_status": "weak_preannotation_not_gold",
        "results": list(results),
        "numpy_version": np.__version__,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_readme(output_dir, results)


@app.command()
def main(
    pair_manifest_path: Annotated[Path, typer.Argument(help="Pair manifest JSONL.")],
    case_dir: Annotated[Path, typer.Option("--case-dir")],
    case_annotations: Annotated[Path, typer.Option("--case-annotations")],
    control_dir: Annotated[Path, typer.Option("--control-dir")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
) -> None:
    if not pair_manifest_path.exists():
        console.print(f"Pair manifest not found: {pair_manifest_path}")
        raise typer.Exit(code=2)
    pair_rows = load_jsonl(pair_manifest_path)
    case_manifest = index_by(load_jsonl(case_dir / "asr_input_manifest.local.jsonl"), "review_id")
    control_manifest = index_by(load_jsonl(control_dir / "asr_input_manifest.local.jsonl"), "review_id")
    case_annotation_rows = index_by(load_jsonl(case_annotations), "utterance_id")
    control_annotation_rows = index_by(load_jsonl(control_dir / "control_annotations.local.jsonl"), "utterance_id")
    results: list[JsonObject] = []
    for model in MODELS:
        case_asr_path = case_dir / f"{model}.local.jsonl"
        control_asr_path = control_dir / f"{model}.local.jsonl"
        if not case_asr_path.exists() or not control_asr_path.exists():
            console.print(f"Skipping {model}: ASR output missing on one side")
            continue
        pairs = build_pairs(
            pair_rows,
            case_manifest,
            case_annotation_rows,
            index_by(load_jsonl(case_asr_path), "review_id"),
            control_manifest,
            control_annotation_rows,
            index_by(load_jsonl(control_asr_path), "review_id"),
        )
        if not pairs:
            console.print(f"Skipping {model}: no pairs resolved")
            continue
        results.append(analyze(pairs, model))
    if not results:
        console.print("No model could be compared.")
        raise typer.Exit(code=1)
    write_outputs(results, output_dir)
    console.print(f"Compared {len(results)} model(s) into {output_dir}")


if __name__ == "__main__":
    app()
