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
#      uv run scripts/classify_cue_substitution.py research/experiments/runs/aihub_119_cue_bearing_split --output-dir research/experiments/runs/aihub_119_cue_substitution
# ──────────────────

"""Split a lost AICC cue into substitution and deletion, and record what it became.

Round 7 established that when a cue word is dialect-marked it is more often absent from the hypothesis,
where absent means neither the dialect surface nor the standard form is there. For a contact centre the
two ways of being absent are not the same:

- deletion, where the cue position is simply empty, leaves a gap a downstream model can notice;
- substitution, where some other word sits in the cue position, produces a confident wrong reading.

This anchors on the cue's neighbouring eojeols. If both neighbours survive in the hypothesis, whatever
lies between them is what the cue became; if nothing lies between them, the cue was deleted. Where the
neighbours are lost too, the case is reported as `context_lost` rather than guessed at.

The per-case inventory of substituting surfaces is transcript-derived and stays local. The shareable
summary carries counts only.
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
from build_dialect_taxonomy import JsonValue, list_of_mappings, text_field
from rich.console import Console
from run_dialect_attribution_probe import label_index, payload_for, target_utterance

JsonObject: TypeAlias = dict[str, JsonValue]
Verdict: TypeAlias = Literal["substitution", "deletion", "context_lost"]

MODELS: Final[tuple[str, ...]] = ("faster_whisper_medium", "faster_whisper_large_v3", "wav2vec2_korean")
MAX_GAP_TOKENS: Final[int] = 3

app = typer.Typer(add_completion=False)
console = Console()


@dataclass(frozen=True, slots=True)
class Case:
    review_id: str
    arm: str
    cohort: str
    category: str
    dialect_surface: str
    standard_surface: str
    reference_tokens: tuple[str, ...]
    cue_index: int


@dataclass(frozen=True, slots=True)
class Judged:
    case: Case
    verdict: Verdict
    replacement: tuple[str, ...]


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


def starts_with(token: str, needle: str) -> bool:
    target = clean(needle)
    return bool(target) and clean(token).startswith(target)


def present(hypothesis_tokens: list[str], needle: str) -> bool:
    return any(starts_with(token, needle) for token in hypothesis_tokens)


def build_cases(split_dir: Path, label_root: Path) -> list[Case]:
    annotations = load_jsonl(split_dir / "cue_annotations.local.jsonl")
    manifest = index_by(load_jsonl(split_dir / "asr_input_manifest.local.jsonl"), "review_id")
    labels = label_index(label_root)
    payloads: dict[str, JsonObject] = {}
    cases: list[Case] = []
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
        wanted = clean(text_field(row, "cue_evidence_eojeol"))
        cue_index = next(
            (
                index
                for index, eojeol in enumerate(eojeols)
                if clean(text_field(eojeol, "eojeol")) == wanted or clean(text_field(eojeol, "standard")) == wanted
            ),
            -1,
        )
        if cue_index < 0:
            continue
        cases.append(
            Case(
                review_id=review_id,
                arm=text_field(row, "arm"),
                cohort=text_field(manifest_row, "cohort"),
                category=text_field(row, "cue_category"),
                dialect_surface=text_field(eojeols[cue_index], "eojeol"),
                standard_surface=text_field(eojeols[cue_index], "standard") or text_field(eojeols[cue_index], "eojeol"),
                reference_tokens=tuple(text_field(eojeol, "eojeol") for eojeol in eojeols),
                cue_index=cue_index,
            ),
        )
    return cases


def anchor_index(hypothesis_tokens: list[str], needle: str, after: int = -1) -> int:
    for index in range(after + 1, len(hypothesis_tokens)):
        if starts_with(hypothesis_tokens[index], needle):
            return index
    return -1


def judge(case: Case, hypothesis: str) -> Judged:
    """Locate the cue position between its surviving neighbours and read off what sits there."""
    tokens = [token for token in hypothesis.split() if clean(token)]
    left = next(
        (
            case.reference_tokens[index]
            for index in range(case.cue_index - 1, -1, -1)
            if present(tokens, case.reference_tokens[index])
        ),
        "",
    )
    right = next(
        (
            case.reference_tokens[index]
            for index in range(case.cue_index + 1, len(case.reference_tokens))
            if present(tokens, case.reference_tokens[index])
        ),
        "",
    )
    if not left or not right:
        return Judged(case, "context_lost", ())
    left_index = anchor_index(tokens, left)
    right_index = anchor_index(tokens, right, left_index)
    if left_index < 0 or right_index < 0:
        return Judged(case, "context_lost", ())
    gap = tokens[left_index + 1 : right_index]
    if not gap:
        return Judged(case, "deletion", ())
    if len(gap) > MAX_GAP_TOKENS:
        # A wide gap means the alignment drifted, not that one word replaced the cue.
        return Judged(case, "context_lost", ())
    return Judged(case, "substitution", tuple(gap))


def case_row(judged: Judged) -> JsonObject:
    return {
        "review_id": judged.case.review_id,
        "arm": judged.case.arm,
        "cohort": judged.case.cohort,
        "cue_category": judged.case.category,
        "cue_dialect_surface": judged.case.dialect_surface,
        "cue_standard_surface": judged.case.standard_surface,
        "verdict": judged.verdict,
        "replacement_tokens": list(judged.replacement),
    }


def block(rows: list[Judged]) -> JsonObject:
    counts = Counter(row.verdict for row in rows)
    total = len(rows)
    resolved = counts["substitution"] + counts["deletion"]
    return {
        "absent_cues": total,
        "counts": dict(counts.most_common()),
        "resolved_cues": resolved,
        "substitution_share_of_resolved": counts["substitution"] / resolved if resolved else None,
        "deletion_share_of_resolved": counts["deletion"] / resolved if resolved else None,
        "context_lost_share": counts["context_lost"] / total if total else None,
    }


def analyze(judged: list[Judged], model: str) -> JsonObject:
    dialect_arm = [row for row in judged if row.case.arm == "case"]
    plain_arm = [row for row in judged if row.case.arm == "control"]
    by_category: dict[str, list[Judged]] = {}
    for row in dialect_arm:
        by_category.setdefault(row.case.category, []).append(row)
    return {
        "model": model,
        "dialect_arm": block(dialect_arm),
        "plain_arm": block(plain_arm),
        "dialect_arm_by_category": {
            name: block(rows) for name, rows in sorted(by_category.items(), key=lambda item: -len(item[1]))
        },
        "distinct_replacement_surfaces": len(
            {row.replacement for row in dialect_arm if row.verdict == "substitution"},
        ),
    }


def format_block(result: JsonObject) -> str:
    dialect = result["dialect_arm"]
    plain = result["plain_arm"]
    assert isinstance(dialect, dict) and isinstance(plain, dict)

    def share(stats: JsonObject, key: str) -> str:
        value = stats.get(key)
        return f"{float(value):.3f}" if isinstance(value, (int, float)) else "n/a"

    lines = [
        f"## {result['model']}",
        "",
        "| Arm | Absent cues | Substitution | Deletion | Context lost | Substitution share of resolved |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for label, stats in (("cue word is dialect-marked", dialect), ("cue word is plain", plain)):
        counts = stats["counts"]
        assert isinstance(counts, dict)
        lines.append(
            f"| {label} | {stats['absent_cues']} | {counts.get('substitution', 0)} | "
            f"{counts.get('deletion', 0)} | {counts.get('context_lost', 0)} | "
            f"{share(stats, 'substitution_share_of_resolved')} |",
        )
    lines.extend(["", f"- Distinct replacement surfaces in the dialect arm: {result['distinct_replacement_surfaces']}"])
    categories = result["dialect_arm_by_category"]
    assert isinstance(categories, dict)
    lines.extend(["", "| Cue category, dialect arm | Absent | Substitution share of resolved |", "|---|---:|---:|"])
    lines.extend(
        f"| {name} | {stats['absent_cues']} | {share(stats, 'substitution_share_of_resolved')} |"
        for name, stats in categories.items()
        if isinstance(stats, dict)
    )
    lines.append("")
    return "\n".join(lines)


def write_readme(output_dir: Path, results: list[JsonObject]) -> None:
    header = (
        "# Cue Substitution Versus Deletion\n\n"
        "Round 7 counted a cue as damaged when neither its dialect surface nor its standard form reached the\n"
        "hypothesis. A contact centre cares which kind of absence it was.\n\n"
        "- Deletion leaves the cue position empty. Downstream, the signal is missing and can be noticed as missing.\n"
        "- Substitution puts another word in the cue position, which reads as a confident wrong answer.\n\n"
        "The verdict comes from the cue's neighbouring eojeols. When both survive in the hypothesis, whatever\n"
        "sits between them is what the cue became. When the neighbours are gone too, or the gap is wider than\n"
        "three tokens, the alignment is not trustworthy and the case is reported as `context_lost` rather than\n"
        "forced into one of the two classes.\n\n"
        "Read `context_lost` as a property of the model as much as of the method: a system whose output drifts\n"
        "far from the reference gives no anchors to align against.\n\n"
        "The inventory of what each lost cue became is transcript-derived and stays in the local case file.\n"
        "Labels are weak preannotations that no human has reviewed.\n\n"
    )
    (output_dir / "README.md").write_text(header + "\n".join(format_block(r) for r in results), encoding="utf-8")


def write_outputs(results: list[JsonObject], cases: dict[str, list[Judged]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "cue_substitution_cases.local.jsonl").open("w", encoding="utf-8") as file:
        for model, rows in cases.items():
            for row in rows:
                payload = case_row(row)
                payload["model"] = model
                _ = file.write(json.dumps(payload, ensure_ascii=False) + "\n")
    summary: JsonObject = {
        "analysis": "cue_absence_split_into_substitution_and_deletion",
        "label_status": "weak_preannotation_not_gold",
        "anchor_rule": "nearest surviving neighbour eojeol on each side; gap wider than three tokens is not trusted",
        "results": list(results),
        "numpy_version": np.__version__,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_readme(output_dir, results)


def absent_cases(cases: list[Case], asr: dict[str, JsonObject]) -> list[Judged]:
    """Keep only the cues round 7 would call absent, then judge how they were absent."""
    judged: list[Judged] = []
    for case in cases:
        row = asr.get(case.review_id)
        if row is None:
            continue
        hypothesis = text_field(row, "hypothesis")
        tokens = [token for token in hypothesis.split() if clean(token)]
        if present(tokens, case.dialect_surface):
            continue
        if clean(case.standard_surface) != clean(case.dialect_surface) and present(tokens, case.standard_surface):
            continue
        judged.append(judge(case, hypothesis))
    return judged


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
    results: list[JsonObject] = []
    judged_by_model: dict[str, list[Judged]] = {}
    for model in MODELS:
        asr_path = split_dir / f"{model}.local.jsonl"
        if not asr_path.exists():
            console.print(f"Skipping {model}: ASR output missing")
            continue
        judged = absent_cases(cases, index_by(load_jsonl(asr_path), "review_id"))
        if not judged:
            continue
        judged_by_model[model] = judged
        results.append(analyze(judged, model))
    if not results:
        console.print("No absent cue could be judged.")
        raise typer.Exit(code=1)
    write_outputs(results, judged_by_model, output_dir)
    console.print(f"Judged absent cues for {len(results)} model(s) into {output_dir}")


if __name__ == "__main__":
    app()
