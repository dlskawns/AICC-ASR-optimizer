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
#      uv run scripts/classify_cue_error_types.py research/experiments/runs/aihub_119_cue_bearing_split --output-dir research/experiments/runs/aihub_119_cue_error_types
# ──────────────────

"""Split the round 6 cue loss into harmless normalisation and real AICC damage.

Round 6 showed a dialect-marked cue word is lost far more often than a plain one. "Lost" there meant
the canonical cue string was absent from the hypothesis, which lumps together two very different
outcomes for a contact centre:

- the ASR wrote the standard form of the same cue, so the business meaning survived;
- the cue is simply gone, so the business meaning did not.

This reads the eojeol pair behind each cue out of the labels and sorts every case into
`dialect_surface_preserved`, `standard_normalised`, or `cue_absent`. Only the third is AICC damage.

It also decomposes the result by cohort, so the Busan-versus-other null from round 4 can be checked at
cue level rather than at whole-utterance level.
"""

from __future__ import annotations

import json
import math
import re
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Final, Literal, TypeAlias, assert_never

import numpy as np
import typer
from build_dialect_taxonomy import JsonValue, list_of_mappings, text_field
from rich.console import Console
from run_dialect_attribution_probe import label_index, payload_for, target_utterance

JsonObject: TypeAlias = dict[str, JsonValue]
Outcome: TypeAlias = Literal["dialect_surface_preserved", "standard_normalised", "cue_absent", "unresolved_eojeol"]

BOOTSTRAP_DRAWS: Final[int] = 10000
RANDOM_SEED: Final[int] = 20260818
MODELS: Final[tuple[str, ...]] = ("faster_whisper_medium", "faster_whisper_large_v3", "wav2vec2_korean")

app = typer.Typer(add_completion=False)
console = Console()


@dataclass(frozen=True, slots=True)
class CueCase:
    review_id: str
    arm: str
    cohort: str
    category: str
    dialect_surface: str
    standard_surface: str


@dataclass(frozen=True, slots=True)
class Scored:
    case: CueCase
    outcome: Outcome


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


