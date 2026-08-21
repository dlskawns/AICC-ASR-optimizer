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
#      uv run scripts/score_cues_by_alignment.py research/experiments/runs/aihub_119_cue_bearing_split --output-dir research/experiments/runs/aihub_119_cue_aligned
# ──────────────────

"""Score AICC cues by position, bringing rounds 6 to 8 onto the alignment standard.

The cue metrics still searched for a surface anywhere in the hypothesis, the rule that unit scoring
has already moved away from. This aligns the reference eojeol sequence to the hypothesis tokens and
judges each cue only against the token aligned to its own position.

Two things follow. The four-way outcome, dialect surface kept, normalised to standard, cue morpheme
under different inflection, or gone, becomes position-locked. And the substitution-versus-deletion
question answers itself: a cue that aligns to a token was replaced by that token, a cue that aligns to
nothing was deleted. Round 8 had to guess this from surviving neighbours and could not resolve two
thirds of cases.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Final, Literal, TypeAlias, assert_never

import numpy as np
import typer
from build_dialect_taxonomy import JsonValue, list_of_mappings, text_field
from compare_cue_bearing_pairs import Arm, Pair, mcnemar
from rich.console import Console
from run_dialect_attribution_probe import label_index, payload_for, target_utterance
from score_units_by_alignment import align, normalized

JsonObject: TypeAlias = dict[str, JsonValue]
Outcome: TypeAlias = Literal[
    "dialect_surface_preserved",
    "standard_normalised",
    "cue_morpheme_only",
    "substituted",
    "deleted",
]

MODELS: Final[tuple[str, ...]] = ("faster_whisper_medium", "faster_whisper_large_v3", "wav2vec2_korean")
BOOTSTRAP_DRAWS: Final[int] = 10000
PERMUTATION_DRAWS: Final[int] = 20000
RANDOM_SEED: Final[int] = 20260821
DAMAGED: Final[frozenset[str]] = frozenset({"substituted", "deleted"})

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
    cue_span_text: str
    reference: tuple[str, ...]
    cue_index: int
    plain_units: tuple[tuple[str, bool], ...]


@dataclass(frozen=True, slots=True)
class Scored:
    case: CueCase
    outcome: Outcome
    replacement: str


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


def matches(candidate: str, surface: str) -> bool:
    a, b = normalized(candidate), normalized(surface)
    return bool(a) and bool(b) and (a == b or a.startswith(b) or b.startswith(a))


def build_cases(split_dir: Path, label_root: Path) -> list[CueCase]:
    annotations = load_jsonl(split_dir / "cue_annotations.local.jsonl")
    manifest = index_by(load_jsonl(split_dir / "asr_input_manifest.local.jsonl"), "review_id")
    labels = label_index(label_root)
    payloads: dict[str, JsonObject] = {}
    cases: list[CueCase] = []
    for row in annotations:
        review_id = text_field(row, "review_id")
        manifest_row = manifest.get(review_id)
        if manifest_row is None:
            continue
        source_file = text_field(manifest_row, "source_file")
        if source_file not in payloads:
            payloads[source_file] = payload_for(labels, source_file)
        utterance = target_utterance(payloads[source_file], text_field(row, "utterance_id"))
        eojeols = list_of_mappings(utterance.get("eojeolList"))
        wanted = normalized(text_field(row, "cue_evidence_eojeol"))
        cue_index = next(
            (
                index
                for index, eojeol in enumerate(eojeols)
                if normalized(text_field(eojeol, "eojeol")) == wanted
                or normalized(text_field(eojeol, "standard")) == wanted
            ),
            -1,
        )
        if cue_index < 0:
            continue
        cases.append(
            CueCase(
                review_id=review_id,
                arm=text_field(row, "arm"),
                cohort=text_field(manifest_row, "cohort"),
                category=text_field(row, "cue_category"),
                dialect_surface=text_field(eojeols[cue_index], "eojeol"),
                standard_surface=text_field(eojeols[cue_index], "standard")
                or text_field(eojeols[cue_index], "eojeol"),
                cue_span_text=text_field(row, "cue_span_text"),
                reference=tuple(text_field(eojeol, "eojeol") for eojeol in eojeols),
                cue_index=cue_index,
                plain_units=tuple(
                    (text_field(eojeol, "standard") or text_field(eojeol, "eojeol"), eojeol.get("isDialect") is True)
                    for eojeol in eojeols
                ),
            ),
        )
    return cases


def score_case(case: CueCase, hypothesis: str) -> tuple[Scored, int, int]:
    """Return the cue verdict plus the non-dialect unit totals used as the placebo."""
    tokens = [normalized(token) for token in hypothesis.split() if normalized(token)]
    pairs = align([normalized(surface) for surface in case.reference], tokens)
    index = pairs[case.cue_index]
    aligned = tokens[index] if index is not None else ""
    if not aligned:
        outcome: Outcome = "deleted"
    elif matches(aligned, case.dialect_surface):
        outcome = "dialect_surface_preserved"
    elif normalized(case.standard_surface) != normalized(case.dialect_surface) and matches(
        aligned, case.standard_surface,
    ):
        outcome = "standard_normalised"
    elif case.cue_span_text and matches(aligned, case.cue_span_text):
        outcome = "cue_morpheme_only"
    else:
        outcome = "substituted"
    plain_total = plain_error = 0
    for position, (surface, is_dialect) in enumerate(case.plain_units):
        if is_dialect:
            continue
        plain_total += 1
        target = pairs[position]
        if target is None or not matches(tokens[target], surface):
            plain_error += 1
    return Scored(case, outcome, aligned if outcome == "substituted" else ""), plain_total, plain_error


def build_pairs(
    pair_rows: list[JsonObject],
    scored: dict[str, tuple[Scored, int, int]],
) -> tuple[list[Pair], list[Scored]]:
    pairs: list[Pair] = []
    flat: list[Scored] = []
    for row in pair_rows:
        case_id = text_field(row, "case_review_id")
        control_id = text_field(row, "control_review_id")
        if case_id not in scored or control_id not in scored:
            continue
        case, case_plain_total, case_plain_error = scored[case_id]
        control, control_plain_total, control_plain_error = scored[control_id]
        flat.extend((case, control))
        pairs.append(
            Pair(
                speaker_key=text_field(row, "speaker_key"),
                cohort=text_field(row, "cohort"),
                category=text_field(row, "cue_category"),
                dialect_arm=Arm(1, 1 if case.outcome in DAMAGED else 0, case_plain_total, case_plain_error),
                plain_arm=Arm(1, 1 if control.outcome in DAMAGED else 0, control_plain_total, control_plain_error),
            ),
        )
    return pairs, flat


def speaker_groups(pairs: list[Pair]) -> list[list[int]]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for index, pair in enumerate(pairs):
        grouped[pair.speaker_key].append(index)
    return [indices for _, indices in sorted(grouped.items())]


def rate(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else float("nan")


def arm_arrays(pairs: list[Pair], numerator: str, denominator: str) -> tuple[np.ndarray, ...]:
    return (
        np.array([getattr(p.dialect_arm, numerator) for p in pairs], dtype=np.float64),
        np.array([getattr(p.dialect_arm, denominator) for p in pairs], dtype=np.float64),
        np.array([getattr(p.plain_arm, numerator) for p in pairs], dtype=np.float64),
        np.array([getattr(p.plain_arm, denominator) for p in pairs], dtype=np.float64),
    )


def speaker_bootstrap(
    pairs: list[Pair],
    numerator: str,
    denominator: str,
    rng: np.random.Generator,
    draws: int,
) -> JsonObject:
    """Resample speakers, not pairs, so a speaker contributing several pairs moves as one unit."""
    a_num, a_den, b_num, b_den = arm_arrays(pairs, numerator, denominator)
    groups = speaker_groups(pairs)
    picks = rng.integers(0, len(groups), size=(draws, len(groups)))
    differences = np.empty(draws, dtype=np.float64)
    for draw in range(draws):
        index = np.concatenate([groups[choice] for choice in picks[draw]])
        differences[draw] = rate(a_num[index].sum(), a_den[index].sum()) - rate(
            b_num[index].sum(), b_den[index].sum(),
        )
    finite = differences[np.isfinite(differences)]
    low, high = np.percentile(finite, [2.5, 97.5])
    observed = rate(a_num.sum(), a_den.sum()) - rate(b_num.sum(), b_den.sum())
    return {
        "resampling_unit": "speaker",
        "speakers": len(groups),
        "dialect_arm_rate": rate(a_num.sum(), a_den.sum()),
        "plain_arm_rate": rate(b_num.sum(), b_den.sum()),
        "difference": observed,
        "difference_ci95": {"low": float(low), "high": float(high)},
        "crosses_zero": bool(low <= 0 <= high),
        "draws": draws,
    }


def speaker_arm_swap(
    pairs: list[Pair],
    numerator: str,
    denominator: str,
    rng: np.random.Generator,
    draws: int,
) -> JsonObject:
    """Swap arms a whole speaker at a time, which respects dependence between one speaker's pairs."""
    a_num, a_den, b_num, b_den = arm_arrays(pairs, numerator, denominator)
    groups = speaker_groups(pairs)
    swap = rng.integers(0, 2, size=(draws, len(groups))).astype(bool)
    per_pair = np.zeros((draws, len(pairs)), dtype=bool)
    for position, indices in enumerate(groups):
        per_pair[:, indices] = swap[:, position][:, None]
    left_num = np.where(per_pair, b_num, a_num).sum(axis=1)
    left_den = np.where(per_pair, b_den, a_den).sum(axis=1)
    right_num = np.where(per_pair, a_num, b_num).sum(axis=1)
    right_den = np.where(per_pair, a_den, b_den).sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        null = (left_num / left_den) - (right_num / right_den)
    observed = rate(a_num.sum(), a_den.sum()) - rate(b_num.sum(), b_den.sum())
    finite = null[np.isfinite(null)]
    extreme = int(np.sum(np.abs(finite) >= abs(observed) - 1e-12))
    return {
        "test": "speaker_level_arm_swap_permutation",
        "draws": int(finite.size),
        "extreme_draws": extreme,
        "two_sided_p_value": (extreme + 1) / (finite.size + 1),
        "p_note": "resolution_floor_reached" if extreme == 0 else "add_one_estimator",
    }


