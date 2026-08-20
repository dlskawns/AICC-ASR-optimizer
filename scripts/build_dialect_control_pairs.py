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
#      uv run scripts/build_dialect_control_pairs.py research/experiments/runs/aihub_119_speaker_independent_split/asr_input_manifest.local.jsonl research/experiments/runs/aihub_119_holdout_critical_spans/remined_annotations.local.jsonl research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz --output-dir research/experiments/runs/aihub_119_dialect_control_pairs
# ──────────────────

"""Pair every dialect-bearing utterance with a dialect-free utterance from the same speaker.

Rounds 2 to 4 tried to link dialect marking to AICC damage by checking whether a critical span's
surface overlapped a dialect eojeol. That never worked: six times more data moved the overlapping-span
count from 4 to 5, because AICC markers and dialect-marked eojeols barely co-occur on the surface.

This builds the comparison at utterance level instead. For each holdout utterance that carries both a
dialect eojeol and at least one critical span, it finds another utterance from the *same speaker in the
same recording* that carries critical spans but no dialect eojeol, matched on length. Speaker, channel,
recording session, and topic are therefore held fixed by construction, and dialect marking is the only
systematic difference left.
"""

from __future__ import annotations

import gzip
import json
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Final, TypeAlias, assert_never

import numpy as np
import typer
from build_dialect_taxonomy import JsonValue, text_field
from build_pilot_review_packet import ClipRequest, ClipWindow, write_clip
from remine_critical_spans import mine, slot_rows
from rich.console import Console
from run_dialect_attribution_probe import analysis_units, label_index, payload_for, target_utterance
from semantic_review_pack import stable_hash

JsonObject: TypeAlias = dict[str, JsonValue]

CLIP_DIR: Final[Path] = Path("data/interim/aihub_119_control_clips")
AUDIO_ROOT: Final[Path] = Path("data/raw/aihub_gyeongsang_119_validation_audio")
STAGING_DIR: Final[Path] = Path("data/interim/aihub_119_control_staging")

app = typer.Typer(add_completion=False)
console = Console()


@dataclass(frozen=True, slots=True)
class Pairing:
    case_utterance_id: str
    case_review_id: str
    source_file: str
    speaker_local_id: str
    cohort: str
    control_utterance_id: str
    case_eojeols: int
    control_eojeols: int

    @property
    def control_review_id(self) -> str:
        return f"control-{stable_hash(f'{self.source_file}:{self.control_utterance_id}')}"


def load_jsonl(path: Path) -> list[JsonObject]:
    opener = gzip.open if path.suffix == ".gz" else open
    rows: list[JsonObject] = []
    with opener(path, "rt", encoding="utf-8") as file:
        for line in file:
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


def int_field(mapping: JsonObject, key: str) -> int:
    match mapping.get(key):
        case bool():
            return 0
        case int() | float() as value:
            return int(value)
        case str() as value:
            return int(value) if value.lstrip("-").isdigit() else 0
        case list() | dict() | None:
            return 0
        case unreachable:
            assert_never(unreachable)


def audio_zip_path() -> Path:
    zips = list(AUDIO_ROOT.rglob("*.zip"))
    if len(zips) != 1:
        msg = f"Expected one validation audio zip, found {len(zips)}"
        raise RuntimeError(msg)
    return zips[0]


def audio_members(archive: zipfile.ZipFile) -> dict[str, str]:
    return {Path(name).stem: name for name in archive.namelist() if name.lower().endswith(".wav")}


def transcripts(utterance: JsonObject) -> tuple[str, str]:
    dialect = text_field(utterance, "dialect_form") or text_field(utterance, "form")
    return dialect, text_field(utterance, "standard_form")


