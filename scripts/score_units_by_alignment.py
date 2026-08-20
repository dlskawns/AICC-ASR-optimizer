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
#      uv run scripts/score_units_by_alignment.py research/experiments/runs/aihub_119_speaker_independent_split/asr_input_manifest.local.jsonl research/experiments/runs/aihub_119_speaker_independent_split/faster_whisper_medium.local.jsonl --output-dir research/experiments/runs/aihub_119_aligned_unit_scoring
# ──────────────────

"""Score dialect and non-dialect eojeols by position, using an alignment instead of a surface search.

Every earlier version of this metric asked whether a reference surface appeared *somewhere* in the
hypothesis. Two corrections have already come out of that: raw containment credited single syllables
that turn up inside unrelated words, and the eojeol-boundary rule that replaced it still lets a
one-syllable unit match any eojeol that happens to start with it. Half the dialect units here are one
syllable, so the loophole was never fully closed.

This aligns the reference eojeol sequence to the hypothesis token sequence by edit distance, with a
substitution cost taken from character similarity, and judges each unit only against whatever aligned
to its position. A unit cannot borrow evidence from elsewhere in the sentence.

Dialect units keep the concession they always had: either the dialect surface or its standard form
counts as correct. That concession makes the dialect arm easier to score well, so it cannot be the
source of a dialect penalty.
"""

from __future__ import annotations

import json
import re
import zipfile
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Annotated, Final, TypeAlias, assert_never

import numpy as np
import typer
from build_dialect_taxonomy import JsonValue, list_of_mappings, text_field
from rich.console import Console
from run_dialect_attribution_probe import label_index, payload_for, target_utterance
from run_dialect_significance_tests import Cluster, analyze, model_label

JsonObject: TypeAlias = dict[str, JsonValue]

GAP_COST: Final[float] = 1.0

app = typer.Typer(add_completion=False)
console = Console()


@dataclass(frozen=True, slots=True)
class RefUnit:
    dialect: str
    standard: str
    is_dialect: bool


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


def substitution_cost(reference: str, candidate: str) -> float:
    """Cheap for lookalike tokens, so the alignment prefers pairing a word with its misrecognition."""
    if not reference or not candidate:
        return GAP_COST
    if reference == candidate:
        return 0.0
    return 1.0 - SequenceMatcher(None, reference, candidate).ratio()


def align(reference: list[str], hypothesis: list[str]) -> list[int | None]:
    """Return, for each reference token, the hypothesis index aligned to it or None if deleted."""
    rows, cols = len(reference), len(hypothesis)
    cost = np.zeros((rows + 1, cols + 1), dtype=np.float64)
    back = np.zeros((rows + 1, cols + 1), dtype=np.int8)  # 0 sub, 1 del, 2 ins
    cost[:, 0] = np.arange(rows + 1) * GAP_COST
    cost[0, :] = np.arange(cols + 1) * GAP_COST
    back[1:, 0] = 1
    back[0, 1:] = 2
    for i in range(1, rows + 1):
        for j in range(1, cols + 1):
            options = (
                cost[i - 1, j - 1] + substitution_cost(reference[i - 1], hypothesis[j - 1]),
                cost[i - 1, j] + GAP_COST,
                cost[i, j - 1] + GAP_COST,
            )
            choice = int(np.argmin(options))
            cost[i, j] = options[choice]
            back[i, j] = choice
    pairs: list[int | None] = [None] * rows
    i, j = rows, cols
    while i > 0 or j > 0:
        move = back[i, j]
        if i > 0 and j > 0 and move == 0:
            pairs[i - 1] = j - 1
            i, j = i - 1, j - 1
        elif i > 0 and move == 1:
            i -= 1
        else:
            j -= 1
    return pairs


def unit_correct(unit: RefUnit, token: str | None) -> bool:
    """A unit is correct when the token aligned to its position carries that word."""
    if token is None:
        return False
    accepted = (normalized(unit.dialect), normalized(unit.standard)) if unit.is_dialect else (normalized(unit.standard),)
    candidate = normalized(token)
    if not candidate:
        return False
    return any(
        surface and (candidate == surface or candidate.startswith(surface) or surface.startswith(candidate))
        for surface in accepted
    )


def reference_units(utterance: JsonObject) -> list[RefUnit]:
    return [
        RefUnit(
            dialect=text_field(eojeol, "eojeol"),
            standard=text_field(eojeol, "standard") or text_field(eojeol, "eojeol"),
            is_dialect=eojeol.get("isDialect") is True,
        )
        for eojeol in list_of_mappings(utterance.get("eojeolList"))
    ]


def cluster_for(row: JsonObject, units: list[RefUnit], hypothesis: str) -> Cluster:
    tokens = [normalized(token) for token in hypothesis.split() if normalized(token)]
    pairs = align([normalized(unit.dialect) for unit in units], tokens)
    dialect_total = dialect_error = plain_total = plain_error = 0
    for unit, index in zip(units, pairs, strict=True):
        token = tokens[index] if index is not None else None
        correct = unit_correct(unit, token)
        if unit.is_dialect:
            dialect_total += 1
            dialect_error += 0 if correct else 1
        else:
            plain_total += 1
            plain_error += 0 if correct else 1
    return Cluster(
        review_id=text_field(row, "review_id"),
        cohort=text_field(row, "cohort"),
        dialect_total=dialect_total,
        dialect_error=dialect_error,
        plain_total=plain_total,
        plain_error=plain_error,
    )


