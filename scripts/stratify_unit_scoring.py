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
#      uv run scripts/stratify_unit_scoring.py research/experiments/runs/aihub_119_speaker_independent_split --output-dir research/experiments/runs/aihub_119_stratified_holdout
# ──────────────────

"""Check whether the dialect penalty holds inside speaker subgroups.

The holdout is skewed: 228 women to 72 men, and 205 of 300 speakers in their twenties. That skew
cannot confound the headline contrast, because the contrast is within-utterance. Every utterance
supplies both its dialect-marked and its non-dialect units, so the speaker, their sex, their age, and
the recording are identical on both sides of the comparison by construction.

What the skew does threaten is generality. If the penalty only appeared in young women, the number
would not travel. This splits the same aligned scoring by sex, age band, and cohort and reports the
dialect-minus-plain gap inside each stratum with an utterance-level bootstrap.

Read the small strata as descriptive. Three speakers aged sixty or older cannot support an interval.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Annotated, Final, TypeAlias, assert_never

import numpy as np
import typer
from build_dialect_taxonomy import JsonValue, text_field
from rich.console import Console
from run_dialect_significance_tests import Cluster
from score_units_by_alignment import build_clusters, load_jsonl

JsonObject: TypeAlias = dict[str, JsonValue]

MODELS: Final[tuple[str, ...]] = ("faster_whisper_medium", "faster_whisper_large_v3", "wav2vec2_korean")
BOOTSTRAP_DRAWS: Final[int] = 10000
RANDOM_SEED: Final[int] = 20260821
MIN_UTTERANCES: Final[int] = 20

app = typer.Typer(add_completion=False)
console = Console()


def rate(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else float("nan")


def stratum_stats(clusters: list[Cluster], rng: np.random.Generator, draws: int) -> JsonObject:
    dialect_error = np.array([c.dialect_error for c in clusters], dtype=np.float64)
    dialect_total = np.array([c.dialect_total for c in clusters], dtype=np.float64)
    plain_error = np.array([c.plain_error for c in clusters], dtype=np.float64)
    plain_total = np.array([c.plain_total for c in clusters], dtype=np.float64)
    dialect_rate = rate(dialect_error.sum(), dialect_total.sum())
    plain_rate = rate(plain_error.sum(), plain_total.sum())
    block: JsonObject = {
        "utterances": len(clusters),
        "dialect_units": int(dialect_total.sum()),
        "plain_units": int(plain_total.sum()),
        "dialect_error_rate": dialect_rate,
        "plain_error_rate": plain_rate,
        "difference": dialect_rate - plain_rate,
        "ratio": dialect_rate / plain_rate if plain_rate else float("nan"),
        "interval_reported": len(clusters) >= MIN_UTTERANCES,
    }
    if len(clusters) < MIN_UTTERANCES:
        block["note"] = f"fewer_than_{MIN_UTTERANCES}_utterances_descriptive_only"
        return block
    picks = rng.integers(0, len(clusters), size=(draws, len(clusters)))
    with np.errstate(divide="ignore", invalid="ignore"):
        differences = (dialect_error[picks].sum(axis=1) / dialect_total[picks].sum(axis=1)) - (
            plain_error[picks].sum(axis=1) / plain_total[picks].sum(axis=1)
        )
    finite = differences[np.isfinite(differences)]
    low, high = np.percentile(finite, [2.5, 97.5])
    block["difference_ci95"] = {"low": float(low), "high": float(high)}
    block["excludes_zero"] = bool(low > 0 or high < 0)
    return block


def analyze(clusters: list[Cluster], attributes: dict[str, JsonObject], model: str) -> JsonObject:
    rng = np.random.default_rng(RANDOM_SEED)
    strata: dict[str, dict[str, list[Cluster]]] = {"sex": defaultdict(list), "age_band": defaultdict(list), "cohort": defaultdict(list)}
    for cluster in clusters:
        row = attributes.get(cluster.review_id)
        if row is None:
            continue
        strata["sex"][text_field(row, "sex") or "unknown"].append(cluster)
        strata["age_band"][text_field(row, "age_band") or "unknown"].append(cluster)
        strata["cohort"][cluster.cohort].append(cluster)
    return {
        "model": model,
        "overall": stratum_stats(clusters, rng, BOOTSTRAP_DRAWS),
        "by_sex": {name: stratum_stats(rows, rng, BOOTSTRAP_DRAWS) for name, rows in sorted(strata["sex"].items(), key=lambda kv: -len(kv[1]))},
        "by_age_band": {name: stratum_stats(rows, rng, BOOTSTRAP_DRAWS) for name, rows in sorted(strata["age_band"].items(), key=lambda kv: -len(kv[1]))},
        "by_cohort": {name: stratum_stats(rows, rng, BOOTSTRAP_DRAWS) for name, rows in sorted(strata["cohort"].items(), key=lambda kv: -len(kv[1]))},
    }


def stratum_rows(block: JsonObject) -> str:
    lines: list[str] = []
    for name, stats in block.items():
        if not isinstance(stats, dict):
            continue
        interval = stats.get("difference_ci95")
        if isinstance(interval, dict):
            span = f"[{float(interval['low']):.3f}, {float(interval['high']):.3f}]"
            verdict = "excludes zero" if stats.get("excludes_zero") else "crosses zero"
        else:
            span = "descriptive only"
            verdict = f"n={stats['utterances']}"
        lines.append(
            f"| {name} | {stats['utterances']} | {float(stats['dialect_error_rate']):.3f} | "
            f"{float(stats['plain_error_rate']):.3f} | {float(stats['difference']):+.3f} | "
            f"{float(stats['ratio']):.2f}x | {span} | {verdict} |",
        )
    return "\n".join(lines)


def format_block(result: JsonObject) -> str:
    header = "| Stratum | Utterances | Dialect | Plain | Difference | Ratio | 95% CI | |\n|---|---:|---:|---:|---:|---:|---|---|"
    sections: list[str] = [f"## {result['model']}", ""]
    for title, key in (("By sex", "by_sex"), ("By age band", "by_age_band"), ("By cohort", "by_cohort")):
        block = result[key]
        assert isinstance(block, dict)
        sections.extend([f"### {title}", "", header, stratum_rows(block), ""])
    overall = result["overall"]
    assert isinstance(overall, dict)
    sections.extend(
        [
            f"Overall: dialect {float(overall['dialect_error_rate']):.3f}, plain "
            f"{float(overall['plain_error_rate']):.3f}, difference {float(overall['difference']):+.3f}, "
            f"ratio {float(overall['ratio']):.2f}x.",
            "",
        ],
    )
    return "\n".join(sections)


def write_outputs(results: list[JsonObject], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    header = (
        "# Stratified Unit Scoring\n\n"
        "The holdout is skewed: 228 women to 72 men, and 205 of its 300 speakers are in their twenties.\n"
        "That skew cannot confound the headline contrast, because the contrast lives inside each utterance.\n"
        "Every utterance supplies both its dialect-marked and its non-dialect units, so speaker, sex, age,\n"
        "and recording are identical on both sides by construction.\n\n"
        "What the skew threatens is generality. This splits the same alignment-scored data by sex, age band,\n"
        "and cohort, and reports the dialect-minus-plain gap inside each stratum.\n\n"
        f"Strata with fewer than {MIN_UTTERANCES} utterances are descriptive only and carry no interval.\n\n"
    )
    (output_dir / "README.md").write_text(header + "\n".join(format_block(r) for r in results), encoding="utf-8")
    summary: JsonObject = {
        "analysis": "stratified_aligned_unit_scoring",
        "random_seed": RANDOM_SEED,
        "min_utterances_for_interval": MIN_UTTERANCES,
        "design_note": "the dialect versus plain contrast is within-utterance, so speaker attributes are held fixed by construction",
        "results": list(results),
        "numpy_version": np.__version__,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@app.command()
def main(
    split_dir: Annotated[Path, typer.Argument(help="Split directory holding the manifest, ASR outputs, and split manifest.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
    label_root: Annotated[Path, typer.Option("--label-root")] = Path("data/raw/aihub_gyeongsang_119"),
) -> None:
    manifest_path = split_dir / "asr_input_manifest.local.jsonl"
    split_manifest_path = split_dir / "split_manifest.jsonl"
    for path in (manifest_path, split_manifest_path):
        if not path.exists():
            console.print(f"Input not found: {path}")
            raise typer.Exit(code=2)
    manifest_rows = load_jsonl(manifest_path)
    attributes = {text_field(row, "review_id"): row for row in load_jsonl(split_manifest_path)}
    results: list[JsonObject] = []
    for model in MODELS:
        asr_path = split_dir / f"{model}.local.jsonl"
        if not asr_path.exists():
            console.print(f"Skipping {model}: ASR output missing")
            continue
        clusters, _ = build_clusters(manifest_rows, load_jsonl(asr_path), label_root)
        if clusters:
            results.append(analyze(clusters, attributes, model))
    if not results:
        console.print("No model could be scored.")
        raise typer.Exit(code=1)
    write_outputs(results, output_dir)
    console.print(f"Stratified {len(results)} model(s) into {output_dir}")


if __name__ == "__main__":
    app()
