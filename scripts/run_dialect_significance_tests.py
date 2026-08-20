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
#      uv run scripts/run_dialect_significance_tests.py research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_medium.local.jsonl --output-dir research/experiments/runs/aihub_119_dialect_significance
# ──────────────────

"""Utterance-clustered significance tests for the dialect attribution probe.

The first probe compared dialect-marked and non-dialect eojeol error rates with a
two-proportion z-test. That test assumes independent units, but units are nested in
utterances, so it understates uncertainty. This script re-tests the same contrast with:

- an utterance-level cluster bootstrap, which keeps units from one utterance together;
- an exact conditional permutation test that reshuffles the dialect flag inside each
  utterance, which controls for utterance-level difficulty;
- a Mantel-Haenszel odds ratio stratified by utterance.
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
from build_dialect_taxonomy import JsonValue, list_of_mappings, text_field
from rich.console import Console

JsonObject: TypeAlias = dict[str, JsonValue]

BOOTSTRAP_DRAWS: Final[int] = 10000
PERMUTATION_DRAWS: Final[int] = 20000
RANDOM_SEED: Final[int] = 20260817

app = typer.Typer(add_completion=False)
console = Console()


@dataclass(frozen=True, slots=True)
class Cluster:
    """One utterance: dialect and non-dialect unit counts with their error counts."""

    review_id: str
    cohort: str
    dialect_total: int
    dialect_error: int
    plain_total: int
    plain_error: int


@dataclass(frozen=True, slots=True)
class Rates:
    dialect_error_rate: float
    plain_error_rate: float
    difference: float
    ratio: float
    odds_ratio: float


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


def carries(hypothesis: str, value: str) -> bool:
    """True when some hypothesis eojeol opens with this reference surface.

    Plain substring containment was the original rule and it is not safe here. Half of the dialect
    units and a fifth of the non-dialect units are a single syllable, and a single syllable turns up
    inside unrelated words constantly, so containment credits recognitions that never happened. It
    does so unevenly too: units judged against two accepted surfaces gain less from the loophole than
    units judged against one, which quietly widened the dialect-versus-plain gap. Requiring the eojeol
    boundary removes that.
    """
    needle = normalized(value)
    return bool(needle) and any(normalized(token).startswith(needle) for token in hypothesis.split() if normalized(token))


def cluster_for(row: JsonObject, hypothesis: str) -> Cluster:
    """Apply the same unit-outcome rule as the dialect attribution probe.

    A dialect unit counts as correct when the hypothesis carries either the dialect
    surface or its standard form. A non-dialect unit counts as correct only when the
    hypothesis carries the standard surface. The rule is deliberately generous toward
    dialect units, so a higher dialect error rate is not an artifact of the rule.
    """
    dialect_units = list_of_mappings(row.get("dialect_units"))
    plain_units = list_of_mappings(row.get("plain_units"))
    dialect_error = sum(
        1
        for unit in dialect_units
        if not carries(hypothesis, text_field(unit, "dialect")) and not carries(hypothesis, text_field(unit, "standard"))
    )
    plain_error = sum(1 for unit in plain_units if not carries(hypothesis, text_field(unit, "standard")))
    return Cluster(
        review_id=text_field(row, "review_id"),
        cohort=text_field(row, "cohort"),
        dialect_total=len(dialect_units),
        dialect_error=dialect_error,
        plain_total=len(plain_units),
        plain_error=plain_error,
    )


def asr_index(rows: list[JsonObject]) -> dict[str, JsonObject]:
    return {text_field(row, "review_id") or text_field(row, "utterance_id"): row for row in rows}


def build_clusters(manifest_rows: list[JsonObject], asr_rows: list[JsonObject]) -> tuple[list[Cluster], int]:
    outputs = asr_index(asr_rows)
    clusters: list[Cluster] = []
    missing = 0
    for row in manifest_rows:
        output = outputs.get(text_field(row, "review_id")) or outputs.get(text_field(row, "utterance_id"))
        if output is None:
            missing += 1
            continue
        clusters.append(cluster_for(row, text_field(output, "hypothesis")))
    return clusters, missing


def columns(clusters: list[Cluster]) -> dict[str, np.ndarray]:
    return {
        "dialect_total": np.array([c.dialect_total for c in clusters], dtype=np.int64),
        "dialect_error": np.array([c.dialect_error for c in clusters], dtype=np.int64),
        "plain_total": np.array([c.plain_total for c in clusters], dtype=np.int64),
        "plain_error": np.array([c.plain_error for c in clusters], dtype=np.int64),
    }


def rates_from_totals(
    dialect_error: float,
    dialect_total: float,
    plain_error: float,
    plain_total: float,
) -> Rates:
    dialect_rate = dialect_error / dialect_total if dialect_total else math.nan
    plain_rate = plain_error / plain_total if plain_total else math.nan
    dialect_ok = dialect_total - dialect_error
    plain_ok = plain_total - plain_error
    odds = (dialect_error * plain_ok) / (plain_error * dialect_ok) if plain_error and dialect_ok else math.nan
    return Rates(
        dialect_error_rate=dialect_rate,
        plain_error_rate=plain_rate,
        difference=dialect_rate - plain_rate,
        ratio=dialect_rate / plain_rate if plain_rate else math.nan,
        odds_ratio=odds,
    )


def observed_rates(data: dict[str, np.ndarray]) -> Rates:
    return rates_from_totals(
        float(data["dialect_error"].sum()),
        float(data["dialect_total"].sum()),
        float(data["plain_error"].sum()),
        float(data["plain_total"].sum()),
    )


def percentile_interval(samples: np.ndarray) -> JsonObject:
    finite = samples[np.isfinite(samples)]
    if finite.size == 0:
        return {"low": None, "high": None, "draws_used": 0}
    low, high = np.percentile(finite, [2.5, 97.5])
    return {"low": float(low), "high": float(high), "draws_used": int(finite.size)}


def cluster_bootstrap(data: dict[str, np.ndarray], rng: np.random.Generator, draws: int) -> JsonObject:
    """Resample utterances with replacement so units from one utterance move together."""
    cluster_count = data["dialect_total"].size
    picks = rng.integers(0, cluster_count, size=(draws, cluster_count))
    dialect_error = data["dialect_error"][picks].sum(axis=1).astype(np.float64)
    dialect_total = data["dialect_total"][picks].sum(axis=1).astype(np.float64)
    plain_error = data["plain_error"][picks].sum(axis=1).astype(np.float64)
    plain_total = data["plain_total"][picks].sum(axis=1).astype(np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        dialect_rate = dialect_error / dialect_total
        plain_rate = plain_error / plain_total
        difference = dialect_rate - plain_rate
        ratio = dialect_rate / plain_rate
        odds = (dialect_error * (plain_total - plain_error)) / (plain_error * (dialect_total - dialect_error))
    return {
        "draws": draws,
        "dialect_error_rate_ci95": percentile_interval(dialect_rate),
        "plain_error_rate_ci95": percentile_interval(plain_rate),
        "difference_ci95": percentile_interval(difference),
        "ratio_ci95": percentile_interval(ratio),
        "odds_ratio_ci95": percentile_interval(odds),
        "difference_bootstrap_se": float(np.std(difference[np.isfinite(difference)], ddof=1)),
        "difference_draws_at_or_below_zero": int(np.sum(difference[np.isfinite(difference)] <= 0)),
    }


def permutation_test(data: dict[str, np.ndarray], rng: np.random.Generator, draws: int) -> JsonObject:
    """Reshuffle the dialect flag inside each utterance, holding per-utterance counts fixed.

    Conditional on each utterance's unit count and error count, the number of errors that
    land on dialect units is hypergeometric. Sampling it directly is an exact permutation
    of the dialect flag within the utterance, so utterance difficulty cannot drive the result.
    """
    unit_total = data["dialect_total"] + data["plain_total"]
    error_total = data["dialect_error"] + data["plain_error"]
    dialect_total = float(data["dialect_total"].sum())
    plain_total = float(data["plain_total"].sum())
    informative = np.sum((data["dialect_total"] > 0) & (data["plain_total"] > 0) & (error_total > 0))
    good = error_total
    bad = unit_total - error_total
    sampled = rng.hypergeometric(
        np.broadcast_to(good, (draws, good.size)),
        np.broadcast_to(bad, (draws, bad.size)),
        np.broadcast_to(data["dialect_total"], (draws, data["dialect_total"].size)),
    )
    dialect_error = sampled.sum(axis=1).astype(np.float64)
    plain_error = float(error_total.sum()) - dialect_error
    null_difference = (dialect_error / dialect_total) - (plain_error / plain_total)
    observed = observed_rates(data).difference
    extreme = int(np.sum(np.abs(null_difference) >= abs(observed) - 1e-12))
    return {
        "draws": draws,
        "test": "within_utterance_conditional_permutation_of_dialect_flag",
        "observed_difference": observed,
        "null_difference_mean": float(np.mean(null_difference)),
        "null_difference_sd": float(np.std(null_difference, ddof=1)),
        # The null mean is not zero: dialect units sit in slightly harder utterances, so some of the
        # raw gap is utterance composition rather than dialect marking. The excess is what survives that.
        "composition_adjusted_difference": observed - float(np.mean(null_difference)),
        "composition_share_of_raw_difference": float(np.mean(null_difference)) / observed if observed else math.nan,
        "informative_utterances": int(informative),
        "extreme_draws": extreme,
        "two_sided_p_value": (extreme + 1) / (draws + 1),
        "p_value_note": (
            "no_null_draw_reached_the_observed_gap_so_the_reported_p_is_the_resolution_floor"
            if extreme == 0
            else "add_one_estimator"
        ),
    }


def mantel_haenszel(data: dict[str, np.ndarray]) -> JsonObject:
    """Utterance-stratified odds ratio with Robins-Breslow-Greenland variance."""
    a = data["dialect_error"].astype(np.float64)
    b = (data["dialect_total"] - data["dialect_error"]).astype(np.float64)
    c = data["plain_error"].astype(np.float64)
    d = (data["plain_total"] - data["plain_error"]).astype(np.float64)
    n = a + b + c + d
    usable = n > 0
    a, b, c, d, n = a[usable], b[usable], c[usable], d[usable], n[usable]
    r = a * d / n
    s = b * c / n
    r_sum, s_sum = float(r.sum()), float(s.sum())
    if r_sum <= 0 or s_sum <= 0:
        return {"odds_ratio": None, "note": "undefined_mantel_haenszel_estimate"}
    p = (a + d) / n
    q = (b + c) / n
    variance = (
        float((p * r).sum()) / (2 * r_sum**2)
        + float((p * s + q * r).sum()) / (2 * r_sum * s_sum)
        + float((q * s).sum()) / (2 * s_sum**2)
    )
    estimate = r_sum / s_sum
    se = math.sqrt(variance)
    z = math.log(estimate) / se if se > 0 else math.nan
    return {
        "odds_ratio": estimate,
        "log_odds_ratio_se": se,
        "ci95": {"low": math.exp(math.log(estimate) - 1.96 * se), "high": math.exp(math.log(estimate) + 1.96 * se)},
        "z": z,
        "two_sided_p_approx": math.erfc(abs(z) / math.sqrt(2)) if math.isfinite(z) else None,
        "strata_used": int(usable.sum()),
    }


def naive_two_proportion(data: dict[str, np.ndarray]) -> JsonObject:
    """The original unit-independent test, kept so the correction is auditable."""
    dialect_error = float(data["dialect_error"].sum())
    dialect_total = float(data["dialect_total"].sum())
    plain_error = float(data["plain_error"].sum())
    plain_total = float(data["plain_total"].sum())
    pooled = (dialect_error + plain_error) / (dialect_total + plain_total)
    se = math.sqrt(pooled * (1 - pooled) * (1 / dialect_total + 1 / plain_total))
    difference = dialect_error / dialect_total - plain_error / plain_total
    z = difference / se
    return {
        "test": "two_proportion_z_units_treated_as_independent",
        "z": z,
        "two_sided_p_approx": math.erfc(abs(z) / math.sqrt(2)),
        "difference_se": se,
    }


def cohort_contrast(clusters: list[Cluster], rng: np.random.Generator, draws: int) -> JsonObject:
    """Bootstrap the Busan minus non-Busan dialect error-rate gap at utterance level."""
    busan = [c for c in clusters if c.cohort == "busan"]
    other = [c for c in clusters if c.cohort != "busan"]
    if not busan or not other:
        return {"comparable": False}

    def rate(rows: list[Cluster]) -> float:
        total = sum(row.dialect_total for row in rows)
        return sum(row.dialect_error for row in rows) / total if total else math.nan

    def resample(rows: list[Cluster]) -> np.ndarray:
        error = np.array([row.dialect_error for row in rows], dtype=np.int64)
        total = np.array([row.dialect_total for row in rows], dtype=np.int64)
        picks = rng.integers(0, len(rows), size=(draws, len(rows)))
        with np.errstate(divide="ignore", invalid="ignore"):
            return error[picks].sum(axis=1) / total[picks].sum(axis=1)

    difference = resample(busan) - resample(other)
    observed = rate(busan) - rate(other)
    finite = difference[np.isfinite(difference)]
    crossings = int(np.sum(finite <= 0)) if observed > 0 else int(np.sum(finite >= 0))
    return {
        "comparable": True,
        "busan_utterances": len(busan),
        "other_utterances": len(other),
        "busan_dialect_error_rate": rate(busan),
        "other_dialect_error_rate": rate(other),
        "difference": observed,
        "difference_ci95": percentile_interval(difference),
        "bootstrap_sign_crossing_fraction": crossings / finite.size if finite.size else None,
    }


def design_effect(bootstrap: JsonObject, naive: JsonObject) -> float:
    match (bootstrap.get("difference_bootstrap_se"), naive.get("difference_se")):
        case (float() as clustered, float() as independent) if independent > 0:
            return (clustered / independent) ** 2
        case _:
            return math.nan


def analyze(clusters: list[Cluster], missing: int, model: str, draws: int, permutations: int) -> JsonObject:
    rng = np.random.default_rng(RANDOM_SEED)
    data = columns(clusters)
    rates = observed_rates(data)
    bootstrap = cluster_bootstrap(data, rng, draws)
    permutation = permutation_test(data, rng, permutations)
    naive = naive_two_proportion(data)
    return {
        "model": model,
        "utterances": len(clusters),
        "missing_asr_outputs": missing,
        "dialect_units": int(data["dialect_total"].sum()),
        "plain_units": int(data["plain_total"].sum()),
        "dialect_error_units": int(data["dialect_error"].sum()),
        "plain_error_units": int(data["plain_error"].sum()),
        "point_estimates": {
            "dialect_unit_error_rate": rates.dialect_error_rate,
            "plain_unit_error_rate": rates.plain_error_rate,
            "difference": rates.difference,
            "ratio": rates.ratio,
            "odds_ratio_pooled": rates.odds_ratio,
        },
        "cluster_bootstrap": bootstrap,
        "permutation_test": permutation,
        "mantel_haenszel_by_utterance": mantel_haenszel(data),
        "naive_unit_independent_test": naive,
        "design_effect_vs_naive": design_effect(bootstrap, naive),
        "cohort_contrast": cohort_contrast(clusters, rng, draws),
        "unit_outcome_rule": "dialect_unit_correct_if_dialect_or_standard_surface_present_plain_unit_correct_if_standard_surface_present",
    }


def model_label(asr_rows: list[JsonObject], path: Path) -> str:
    labels = Counter(text_field(row, "model") for row in asr_rows if text_field(row, "model"))
    return labels.most_common(1)[0][0] if labels else path.stem


def format_ci(interval: JsonValue) -> str:
    match interval:
        case {"low": float() as low, "high": float() as high}:
            return f"[{low:.3f}, {high:.3f}]"
        case _:
            return "[n/a]"


def report_section(result: JsonObject) -> str:
    point = result["point_estimates"]
    bootstrap = result["cluster_bootstrap"]
    permutation = result["permutation_test"]
    mh = result["mantel_haenszel_by_utterance"]
    naive = result["naive_unit_independent_test"]
    assert isinstance(point, dict) and isinstance(bootstrap, dict)
    assert isinstance(permutation, dict) and isinstance(mh, dict) and isinstance(naive, dict)
    cohort = result["cohort_contrast"]
    lines = [
        f"## {result['model']}",
        "",
        f"- Utterances (clusters): {result['utterances']}",
        f"- Dialect units: {result['dialect_units']}, non-dialect units: {result['plain_units']}",
        f"- Dialect unit error rate: {float(point['dialect_unit_error_rate']):.3f}, "
        f"cluster bootstrap 95% CI {format_ci(bootstrap['dialect_error_rate_ci95'])}",
        f"- Non-dialect unit error rate: {float(point['plain_unit_error_rate']):.3f}, "
        f"cluster bootstrap 95% CI {format_ci(bootstrap['plain_error_rate_ci95'])}",
        f"- Difference: {float(point['difference']):.3f}, "
        f"cluster bootstrap 95% CI {format_ci(bootstrap['difference_ci95'])}",
        f"- Ratio: {float(point['ratio']):.2f}x, cluster bootstrap 95% CI {format_ci(bootstrap['ratio_ci95'])}",
        f"- Mantel-Haenszel odds ratio stratified by utterance: "
        f"{float(mh['odds_ratio']):.2f} 95% CI {format_ci(mh['ci95'])}"
        if mh.get("odds_ratio") is not None
        else "- Mantel-Haenszel odds ratio: undefined",
        f"- Within-utterance permutation p: "
        f"{'<' if permutation['extreme_draws'] == 0 else ''}{float(permutation['two_sided_p_value']):.2e} "
        f"({permutation['draws']} draws, {permutation['informative_utterances']} informative utterances, "
        f"{permutation['extreme_draws']} draws at or beyond the observed gap)",
        f"- Utterance composition alone explains a gap of {float(permutation['null_difference_mean']):.3f}, "
        f"which is {float(permutation['composition_share_of_raw_difference']):.0%} of the raw gap; "
        f"the dialect-attributable excess is {float(permutation['composition_adjusted_difference']):.3f}",
        f"- Naive unit-independent p: {float(naive['two_sided_p_approx']):.2e} "
        f"(design effect vs cluster bootstrap: {float(result['design_effect_vs_naive']):.2f})",
    ]
    if isinstance(cohort, dict) and cohort.get("comparable"):
        lines.extend(
            [
                "",
                f"- Busan dialect unit error rate: {float(cohort['busan_dialect_error_rate']):.3f} "
                f"({cohort['busan_utterances']} utterances)",
                f"- Non-Busan Gyeongsang dialect unit error rate: {float(cohort['other_dialect_error_rate']):.3f} "
                f"({cohort['other_utterances']} utterances)",
                f"- Cohort difference: {float(cohort['difference']):.3f}, "
                f"cluster bootstrap 95% CI {format_ci(cohort['difference_ci95'])}",
            ],
        )
    lines.append("")
    return "\n".join(lines)


def write_readme(output_dir: Path, results: list[JsonObject]) -> None:
    header = (
        "# Dialect Attribution Significance Tests\n\n"
        "The first probe compared dialect-marked and non-dialect eojeol error rates with a two-proportion\n"
        "z-test over units. Units are nested in utterances, so that test overstates the evidence. This run\n"
        "re-tests the same contrast three ways that respect the utterance clustering:\n\n"
        "1. Utterance-level cluster bootstrap: resamples whole utterances, so units from one utterance stay together.\n"
        "2. Within-utterance conditional permutation: reshuffles the dialect flag inside each utterance while\n"
        "   holding that utterance's unit count and error count fixed, so utterance difficulty cannot drive the gap.\n"
        "3. Mantel-Haenszel odds ratio stratified by utterance.\n\n"
        "The unit outcome rule is unchanged and favours dialect units: a dialect unit counts as correct when the\n"
        "hypothesis carries either the dialect surface or its standard form, while a non-dialect unit counts as\n"
        "correct only on the standard surface.\n\n"
        "Outputs carry counts and statistics only, with no transcript text.\n\n"
    )
    body = "\n".join(report_section(result) for result in results)
    (output_dir / "README.md").write_text(header + body, encoding="utf-8")


def write_outputs(results: list[JsonObject], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary: JsonObject = {
        "analysis": "utterance_clustered_significance_tests",
        "random_seed": RANDOM_SEED,
        "models": [result["model"] for result in results],
        "results": list(results),
        "numpy_version": np.__version__,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_readme(output_dir, results)


@app.command()
def main(
    manifest_path: Annotated[Path, typer.Argument(help="ASR input manifest local JSONL.")],
    asr_paths: Annotated[list[Path], typer.Argument(help="One or more ASR output local JSONL files.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
    bootstrap_draws: Annotated[int, typer.Option("--bootstrap-draws", min=1000)] = BOOTSTRAP_DRAWS,
    permutation_draws: Annotated[int, typer.Option("--permutation-draws", min=1000)] = PERMUTATION_DRAWS,
) -> None:
    if not manifest_path.exists():
        console.print(f"Manifest not found: {manifest_path}")
        raise typer.Exit(code=2)
    missing_inputs = [path for path in asr_paths if not path.exists()]
    if missing_inputs:
        console.print(f"ASR output not found: {missing_inputs[0]}")
        raise typer.Exit(code=2)
    manifest_rows = load_jsonl(manifest_path)
    results: list[JsonObject] = []
    for path in asr_paths:
        asr_rows = load_jsonl(path)
        clusters, missing = build_clusters(manifest_rows, asr_rows)
        if not clusters:
            console.print(f"No overlapping utterances between manifest and {path}")
            raise typer.Exit(code=1)
        results.append(analyze(clusters, missing, model_label(asr_rows, path), bootstrap_draws, permutation_draws))
    write_outputs(results, output_dir)
    console.print(f"Wrote {len(results)} model result(s) to {output_dir}")


if __name__ == "__main__":
    app()