def clean(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", text)


def eojeol_initial(hypothesis: str, needle: str) -> bool:
    target = clean(needle)
    return bool(target) and any(clean(token).startswith(target) for token in hypothesis.split())


def resolve_surfaces(utterance: JsonObject, evidence: str) -> tuple[str, str] | None:
    """Find the eojeol the cue was mined from and return its dialect and standard surfaces."""
    wanted = clean(evidence)
    if not wanted:
        return None
    for eojeol in list_of_mappings(utterance.get("eojeolList")):
        dialect = clean(text_field(eojeol, "eojeol"))
        standard = clean(text_field(eojeol, "standard"))
        if dialect == wanted or standard == wanted:
            return text_field(eojeol, "eojeol"), text_field(eojeol, "standard") or text_field(eojeol, "eojeol")
    return None


def classify(hypothesis: str, dialect_surface: str, standard_surface: str) -> Outcome:
    if eojeol_initial(hypothesis, dialect_surface):
        return "dialect_surface_preserved"
    if clean(standard_surface) != clean(dialect_surface) and eojeol_initial(hypothesis, standard_surface):
        return "standard_normalised"
    return "cue_absent"


def build_cases(split_dir: Path, label_root: Path) -> list[CueCase]:
    annotations = load_jsonl(split_dir / "cue_annotations.local.jsonl")
    manifest = index_by(load_jsonl(split_dir / "asr_input_manifest.local.jsonl"), "review_id")
    labels = label_index(label_root)
    payload_cache: dict[str, JsonObject] = {}
    cases: list[CueCase] = []
    for row in annotations:
        review_id = text_field(row, "review_id")
        manifest_row = manifest.get(review_id)
        if manifest_row is None:
            continue
        source_file = text_field(manifest_row, "source_file")
        if source_file not in payload_cache:
            payload_cache[source_file] = payload_for(labels, source_file)
        utterance = target_utterance(payload_cache[source_file], text_field(row, "utterance_id"))
        surfaces = resolve_surfaces(utterance, text_field(row, "cue_evidence_eojeol"))
        if surfaces is None:
            continue
        cases.append(
            CueCase(
                review_id=review_id,
                arm=text_field(row, "arm"),
                cohort=text_field(manifest_row, "cohort"),
                category=text_field(row, "cue_category"),
                dialect_surface=surfaces[0],
                standard_surface=surfaces[1],
            ),
        )
    return cases


def score(cases: list[CueCase], asr: dict[str, JsonObject]) -> list[Scored]:
    scored: list[Scored] = []
    for case in cases:
        row = asr.get(case.review_id)
        if row is None:
            continue
        scored.append(Scored(case, classify(text_field(row, "hypothesis"), case.dialect_surface, case.standard_surface)))
    return scored


def rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else math.nan


def outcome_block(rows: list[Scored]) -> JsonObject:
    counts = Counter(row.outcome for row in rows)
    total = len(rows)
    return {
        "cues": total,
        "counts": dict(counts.most_common()),
        "dialect_surface_preserved_rate": rate(counts["dialect_surface_preserved"], total),
        "standard_normalised_rate": rate(counts["standard_normalised"], total),
        "cue_absent_rate": rate(counts["cue_absent"], total),
    }


def arm_bootstrap(rows: list[Scored], rng: np.random.Generator, draws: int) -> JsonObject:
    """Bootstrap the dialect-arm minus plain-arm gap in genuine cue loss."""
    dialect = np.array([1.0 if r.outcome == "cue_absent" else 0.0 for r in rows if r.case.arm == "case"])
    plain = np.array([1.0 if r.outcome == "cue_absent" else 0.0 for r in rows if r.case.arm == "control"])
    if dialect.size == 0 or plain.size == 0:
        return {"comparable": False}
    d_picks = rng.integers(0, dialect.size, size=(draws, dialect.size))
    p_picks = rng.integers(0, plain.size, size=(draws, plain.size))
    difference = dialect[d_picks].mean(axis=1) - plain[p_picks].mean(axis=1)
    low, high = np.percentile(difference, [2.5, 97.5])
    return {
        "comparable": True,
        "dialect_arm_absent_rate": float(dialect.mean()),
        "plain_arm_absent_rate": float(plain.mean()),
        "difference": float(dialect.mean() - plain.mean()),
        "difference_ci95": {"low": float(low), "high": float(high)},
        "crosses_zero": bool(low <= 0 <= high),
    }


def by_key(rows: list[Scored], key: str) -> JsonObject:
    grouped: dict[str, list[Scored]] = defaultdict(list)
    for row in rows:
        grouped[getattr(row.case, key)].append(row)
    return {name: outcome_block(items) for name, items in sorted(grouped.items(), key=lambda item: -len(item[1]))}


def cohort_gap(rows: list[Scored], rng: np.random.Generator, draws: int) -> JsonObject:
    """Busan minus other-Gyeongsang genuine cue loss, dialect arm only."""
    busan = np.array([1.0 if r.outcome == "cue_absent" else 0.0 for r in rows if r.case.cohort == "busan"])
    other = np.array([1.0 if r.outcome == "cue_absent" else 0.0 for r in rows if r.case.cohort == "gyeongsang_other"])
    if busan.size == 0 or other.size == 0:
        return {"comparable": False}
    difference = busan[rng.integers(0, busan.size, size=(draws, busan.size))].mean(axis=1) - other[
        rng.integers(0, other.size, size=(draws, other.size))
    ].mean(axis=1)
    low, high = np.percentile(difference, [2.5, 97.5])
    return {
        "comparable": True,
        "busan_cues": int(busan.size),
        "other_cues": int(other.size),
        "busan_absent_rate": float(busan.mean()),
        "other_absent_rate": float(other.mean()),
        "difference": float(busan.mean() - other.mean()),
        "difference_ci95": {"low": float(low), "high": float(high)},
        "crosses_zero": bool(low <= 0 <= high),
    }


def analyze(scored: list[Scored], model: str) -> JsonObject:
    rng = np.random.default_rng(RANDOM_SEED)
    dialect_arm = [row for row in scored if row.case.arm == "case"]
    return {
        "model": model,
        "scored_cues": len(scored),
        "dialect_arm": outcome_block(dialect_arm),
        "plain_arm": outcome_block([row for row in scored if row.case.arm == "control"]),
        "genuine_loss_gap": arm_bootstrap(scored, rng, BOOTSTRAP_DRAWS),
        "dialect_arm_by_category": by_key(dialect_arm, "category"),
        "dialect_arm_by_cohort": by_key(dialect_arm, "cohort"),
        "cohort_gap_dialect_arm": cohort_gap(dialect_arm, rng, BOOTSTRAP_DRAWS),
    }


def format_block(result: JsonObject) -> str:
    dialect = result["dialect_arm"]
    plain = result["plain_arm"]
    gap = result["genuine_loss_gap"]
    cohort = result["cohort_gap_dialect_arm"]
    assert isinstance(dialect, dict) and isinstance(plain, dict)
    assert isinstance(gap, dict) and isinstance(cohort, dict)
    lines = [
        f"## {result['model']}",
        "",
        "| Arm | Cues | Dialect surface kept | Normalised to standard | Cue absent |",
        "|---|---:|---:|---:|---:|",
        f"| cue word is dialect-marked | {dialect['cues']} | "
        f"{float(dialect['dialect_surface_preserved_rate']):.3f} | "
        f"{float(dialect['standard_normalised_rate']):.3f} | {float(dialect['cue_absent_rate']):.3f} |",
        f"| cue word is plain | {plain['cues']} | "
        f"{float(plain['dialect_surface_preserved_rate']):.3f} | "
        f"{float(plain['standard_normalised_rate']):.3f} | {float(plain['cue_absent_rate']):.3f} |",
        "",
    ]
    if gap.get("comparable"):
        ci = gap["difference_ci95"]
        assert isinstance(ci, dict)
        lines.append(
            f"- Genuine cue loss gap: {float(gap['difference']):+.3f}, "
            f"95% CI [{float(ci['low']):.3f}, {float(ci['high']):.3f}]"
            f"{' — crosses zero' if gap['crosses_zero'] else ' — excludes zero'}",
        )
    if cohort.get("comparable"):
        ci = cohort["difference_ci95"]
        assert isinstance(ci, dict)
        lines.append(
            f"- Busan minus other Gyeongsang, dialect arm: {float(cohort['difference']):+.3f}, "
            f"95% CI [{float(ci['low']):.3f}, {float(ci['high']):.3f}]"
            f"{' — crosses zero' if cohort['crosses_zero'] else ' — excludes zero'} "
            f"({cohort['busan_cues']} vs {cohort['other_cues']} cues)",
        )
    categories = result["dialect_arm_by_category"]
    assert isinstance(categories, dict)
    lines.extend(
        [
            "",
            "| Cue category, dialect arm | Cues | Dialect surface kept | Normalised | Absent |",
            "|---|---:|---:|---:|---:|",
        ],
    )
    lines.extend(
        f"| {name} | {stats['cues']} | {float(stats['dialect_surface_preserved_rate']):.3f} | "
        f"{float(stats['standard_normalised_rate']):.3f} | {float(stats['cue_absent_rate']):.3f} |"
        for name, stats in categories.items()
        if isinstance(stats, dict)
    )
    lines.append("")
    return "\n".join(lines)


def write_readme(output_dir: Path, results: list[JsonObject]) -> None:
    header = (
        "# Cue Error Types\n\n"
        "Round 6 measured how often a dialect-marked cue word goes missing from the hypothesis. That number\n"
        "mixes two outcomes a contact centre would treat very differently: the ASR writing the standard form\n"
        "of the same cue, where the business meaning survives, and the cue disappearing outright, where it\n"
        "does not. This run separates them.\n\n"
        "`standard_normalised` is not damage. Only `cue_absent` is.\n\n"
        "The cohort line re-tests the Busan-versus-other question at cue level, where round 4 could only test\n"
        "it at whole-utterance level.\n\n"
        "Labels are weak preannotations that no human has reviewed.\n\n"
    )
    (output_dir / "README.md").write_text(header + "\n".join(format_block(r) for r in results), encoding="utf-8")


def write_outputs(results: list[JsonObject], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary: JsonObject = {
        "analysis": "cue_error_type_decomposition",
        "random_seed": RANDOM_SEED,
        "label_status": "weak_preannotation_not_gold",
        "outcome_rule": "dialect surface kept, else standard form of the same eojeol present, else absent",
        "results": list(results),
        "numpy_version": np.__version__,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_readme(output_dir, results)


@app.command()
def main(
    split_dir: Annotated[Path, typer.Argument(help="Cue-bearing split directory.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
    label_root: Annotated[Path, typer.Option("--label-root")] = Path("data/raw/aihub_gyeongsang_119"),
) -> None:
    if not (split_dir / "cue_annotations.local.jsonl").exists():
        console.print(f"Cue annotations not found under {split_dir}")
        raise typer.Exit(code=2)
    console.print("Resolving cue eojeol surfaces from labels")
    cases = build_cases(split_dir, label_root)
    if not cases:
        console.print("No cue case could be resolved against the label set.")
        raise typer.Exit(code=1)
    results: list[JsonObject] = []
    for model in MODELS:
        asr_path = split_dir / f"{model}.local.jsonl"
        if not asr_path.exists():
            console.print(f"Skipping {model}: ASR output missing")
            continue
        scored = score(cases, index_by(load_jsonl(asr_path), "review_id"))
        if scored:
            results.append(analyze(scored, model))
    if not results:
        console.print("No model could be scored.")
        raise typer.Exit(code=1)
    write_outputs(results, output_dir)
    console.print(f"Classified {len(cases)} cue cases across {len(results)} model(s) into {output_dir}")


if __name__ == "__main__":
    app()
