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
#      uv run scripts/score_spans_by_alignment.py research/experiments/runs/aihub_119_dialect_control_pairs/pair_manifest.jsonl --case-dir research/experiments/runs/aihub_119_speaker_independent_split --case-annotations research/experiments/runs/aihub_119_holdout_critical_spans/remined_annotations.local.jsonl --control-dir research/experiments/runs/aihub_119_dialect_control_pairs --output-dir research/experiments/runs/aihub_119_control_pairs_aligned
# ──────────────────

"""Re-score the round 5 within-speaker control pairs by alignment.

Round 5 asked whether an utterance carrying dialect marking loses more AICC critical spans than the
same speaker's dialect-free utterance, and found nothing. It judged a span by searching the whole
hypothesis, the rule the unit and cue metrics have since abandoned. Every other correction in this
project moved a number, so the round 5 null cannot be trusted until it has been rescored the same way.

Each span is located at its evidence eojeol, the reference eojeol sequence is aligned to the hypothesis
tokens, and the span is judged only against the token aligned to its position.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Final, TypeAlias, assert_never

import numpy as np
import typer
from build_dialect_taxonomy import JsonValue, list_of_mappings, text_field
from compare_cue_bearing_pairs import Arm, Pair, arm_swap_permutation, mcnemar, paired_bootstrap
from rich.console import Console
from run_dialect_attribution_probe import label_index, payload_for, target_utterance
from score_units_by_alignment import align, normalized

JsonObject: TypeAlias = dict[str, JsonValue]

MODELS: Final[tuple[str, ...]] = ("faster_whisper_medium", "faster_whisper_large_v3", "wav2vec2_korean")
BOOTSTRAP_DRAWS: Final[int] = 10000
PERMUTATION_DRAWS: Final[int] = 20000
RANDOM_SEED: Final[int] = 20260821

app = typer.Typer(add_completion=False)
console = Console()


@dataclass(frozen=True, slots=True)
class Utterance:
    review_id: str
    reference: tuple[str, ...]
    is_dialect: tuple[bool, ...]
    standards: tuple[str, ...]
    span_positions: tuple[int, ...]
    span_surfaces: tuple[str, ...]


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


def build_utterances(
    manifest_rows: list[JsonObject],
    annotations: dict[str, JsonObject],
    label_root: Path,
) -> dict[str, Utterance]:
    labels = label_index(label_root)
    payloads: dict[str, JsonObject] = {}
    built: dict[str, Utterance] = {}
    for row in manifest_rows:
        utterance_id = text_field(row, "utterance_id")
        annotation = annotations.get(utterance_id)
        if annotation is None:
            continue
        source_file = text_field(row, "source_file")
        if source_file not in payloads:
            payloads[source_file] = payload_for(labels, source_file)
        utterance = target_utterance(payloads[source_file], utterance_id)
        eojeols = list_of_mappings(utterance.get("eojeolList"))
        surfaces = [text_field(eojeol, "eojeol") for eojeol in eojeols]
        positions: list[int] = []
        span_surfaces: list[str] = []
        for span in list_of_mappings(annotation.get("critical_spans")):
            wanted = normalized(text_field(span, "evidence_eojeol"))
            index = next(
                (
                    position
                    for position, eojeol in enumerate(eojeols)
                    if normalized(text_field(eojeol, "eojeol")) == wanted
                    or normalized(text_field(eojeol, "standard")) == wanted
                ),
                -1,
            )
            if index < 0:
                continue
            positions.append(index)
            span_surfaces.append(text_field(span, "span_text"))
        built[text_field(row, "review_id")] = Utterance(
            review_id=text_field(row, "review_id"),
            reference=tuple(surfaces),
            is_dialect=tuple(eojeol.get("isDialect") is True for eojeol in eojeols),
            standards=tuple(
                text_field(eojeol, "standard") or text_field(eojeol, "eojeol") for eojeol in eojeols
            ),
            span_positions=tuple(positions),
            span_surfaces=tuple(span_surfaces),
        )
    return built


def score(utterance: Utterance, hypothesis: str) -> Arm:
    tokens = [normalized(token) for token in hypothesis.split() if normalized(token)]
    pairs = align([normalized(surface) for surface in utterance.reference], tokens)
    spans_total = spans_lost = 0
    for position, span_surface in zip(utterance.span_positions, utterance.span_surfaces, strict=True):
        spans_total += 1
        target = pairs[position]
        token = tokens[target] if target is not None else ""
        accepted = (utterance.reference[position], utterance.standards[position], span_surface)
        if not any(surface and matches(token, surface) for surface in accepted):
            spans_lost += 1
    plain_total = plain_error = 0
    for position, dialect_flag in enumerate(utterance.is_dialect):
        if dialect_flag:
            continue
        plain_total += 1
        target = pairs[position]
        if target is None or not matches(tokens[target], utterance.standards[position]):
            plain_error += 1
    return Arm(spans_total, spans_lost, plain_total, plain_error)


def analyze(pairs: list[Pair], model: str) -> JsonObject:
    rng = np.random.default_rng(RANDOM_SEED)
    return {
        "model": model,
        "pairs": len(pairs),
        "distinct_speakers": len({pair.speaker_key for pair in pairs}),
        "dialect_arm_spans": sum(pair.dialect_arm.cue_scorable for pair in pairs),
        "control_arm_spans": sum(pair.plain_arm.cue_scorable for pair in pairs),
        "critical_span_loss": paired_bootstrap(pairs, "cue_lost", "cue_scorable", rng, BOOTSTRAP_DRAWS),
        "loss_permutation": arm_swap_permutation(pairs, "cue_lost", "cue_scorable", rng, PERMUTATION_DRAWS),
        "mcnemar": mcnemar(pairs),
        "placebo_plain_unit_error": paired_bootstrap(pairs, "plain_error", "plain_total", rng, BOOTSTRAP_DRAWS),
    }


def format_block(result: JsonObject) -> str:
    loss = result["critical_span_loss"]
    placebo = result["placebo_plain_unit_error"]
    permutation = result["loss_permutation"]
    table = result["mcnemar"]
    assert isinstance(loss, dict) and isinstance(placebo, dict)
    assert isinstance(permutation, dict) and isinstance(table, dict)
    ci = loss["difference_ci95"]
    placebo_ci = placebo["difference_ci95"]
    assert isinstance(ci, dict) and isinstance(placebo_ci, dict)
    return "\n".join(
        [
            f"## {result['model']}",
            "",
            f"- Pairs: {result['pairs']} across {result['distinct_speakers']} speakers",
            f"- Spans: {result['dialect_arm_spans']} dialect arm, {result['control_arm_spans']} control arm",
            f"- Critical-span loss: {float(loss['dialect_arm_rate']):.3f} dialect vs "
            f"{float(loss['plain_arm_rate']):.3f} control",
            f"- Paired difference: {float(loss['difference']):+.3f}, "
            f"95% CI [{float(ci['low']):.3f}, {float(ci['high']):.3f}]"
            f"{' — crosses zero' if loss['crosses_zero'] else ' — excludes zero'}",
            f"- Arm-swap permutation p: "
            f"{'<' if permutation['extreme_draws'] == 0 else ''}{float(permutation['two_sided_p_value']):.3e}",
            f"- Discordant pairs: {table['dialect_arm_only_lost']} dialect-only vs "
            f"{table['plain_arm_only_lost']} control-only"
            + (
                f", McNemar p {float(table['mcnemar_p_approx']):.3f}"
                if table.get("mcnemar_p_approx") is not None
                else ""
            ),
            f"- Placebo, non-dialect unit error: {float(placebo['difference']):+.3f} 95% CI "
            f"[{float(placebo_ci['low']):.3f}, {float(placebo_ci['high']):.3f}]"
            f"{' — crosses zero' if placebo['crosses_zero'] else ' — EXCLUDES ZERO, matching is suspect'}",
            "",
        ],
    )


def write_outputs(results: list[JsonObject], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    header = (
        "# Control Pairs Scored By Alignment\n\n"
        "Round 5 asked whether an utterance carrying dialect marking loses more AICC critical spans than the\n"
        "same speaker's dialect-free utterance, and found nothing. It judged a span by searching the whole\n"
        "hypothesis. Every other metric in this project has since moved to alignment, and every correction so\n"
        "far moved a number, so the null needed rescoring on the same standard.\n\n"
        "Each span is located at its evidence eojeol and judged only against the token aligned to that\n"
        "position. The placebo is non-dialect unit error, which should not differ between arms.\n\n"
        "Labels are weak preannotations that no human has reviewed.\n\n"
    )
    (output_dir / "README.md").write_text(header + "\n".join(format_block(r) for r in results), encoding="utf-8")
    summary: JsonObject = {
        "analysis": "round5_control_pairs_rescored_by_alignment",
        "random_seed": RANDOM_SEED,
        "label_status": "weak_preannotation_not_gold",
        "results": list(results),
        "numpy_version": np.__version__,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@app.command()
def main(
    pair_manifest_path: Annotated[Path, typer.Argument(help="Pair manifest JSONL.")],
    case_dir: Annotated[Path, typer.Option("--case-dir")],
    case_annotations: Annotated[Path, typer.Option("--case-annotations")],
    control_dir: Annotated[Path, typer.Option("--control-dir")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
    label_root: Annotated[Path, typer.Option("--label-root")] = Path("data/raw/aihub_gyeongsang_119"),
) -> None:
    if not pair_manifest_path.exists():
        console.print(f"Pair manifest not found: {pair_manifest_path}")
        raise typer.Exit(code=2)
    pair_rows = load_jsonl(pair_manifest_path)
    console.print("Resolving span positions from labels")
    cases = build_utterances(
        load_jsonl(case_dir / "asr_input_manifest.local.jsonl"),
        index_by(load_jsonl(case_annotations), "utterance_id"),
        label_root,
    )
    controls = build_utterances(
        load_jsonl(control_dir / "asr_input_manifest.local.jsonl"),
        index_by(load_jsonl(control_dir / "control_annotations.local.jsonl"), "utterance_id"),
        label_root,
    )
    results: list[JsonObject] = []
    for model in MODELS:
        case_asr_path = case_dir / f"{model}.local.jsonl"
        control_asr_path = control_dir / f"{model}.local.jsonl"
        if not case_asr_path.exists() or not control_asr_path.exists():
            console.print(f"Skipping {model}: ASR output missing on one side")
            continue
        case_asr = index_by(load_jsonl(case_asr_path), "review_id")
        control_asr = index_by(load_jsonl(control_asr_path), "review_id")
        pairs: list[Pair] = []
        for row in pair_rows:
            case_id = text_field(row, "case_review_id")
            control_id = text_field(row, "control_review_id")
            if case_id not in cases or control_id not in controls:
                continue
            if case_id not in case_asr or control_id not in control_asr:
                continue
            pairs.append(
                Pair(
                    speaker_key=text_field(row, "speaker_key"),
                    cohort=text_field(row, "cohort"),
                    category="critical_span",
                    dialect_arm=score(cases[case_id], text_field(case_asr[case_id], "hypothesis")),
                    plain_arm=score(controls[control_id], text_field(control_asr[control_id], "hypothesis")),
                ),
            )
        if pairs:
            results.append(analyze(pairs, model))
    if not results:
        console.print("No model could be scored.")
        raise typer.Exit(code=1)
    write_outputs(results, output_dir)
    console.print(f"Rescored {len(results)} model(s) into {output_dir}")


if __name__ == "__main__":
    app()