def choose_control(
    candidates: list[JsonObject],
    case_eojeols: int,
    tolerance: float,
    payload: JsonObject,
) -> tuple[JsonObject, list[JsonObject]] | None:
    """Pick the length-closest dialect-free utterance from the same speaker that has critical spans.

    Ordering is by absolute length distance and then by utterance id, so the choice is deterministic
    and does not depend on the order the manifest happens to store utterances in.
    """
    low, high = case_eojeols * (1 - tolerance), case_eojeols * (1 + tolerance)
    ranked = sorted(
        (row for row in candidates if low <= int_field(row, "eojeol_count") <= high),
        key=lambda row: (abs(int_field(row, "eojeol_count") - case_eojeols), text_field(row, "utterance_id")),
    )
    for row in ranked:
        utterance_id = text_field(row, "utterance_id")
        try:
            utterance = target_utterance(payload, utterance_id)
        except RuntimeError:
            continue
        dialect_text, standard_text = transcripts(utterance)
        spans = mine(f"{standard_text} {dialect_text}".strip())
        if spans:
            return row, spans
    return None


def build_pairs(
    cases: list[JsonObject],
    annotations: dict[str, JsonObject],
    slice_rows: list[JsonObject],
    label_root: Path,
    tolerance: float,
) -> tuple[list[JsonObject], list[JsonObject], list[Pairing]]:
    by_speaker: dict[tuple[str, str], list[JsonObject]] = defaultdict(list)
    speaker_of: dict[str, str] = {}
    for row in slice_rows:
        source_file = text_field(row, "source_file")
        speaker = text_field(row, "speaker_local_id")
        by_speaker[(source_file, speaker)].append(row)
        speaker_of[text_field(row, "utterance_id")] = speaker

    labels = label_index(label_root)
    cases_by_file: dict[str, list[JsonObject]] = defaultdict(list)
    for case in cases:
        cases_by_file[text_field(case, "source_file")].append(case)

    manifest_rows: list[JsonObject] = []
    annotation_rows: list[JsonObject] = []
    pairings: list[Pairing] = []
    CLIP_DIR.mkdir(parents=True, exist_ok=True)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(audio_zip_path()) as archive:
        members = audio_members(archive)
        for index, (source_file, group) in enumerate(sorted(cases_by_file.items()), start=1):
            payload = payload_for(labels, source_file)
            stem = Path(source_file).stem
            staged = STAGING_DIR / f"{stem}.wav"
            staged.write_bytes(archive.read(members[stem]))
            try:
                for case in group:
                    case_id = text_field(case, "utterance_id")
                    speaker = speaker_of.get(case_id, "")
                    pool = [
                        row
                        for row in by_speaker[(source_file, speaker)]
                        if int_field(row, "dialect_eojeol_count") == 0 and int_field(row, "eojeol_count") >= 5
                    ]
                    case_eojeols = len(
                        [unit for unit in (case.get("dialect_units") or []) if unit]
                    ) + len([unit for unit in (case.get("plain_units") or []) if unit])
                    picked = choose_control(pool, case_eojeols, tolerance, payload)
                    if picked is None:
                        continue
                    control_row, spans = picked
                    control_id = text_field(control_row, "utterance_id")
                    pairing = Pairing(
                        case_utterance_id=case_id,
                        case_review_id=text_field(case, "review_id"),
                        source_file=source_file,
                        speaker_local_id=speaker,
                        cohort=text_field(case, "cohort"),
                        control_utterance_id=control_id,
                        case_eojeols=case_eojeols,
                        control_eojeols=int_field(control_row, "eojeol_count"),
                    )
                    utterance = target_utterance(payload, control_id)
                    window = ClipWindow(
                        float(str(utterance.get("start") or 0.0)),
                        float(str(utterance.get("end") or 0.0)),
                    )
                    clip_path = CLIP_DIR / f"{pairing.control_review_id}.wav"
                    duration = write_clip(ClipRequest(staged, clip_path, window, 0.25))
                    row = analysis_units(
                        {
                            "review_id": pairing.control_review_id,
                            "source_file": source_file,
                            "utterance_id": control_id,
                            "cohort": pairing.cohort,
                        },
                        utterance,
                        CLIP_DIR,
                    )
                    row["clip_duration_sec"] = round(duration, 3)
                    manifest_rows.append(row)
                    annotation_rows.append(
                        {
                            "utterance_id": control_id,
                            "review_id": pairing.control_review_id,
                            "dialect_transcript": text_field(row, "dialect_transcript"),
                            "standard_transcript": text_field(row, "standard_transcript"),
                            "critical_spans": list(spans),
                            "slots": slot_rows(spans),
                            "arm": "control_no_dialect",
                        },
                    )
                    pairings.append(pairing)
            finally:
                staged.unlink(missing_ok=True)
            if index % 20 == 0:
                console.print(f"paired {index}/{len(cases_by_file)} recordings")
    STAGING_DIR.rmdir()
    return manifest_rows, annotation_rows, pairings


