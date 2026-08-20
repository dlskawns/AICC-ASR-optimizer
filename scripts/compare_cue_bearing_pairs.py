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
#      uv run scripts/compare_cue_bearing_pairs.py research/experiments/runs/aihub_119_cue_bearing_split --output-dir research/experiments/runs/aihub_119_cue_bearing_comparison
# ──────────────────

"""Does an AICC cue survive worse when the cue word itself is dialect-marked?

This is the sharp version of the question the project has been circling. Round 5 compared utterances
that contained dialect marking somewhere against utterances that contained none, and found nothing.
That pointed to dialect fragility being local to the dialect token. If that is right, the effect should
appear when the cue word *is* the dialect token.

Each pair is one speaker producing the same cue category twice: once on a dialect-marked eojeol, once
on a plain one. Speaker, recording, and cue category are fixed inside the pair.

The placebo is the non-dialect unit error rate of the two utterances. It should not differ between arms.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
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
class Arm:
    cue_scorable: int
    cue_lost: int
    plain_total: int
    plain_error: int


@dataclass(frozen=True, slots=True)
class Pair:
    speaker_key: str
    cohort: str
    category: str
    dialect_arm: Arm
    plain_arm: Arm


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


def contains(hypothesis: str, value: str) -> bool:
    needle = normalized(value)
    return bool(needle) and needle in normalized(hypothesis)


def arm_outcome(manifest_row: JsonObject, annotation: JsonObject, hypothesis: str) -> Arm:
    references = [
        text_field(annotation, "standard_transcript"),
        text_field(annotation, "dialect_transcript"),
    ]
    scorable = 0
    lost = 0
    for span in list_of_mappings(annotation.get("critical_spans")):
        match_type = classify_match(hypothesis, text_field(span, "span_text"), references)
        if match_type == "phantom_label":
            continue
        scorable += 1
        if match_type == "absent":
            lost += 1
    plain_units = list_of_mappings(manifest_row.get("plain_units"))
    plain_error = sum(1 for unit in plain_units if not contains(hypothesis, text_field(unit, "standard")))
    return Arm(scorable, lost, len(plain_units), plain_error)


def build_pairs(
    pair_rows: list[JsonObject],
    manifest: dict[str, JsonObject],
    annotations: dict[str, JsonObject],
    asr: dict[str, JsonObject],
) -> list[Pair]:
    pairs: list[Pair] = []
    for row in pair_rows:
        case_id = text_field(row, "case_review_id")
        control_id = text_field(row, "control_review_id")
        if case_id not in asr or control_id not in asr:
            continue
        if case_id not in annotations or control_id not in annotations:
            continue
        pairs.append(
            Pair(
                speaker_key=text_field(row, "speaker_key"),
                cohort=text_field(row, "cohort"),
                category=text_field(row, "cue_category"),
                dialect_arm=arm_outcome(
                    manifest[case_id], annotations[case_id], text_field(asr[case_id], "hypothesis"),
                ),
                plain_arm=arm_outcome(
                    manifest[control_id], annotations[control_id], text_field(asr[control_id], "hypothesis"),
                ),
            ),
        )
    return pairs


def rate(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else math.nan


def paired_bootstrap(
    pairs: list[Pair],
    numerator: str,
    denominator: str,
    rng: np.random.Generator,
    draws: int,
) -> JsonObject:
    a_num = np.array([getattr(p.dialect_arm, numerator) for p in pairs], dtype=np.float64)
    a_den = np.array([getattr(p.dialect_arm, denominator) for p in pairs], dtype=np.float64)
    b_num = np.array([getattr(p.plain_arm, numerator) for p in pairs], dtype=np.float64)
    b_den = np.array([getattr(p.plain_arm, denominator) for p in pairs], dtype=np.float64)
    picks = rng.integers(0, len(pairs), size=(draws, len(pairs)))
    with np.errstate(divide="ignore", invalid="ignore"):
        difference = (a_num[picks].sum(axis=1) / a_den[picks].sum(axis=1)) - (
            b_num[picks].sum(axis=1) / b_den[picks].sum(axis=1)
        )
    finite = difference[np.isfinite(difference)]
    low, high = np.percentile(finite, [2.5, 97.5])
    return {
        "dialect_arm_rate": rate(float(a_num.sum()), float(a_den.sum())),
        "plain_arm_rate": rate(float(b_num.sum()), float(b_den.sum())),
        "difference": rate(float(a_num.sum()), float(a_den.sum())) - rate(float(b_num.sum()), float(b_den.sum())),
        "difference_ci95": {"low": float(low), "high": float(high)},
        "crosses_zero": bool(low <= 0 <= high),
        "draws": draws,
    }


def arm_swap_permutation(
    pairs: list[Pair],
    numerator: str,
    denominator: str,
    rng: np.random.Generator,
    draws: int,
) -> JsonObject:
    a_num = np.array([getattr(p.dialect_arm, numerator) for p in pairs], dtype=np.float64)
    a_den = np.array([getattr(p.dialect_arm, denominator) for p in pairs], dtype=np.float64)
    b_num = np.array([getattr(p.plain_arm, numerator) for p in pairs], dtype=np.float64)
    b_den = np.array([getattr(p.plain_arm, denominator) for p in pairs], dtype=np.float64)
    swap = rng.integers(0, 2, size=(draws, len(pairs))).astype(bool)
    with np.errstate(divide="ignore", invalid="ignore"):
        null = (
            np.where(swap, b_num, a_num).sum(axis=1) / np.where(swap, b_den, a_den).sum(axis=1)
        ) - (
            np.where(swap, a_num, b_num).sum(axis=1) / np.where(swap, a_den, b_den).sum(axis=1)
        )
    observed = rate(float(a_num.sum()), float(a_den.sum())) - rate(float(b_num.sum()), float(b_den.sum()))
    finite = null[np.isfinite(null)]
    extreme = int(np.sum(np.abs(finite) >= abs(observed) - 1e-12))
    return {
        "test": "within_pair_arm_swap_permutation",
        "draws": int(finite.size),
        "extreme_draws": extreme,
        "two_sided_p_value": (extreme + 1) / (finite.size + 1),
        "p_note": "resolution_floor_reached" if extreme == 0 else "add_one_estimator",
    }


def mcnemar(pairs: list[Pair]) -> JsonObject:
    dialect_only = sum(1 for p in pairs if p.dialect_arm.cue_lost > 0 and p.plain_arm.cue_lost == 0)
    plain_only = sum(1 for p in pairs if p.plain_arm.cue_lost > 0 and p.dialect_arm.cue_lost == 0)
    both = sum(1 for p in pairs if p.dialect_arm.cue_lost > 0 and p.plain_arm.cue_lost > 0)
    neither = sum(1 for p in pairs if p.dialect_arm.cue_lost == 0 and p.plain_arm.cue_lost == 0)
    discordant = dialect_only + plain_only
    statistic = ((abs(dialect_only - plain_only) - 1) ** 2) / discordant if discordant else math.nan
    return {
        "dialect_arm_only_lost": dialect_only,
        "plain_arm_only_lost": plain_only,
        "both_lost": both,
        "neither_lost": neither,
        "discordant_pairs": discordant,
        "mcnemar_chi2_continuity_corrected": statistic,
        "mcnemar_p_approx": math.erfc(math.sqrt(statistic / 2)) if discordant and statistic >= 0 else None,
    }


def by_category(pairs: list[Pair]) -> JsonObject:
    grouped: dict[str, list[Pair]] = defaultdict(list)
    for pair in pairs:
        grouped[pair.category].append(pair)
    return {
        category: {
            "pairs": len(rows),
            "dialect_arm_cue_loss": rate(
                sum(p.dialect_arm.cue_lost for p in rows), sum(p.dialect_arm.cue_scorable for p in rows),
            ),
            "plain_arm_cue_loss": rate(
                sum(p.plain_arm.cue_lost for p in rows), sum(p.plain_arm.cue_scorable for p in rows),
            ),
        }
        for category, rows in sorted(grouped.items(), key=lambda item: -len(item[1]))
    }


def analyze(pairs: list[Pair], model: str) -> JsonObject:
    rng = np.random.default_rng(RANDOM_SEED)
    return {
        "model": model,
        "pairs": len(pairs),
        "distinct_speakers": len({p.speaker_key for p in pairs}),
        "cohort_counts": dict(Counter(p.cohort for p in pairs).most_common()),
        "dialect_arm_cues": sum(p.dialect_arm.cue_scorable for p in pairs),
        "plain_arm_cues": sum(p.plain_arm.cue_scorable for p in pairs),
        "cue_loss": paired_bootstrap(pairs, "cue_lost", "cue_scorable", rng, BOOTSTRAP_DRAWS),
        "cue_permutation": arm_swap_permutation(pairs, "cue_lost", "cue_scorable", rng, PERMUTATION_DRAWS),
        "mcnemar": mcnemar(pairs),
        "cue_loss_by_category": by_category(pairs),
        "placebo_plain_unit_error": paired_bootstrap(pairs, "plain_error", "plain_total", rng, BOOTSTRAP_DRAWS),
    }


def format_block(result: JsonObject) -> str:
    loss = result["cue_loss"]
    placebo = result["placebo_plain_unit_error"]
    permutation = result["cue_permutation"]
    table = result["mcnemar"]
    assert isinstance(loss, dict) and isinstance(placebo, dict)
    assert isinstance(permutation, dict) and isinstance(table, dict)
    ci = loss["difference_ci95"]
    placebo_ci = placebo["difference_ci95"]
    categories = result["cue_loss_by_category"]
    assert isinstance(ci, dict) and isinstance(placebo_ci, dict) and isinstance(categories, dict)
    lines = [
        f"## {result['model']}",
        "",
        f"- Pairs: {result['pairs']} across {result['distinct_speakers']} speakers",
        f"- Scorable cues: {result['dialect_arm_cues']} dialect-marked arm, {result['plain_arm_cues']} plain arm",
        f"- Cue loss: {float(loss['dialect_arm_rate']):.3f} when the cue word is dialect-marked vs "
        f"{float(loss['plain_arm_rate']):.3f} when it is not",
        f"- Paired difference: {float(loss['difference']):+.3f}, "
        f"95% CI [{float(ci['low']):.3f}, {float(ci['high']):.3f}]"
        f"{' — crosses zero' if loss['crosses_zero'] else ' — excludes zero'}",
        f"- Arm-swap permutation p: "
        f"{'<' if permutation['extreme_draws'] == 0 else ''}{float(permutation['two_sided_p_value']):.3e}",
        f"- Discordant pairs: {table['dialect_arm_only_lost']} dialect-only vs {table['plain_arm_only_lost']} plain-only"
        + (
            f", McNemar p {float(table['mcnemar_p_approx']):.3e}"
            if table.get("mcnemar_p_approx") is not None
            else ""
        ),
        f"- Placebo, non-dialect unit error: {float(placebo['dialect_arm_rate']):.3f} vs "
        f"{float(placebo['plain_arm_rate']):.3f}, difference {float(placebo['difference']):+.3f} "
        f"95% CI [{float(placebo_ci['low']):.3f}, {float(placebo_ci['high']):.3f}]"
        f"{' — crosses zero' if placebo['crosses_zero'] else ' — EXCLUDES ZERO, matching is suspect'}",
        "",
        "| Cue category | Pairs | Dialect-marked arm loss | Plain arm loss |",
        "|---|---:|---:|---:|",
    ]
    lines.extend(
        f"| {name} | {stats['pairs']} | {float(stats['dialect_arm_cue_loss']):.3f} | "
        f"{float(stats['plain_arm_cue_loss']):.3f} |"
        for name, stats in categories.items()
        if isinstance(stats, dict)
    )
    lines.append("")
    return "\n".join(lines)


def write_readme(output_dir: Path, results: list[JsonObject]) -> None:
    header = (
        "# Cue-Bearing Dialect Comparison\n\n"
        "Round 5 compared utterances containing dialect marking anywhere against utterances containing none\n"
        "and found no difference in AICC critical-span loss. That pointed to dialect fragility being local to\n"
        "the dialect token, which predicts an effect when the cue word itself is the dialect-marked eojeol.\n\n"
        "Each pair here is one speaker producing the same cue category twice: once on a dialect-marked eojeol,\n"
        "once on a plain one. Speaker, recording, and cue category are fixed inside the pair.\n\n"
        "Read the placebo line first. If non-dialect unit error differs between arms, the pairs differ in more\n"
        "than the dialect marking of the cue word and the headline number cannot carry weight.\n\n"
        "Labels are weak preannotations that no human has reviewed.\n\n"
    )
    (output_dir / "README.md").write_text(header + "\n".join(format_block(r) for r in results), encoding="utf-8")


def write_outputs(results: list[JsonObject], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary: JsonObject = {
        "analysis": "within_speaker_within_category_cue_bearing_dialect_comparison",
        "random_seed": RANDOM_SEED,
        "label_status": "weak_preannotation_not_gold",
        "results": list(results),
        "numpy_version": np.__version__,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_readme(output_dir, results)


@app.command()
def main(
    split_dir: Annotated[Path, typer.Argument(help="Cue-bearing split directory.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
) -> None:
    pair_path = split_dir / "pair_manifest.jsonl"
    if not pair_path.exists():
        console.print(f"Pair manifest not found: {pair_path}")
        raise typer.Exit(code=2)
    pair_rows = load_jsonl(pair_path)
    manifest = index_by(load_jsonl(split_dir / "asr_input_manifest.local.jsonl"), "review_id")
    annotations = index_by(load_jsonl(split_dir / "cue_annotations.local.jsonl"), "review_id")
    results: list[JsonObject] = []
    for model in MODELS:
        asr_path = split_dir / f"{model}.local.jsonl"
        if not asr_path.exists():
            console.print(f"Skipping {model}: ASR output missing")
            continue
        pairs = build_pairs(pair_rows, manifest, annotations, index_by(load_jsonl(asr_path), "review_id"))
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