def outcome_block(rows: list[Scored]) -> JsonObject:
    counts = Counter(row.outcome for row in rows)
    total = len(rows)
    damaged = counts["substituted"] + counts["deleted"]
    return {
        "cues": total,
        "counts": dict(counts.most_common()),
        "damaged": damaged,
        "damage_rate": damaged / total if total else 0.0,
        "substitution_share_of_damage": counts["substituted"] / damaged if damaged else None,
    }


def analyze(pairs: list[Pair], flat: list[Scored], model: str) -> JsonObject:
    rng = np.random.default_rng(RANDOM_SEED)
    dialect_arm = [row for row in flat if row.case.arm == "case"]
    plain_arm = [row for row in flat if row.case.arm == "control"]
    by_category: dict[str, list[Scored]] = defaultdict(list)
    by_cohort: dict[str, list[Scored]] = defaultdict(list)
    for row in dialect_arm:
        by_category[row.case.category].append(row)
        by_cohort[row.case.cohort].append(row)
    return {
        "model": model,
        "pairs": len(pairs),
        "distinct_speakers": len({pair.speaker_key for pair in pairs}),
        "dialect_arm": outcome_block(dialect_arm),
        "plain_arm": outcome_block(plain_arm),
        "pairs_per_speaker_max": max(len(group) for group in speaker_groups(pairs)),
        "damage_gap": speaker_bootstrap(pairs, "cue_lost", "cue_scorable", rng, BOOTSTRAP_DRAWS),
        "damage_permutation": speaker_arm_swap(pairs, "cue_lost", "cue_scorable", rng, PERMUTATION_DRAWS),
        "mcnemar": mcnemar(pairs),
        "mcnemar_note": "treats pairs as independent; read it only when each speaker contributes one pair",
        "placebo_plain_unit_error": speaker_bootstrap(pairs, "plain_error", "plain_total", rng, BOOTSTRAP_DRAWS),
        "dialect_arm_by_category": {name: outcome_block(rows) for name, rows in sorted(by_category.items())},
        "dialect_arm_by_cohort": {name: outcome_block(rows) for name, rows in sorted(by_cohort.items())},
        "distinct_replacement_surfaces": len({row.replacement for row in dialect_arm if row.replacement}),
    }