def pair_row(pairing: Pairing, annotation: JsonObject) -> JsonObject:
    return {
        "case_review_id": pairing.case_review_id,
        "control_review_id": pairing.control_review_id,
        "speaker_key": stable_hash(f"{pairing.source_file}:{pairing.speaker_local_id}"),
        "cohort": pairing.cohort,
        "case_eojeol_count": pairing.case_eojeols,
        "control_eojeol_count": pairing.control_eojeols,
        "control_critical_spans": len(annotation.get("critical_spans") or []),
    }


def summarize(
    pairings: list[Pairing],
    annotations: list[JsonObject],
    cases: list[JsonObject],
    manifest_rows: list[JsonObject],
) -> JsonObject:
    case_lengths = np.array([p.case_eojeols for p in pairings], dtype=np.float64)
    control_lengths = np.array([p.control_eojeols for p in pairings], dtype=np.float64)
    durations = [float(str(row.get("clip_duration_sec") or 0.0)) for row in manifest_rows]
    return {
        "design": "within_speaker_pairing_dialect_bearing_versus_dialect_free",
        "label_status": "weak_preannotation_not_gold",
        "case_utterances_offered": len(cases),
        "pairs_built": len(pairings),
        "unpaired_cases": len(cases) - len(pairings),
        "distinct_speakers": len({stable_hash(f"{p.source_file}:{p.speaker_local_id}") for p in pairings}),
        "distinct_recordings": len({p.source_file for p in pairings}),
        "cohort_counts": dict(Counter(p.cohort for p in pairings).most_common()),
        "control_critical_spans": sum(len(row.get("critical_spans") or []) for row in annotations),
        "mean_case_eojeols": float(case_lengths.mean()) if case_lengths.size else 0.0,
        "mean_control_eojeols": float(control_lengths.mean()) if control_lengths.size else 0.0,
        "mean_length_difference": float((control_lengths - case_lengths).mean()) if case_lengths.size else 0.0,
        "total_control_clip_minutes": round(sum(durations) / 60, 2),
        "clip_dir": str(CLIP_DIR),
        "matching_rule": "same recording, same speaker, zero dialect eojeols, length-closest, at least one minable critical span",
    }