def build_clusters(
    manifest_rows: list[JsonObject],
    asr_rows: list[JsonObject],
    label_root: Path,
) -> tuple[list[Cluster], int]:
    outputs = {text_field(row, "review_id"): row for row in asr_rows}
    labels = label_index(label_root)
    payloads: dict[str, JsonObject] = {}
    clusters: list[Cluster] = []
    missing = 0
    for row in manifest_rows:
        output = outputs.get(text_field(row, "review_id"))
        if output is None:
            missing += 1
            continue
        source_file = text_field(row, "source_file")
        if source_file not in payloads:
            payloads[source_file] = payload_for(labels, source_file)
        utterance = target_utterance(payloads[source_file], text_field(row, "utterance_id"))
        units = reference_units(utterance)
        if not units:
            continue
        clusters.append(cluster_for(row, units, text_field(output, "hypothesis")))
    return clusters, missing


def write_readme(output_dir: Path, results: list[JsonObject]) -> None:
    header = (
        "# Aligned Unit Scoring\n\n"
        "Earlier versions of this metric asked whether a reference eojeol appeared anywhere in the hypothesis.\n"
        "Raw containment credited a single syllable that turned up inside an unrelated word; the eojeol-boundary\n"
        "rule that replaced it still let a one-syllable unit match any eojeol beginning with it. Half the dialect\n"
        "units in this data are one syllable, so that loophole stayed open.\n\n"
        "Here the reference eojeol sequence is aligned to the hypothesis token sequence by edit distance, with a\n"
        "substitution cost drawn from character similarity, and each unit is judged only against whatever aligned\n"
        "to its position. Evidence cannot be borrowed from elsewhere in the sentence.\n\n"
        "Dialect units keep their standing concession: the dialect surface or its standard form both count as\n"
        "correct. That makes the dialect arm easier to score well, so it cannot manufacture a dialect penalty.\n\n"
    )
    body: list[str] = []
    for result in results:
        point = result["point_estimates"]
        bootstrap = result["cluster_bootstrap"]
        permutation = result["permutation_test"]
        mh = result["mantel_haenszel_by_utterance"]
        cohort = result["cohort_contrast"]
        assert isinstance(point, dict) and isinstance(bootstrap, dict)
        assert isinstance(permutation, dict) and isinstance(mh, dict) and isinstance(cohort, dict)
        difference_ci = bootstrap["difference_ci95"]
        mh_ci = mh["ci95"]
        assert isinstance(difference_ci, dict) and isinstance(mh_ci, dict)
        body.append(
            "\n".join(
                [
                    f"## {result['model']}",
                    "",
                    f"- Utterances: {result['utterances']}, dialect units {result['dialect_units']}, "
                    f"non-dialect units {result['plain_units']}",
                    f"- Dialect unit error rate: {float(point['dialect_unit_error_rate']):.3f}",
                    f"- Non-dialect unit error rate: {float(point['plain_unit_error_rate']):.3f}",
                    f"- Difference: {float(point['difference']):.3f}, cluster bootstrap 95% CI "
                    f"[{float(difference_ci['low']):.3f}, {float(difference_ci['high']):.3f}]",
                    f"- Ratio: {float(point['ratio']):.2f}x",
                    f"- Utterance-stratified odds ratio: {float(mh['odds_ratio']):.2f} "
                    f"[{float(mh_ci['low']):.2f}, {float(mh_ci['high']):.2f}]",
                    f"- Within-utterance permutation p: "
                    f"{'<' if permutation['extreme_draws'] == 0 else ''}"
                    f"{float(permutation['two_sided_p_value']):.2e}",
                    f"- Busan minus other Gyeongsang: {float(cohort['difference']):+.3f}"
                    if cohort.get("comparable")
                    else "- Cohort contrast not computable",
                    "",
                ],
            ),
        )
    (output_dir / "README.md").write_text(header + "\n".join(body), encoding="utf-8")


def write_outputs(results: list[JsonObject], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary: JsonObject = {
        "analysis": "unit_scoring_by_sequence_alignment",
        "scoring_rule": "reference eojeols aligned to hypothesis tokens by edit distance; each unit judged against its aligned token only",
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
    label_root: Annotated[Path, typer.Option("--label-root")] = Path("data/raw/aihub_gyeongsang_119"),
    bootstrap_draws: Annotated[int, typer.Option("--bootstrap-draws", min=1000)] = 10000,
    permutation_draws: Annotated[int, typer.Option("--permutation-draws", min=1000)] = 20000,
) -> None:
    if not manifest_path.exists():
        console.print(f"Manifest not found: {manifest_path}")
        raise typer.Exit(code=2)
    manifest_rows = load_jsonl(manifest_path)
    results: list[JsonObject] = []
    for path in asr_paths:
        if not path.exists():
            console.print(f"ASR output not found: {path}")
            raise typer.Exit(code=2)
        asr_rows = load_jsonl(path)
        clusters, missing = build_clusters(manifest_rows, asr_rows, label_root)
        if not clusters:
            console.print(f"No utterance could be aligned for {path}")
            raise typer.Exit(code=1)
        results.append(analyze(clusters, missing, model_label(asr_rows, path), bootstrap_draws, permutation_draws))
    write_outputs(results, output_dir)
    console.print(f"Scored {len(results)} model(s) by alignment into {output_dir}")


if __name__ == "__main__":
    app()