def format_block(result: JsonObject) -> str:
    dialect = result["dialect_arm"]
    plain = result["plain_arm"]
    gap = result["damage_gap"]
    placebo = result["placebo_plain_unit_error"]
    permutation = result["damage_permutation"]
    table = result["mcnemar"]
    assert isinstance(dialect, dict) and isinstance(plain, dict) and isinstance(gap, dict)
    assert isinstance(placebo, dict) and isinstance(permutation, dict) and isinstance(table, dict)
    gap_ci = gap["difference_ci95"]
    placebo_ci = placebo["difference_ci95"]
    assert isinstance(gap_ci, dict) and isinstance(placebo_ci, dict)

    def share(stats: JsonObject) -> str:
        value = stats.get("substitution_share_of_damage")
        return f"{float(value):.3f}" if isinstance(value, (int, float)) else "n/a"

    def counts_of(stats: JsonObject, key: str) -> int:
        counts = stats["counts"]
        return int(counts.get(key, 0)) if isinstance(counts, dict) else 0

    lines = [
        f"## {result['model']}",
        "",
        f"- Pairs: {result['pairs']} across {result['distinct_speakers']} speakers",
        "",
        "| Arm | Cues | Dialect kept | Normalised | Morpheme only | Substituted | Deleted | Damage rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, stats in (("cue word is dialect-marked", dialect), ("cue word is plain", plain)):
        lines.append(
            f"| {label} | {stats['cues']} | {counts_of(stats, 'dialect_surface_preserved')} | "
            f"{counts_of(stats, 'standard_normalised')} | {counts_of(stats, 'cue_morpheme_only')} | "
            f"{counts_of(stats, 'substituted')} | {counts_of(stats, 'deleted')} | "
            f"{float(stats['damage_rate']):.3f} |",
        )
    lines.extend(
        [
            "",
            f"- Damage gap: {float(gap['difference']):+.3f}, 95% CI "
            f"[{float(gap_ci['low']):.3f}, {float(gap_ci['high']):.3f}]"
            f"{' — crosses zero' if gap['crosses_zero'] else ' — excludes zero'}",
            f"- Arm-swap permutation p: "
            f"{'<' if permutation['extreme_draws'] == 0 else ''}{float(permutation['two_sided_p_value']):.3e}",
            f"- Discordant pairs: {table['dialect_arm_only_lost']} dialect-only vs "
            f"{table['plain_arm_only_lost']} plain-only"
            + (
                f", McNemar p {float(table['mcnemar_p_approx']):.3e}"
                if table.get("mcnemar_p_approx") is not None
                else ""
            ),
            f"- Substitution share of damage: {share(dialect)} dialect arm, {share(plain)} plain arm",
            f"- Distinct replacement surfaces, dialect arm: {result['distinct_replacement_surfaces']}",
            f"- Placebo, non-dialect unit error: {float(placebo['difference']):+.3f} 95% CI "
            f"[{float(placebo_ci['low']):.3f}, {float(placebo_ci['high']):.3f}]"
            f"{' — crosses zero' if placebo['crosses_zero'] else ' — EXCLUDES ZERO, matching is suspect'}",
            "",
        ],
    )
    return "\n".join(lines)


def write_readme(output_dir: Path, results: list[JsonObject]) -> None:
    header = (
        "# Cue Scoring By Alignment\n\n"
        "Rounds 6 to 8 searched for a cue surface anywhere in the hypothesis. Unit scoring has already moved\n"
        "to alignment; this brings the cue metrics onto the same standard. The reference eojeol sequence is\n"
        "aligned to the hypothesis tokens and each cue is judged only against the token at its own position.\n\n"
        "Five outcomes. Three preserve the business meaning: the dialect form written as spoken, the standard\n"
        "form of the same word, or the cue morpheme surviving under different inflection. Two are damage:\n"
        "the position holds some other word, or it holds nothing.\n\n"
        "That last split is free here. Round 8 had to infer substitution from surviving neighbours and could\n"
        "not resolve about two thirds of cases; the alignment states it directly.\n\n"
        "Read the placebo line first. If non-dialect unit error differs between arms the pairing is suspect.\n\n"
        "Labels are weak preannotations that no human has reviewed.\n\n"
    )
    (output_dir / "README.md").write_text(header + "\n".join(format_block(r) for r in results), encoding="utf-8")


def write_outputs(results: list[JsonObject], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary: JsonObject = {
        "analysis": "cue_scoring_by_sequence_alignment",
        "random_seed": RANDOM_SEED,
        "label_status": "weak_preannotation_not_gold",
        "scoring_rule": "reference eojeols aligned to hypothesis tokens; each cue judged against its aligned token only",
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
    console.print("Resolving cue positions from labels")
    cases = build_cases(split_dir, label_root)
    if not cases:
        console.print("No cue case could be resolved.")
        raise typer.Exit(code=1)
    pair_rows = load_jsonl(split_dir / "pair_manifest.jsonl")
    results: list[JsonObject] = []
    for model in MODELS:
        asr_path = split_dir / f"{model}.local.jsonl"
        if not asr_path.exists():
            console.print(f"Skipping {model}: ASR output missing")
            continue
        asr = index_by(load_jsonl(asr_path), "review_id")
        scored = {
            case.review_id: score_case(case, text_field(asr[case.review_id], "hypothesis"))
            for case in cases
            if case.review_id in asr
        }
        pairs, flat = build_pairs(pair_rows, scored)
        if pairs:
            results.append(analyze(pairs, flat, model))
    if not results:
        console.print("No model could be scored.")
        raise typer.Exit(code=1)
    write_outputs(results, output_dir)
    console.print(f"Scored cues by alignment for {len(results)} model(s) into {output_dir}")


if __name__ == "__main__":
    app()