def write_readme(output_dir: Path, summary: JsonObject) -> None:
    text = (
        "# Dialect Control Pairs\n\n"
        "Surface overlap between critical spans and dialect eojeols was a dead end: going from 50 to 300\n"
        "utterances moved the overlapping-span count only from 4 to 5, because the two rarely co-occur on\n"
        "the surface. This run replaces that design with an utterance-level, within-speaker comparison.\n\n"
        "For each holdout utterance carrying both a dialect eojeol and a critical span, a second utterance\n"
        "is drawn from the same speaker in the same recording that carries critical spans but no dialect\n"
        "eojeol, matched on length. Speaker, microphone, session, and topic are held fixed by construction.\n\n"
        f"**Label status: `{summary['label_status']}`.**\n\n"
        "## Composition\n\n"
        f"- Case utterances offered: {summary['case_utterances_offered']}\n"
        f"- Pairs built: {summary['pairs_built']}, unpaired: {summary['unpaired_cases']}\n"
        f"- Distinct speakers: {summary['distinct_speakers']} across {summary['distinct_recordings']} recordings\n"
        f"- Cohorts: {json.dumps(summary['cohort_counts'], ensure_ascii=False)}\n"
        f"- Critical spans on the control side: {summary['control_critical_spans']}\n"
        f"- Mean length, case vs control: {float(summary['mean_case_eojeols']):.1f} vs "
        f"{float(summary['mean_control_eojeols']):.1f} eojeols "
        f"(mean difference {float(summary['mean_length_difference']):+.2f})\n"
        f"- Control clip duration: {summary['total_control_clip_minutes']} minutes\n\n"
        f"Matching rule: {summary['matching_rule']}.\n\n"
        "## Limits\n\n"
        "- Dialect marking is not randomly assigned. A speaker may reach for dialect forms in harder or more\n"
        "  informal stretches of talk, so the pairing controls who is speaking, not what they chose to say.\n"
        "- Length is matched on eojeol count, not on acoustic duration or speaking rate.\n"
        "- Control spans are mined by the same weak boundary rules and no human has reviewed them.\n\n"
        "Manifests carry transcript text and are local-only.\n"
    )
    (output_dir / "README.md").write_text(text, encoding="utf-8")


def write_outputs(
    manifest_rows: list[JsonObject],
    annotation_rows: list[JsonObject],
    pairings: list[Pairing],
    summary: JsonObject,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "asr_input_manifest.local.jsonl").open("w", encoding="utf-8") as file:
        for row in manifest_rows:
            _ = file.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (output_dir / "control_annotations.local.jsonl").open("w", encoding="utf-8") as file:
        for row in annotation_rows:
            _ = file.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (output_dir / "pair_manifest.jsonl").open("w", encoding="utf-8") as file:
        for pairing, annotation in zip(pairings, annotation_rows, strict=True):
            _ = file.write(json.dumps(pair_row(pairing, annotation), ensure_ascii=False) + "\n")
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_readme(output_dir, summary)


@app.command()
def main(
    holdout_manifest_path: Annotated[Path, typer.Argument(help="Holdout ASR input manifest local JSONL.")],
    holdout_annotations_path: Annotated[Path, typer.Argument(help="Holdout re-mined annotations local JSONL.")],
    slice_manifest_path: Annotated[Path, typer.Argument(help="Busan slice manifest jsonl or jsonl.gz.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
    label_root: Annotated[Path, typer.Option("--label-root")] = Path("data/raw/aihub_gyeongsang_119"),
    length_tolerance: Annotated[float, typer.Option("--length-tolerance", min=0.05, max=2.0)] = 0.4,
) -> None:
    for path in (holdout_manifest_path, holdout_annotations_path, slice_manifest_path):
        if not path.exists():
            console.print(f"Input not found: {path}")
            raise typer.Exit(code=2)
    manifest = {text_field(row, "utterance_id"): row for row in load_jsonl(holdout_manifest_path)}
    annotations = {text_field(row, "utterance_id"): row for row in load_jsonl(holdout_annotations_path)}
    cases = [
        manifest[utterance_id]
        for utterance_id, row in annotations.items()
        if row.get("critical_spans") and utterance_id in manifest and manifest[utterance_id].get("dialect_units")
    ]
    if not cases:
        console.print("No case utterances carry both a dialect unit and a critical span.")
        raise typer.Exit(code=1)
    console.print(f"Pairing {len(cases)} case utterances")
    manifest_rows, annotation_rows, pairings = build_pairs(
        cases, annotations, load_jsonl(slice_manifest_path), label_root, length_tolerance,
    )
    summary = summarize(pairings, annotation_rows, cases, manifest_rows)
    write_outputs(manifest_rows, annotation_rows, pairings, summary, output_dir)
    console.print(f"Built {len(pairings)} pairs into {output_dir}")


if __name__ == "__main__":
    app()
