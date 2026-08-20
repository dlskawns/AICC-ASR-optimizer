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
#      uv run scripts/build_speaker_independent_split.py research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz --output-dir research/experiments/runs/aihub_119_speaker_independent_split
# ──────────────────

"""Build a speaker-disjoint holdout split for the dialect attribution probe.

The 50-utterance pilot is too small to measure anything about individual speakers, and it reuses the
same 46 recordings throughout. This script builds a larger split that shares no recording with the
pilot and caps how many utterances any one speaker contributes, so a handful of speakers cannot carry
the result.

It emits the same manifest schema as `run_dialect_attribution_probe.py`, so the ASR runners, the
significance tests, and the critical-span audit all consume the output unchanged.

Clips are cut recording by recording and the extracted source WAV is deleted straight after, so peak
disk stays at one recording rather than the whole subset.
"""

from __future__ import annotations

import gzip
import json
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Final, TypeAlias, assert_never

import numpy as np
import typer
from build_dialect_taxonomy import JsonValue, cohort, text_field
from build_pilot_review_packet import ClipRequest, ClipWindow, write_clip
from rich.console import Console
from run_dialect_attribution_probe import analysis_units, payload_for, target_utterance
from semantic_review_pack import stable_hash

JsonObject: TypeAlias = dict[str, JsonValue]

CLIP_DIR: Final[Path] = Path("data/interim/aihub_119_holdout_clips")
AUDIO_ROOT: Final[Path] = Path("data/raw/aihub_gyeongsang_119_validation_audio")
STAGING_DIR: Final[Path] = Path("data/interim/aihub_119_holdout_staging")
COHORTS: Final[tuple[str, ...]] = ("busan", "gyeongsang_other")

app = typer.Typer(add_completion=False)
console = Console()


@dataclass(frozen=True, slots=True)
class Candidate:
    source_file: str
    utterance_id: str
    speaker_local_id: str
    cohort: str
    slice_label: str
    age: str
    sex: str
    topic: str
    eojeol_count: int
    dialect_eojeol_count: int

    @property
    def speaker_key(self) -> str:
        return f"{self.source_file}:{self.speaker_local_id}"

    @property
    def review_id(self) -> str:
        return f"holdout-{stable_hash(f'{self.source_file}:{self.utterance_id}')}"


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


def load_manifest(path: Path) -> list[JsonObject]:
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


def audio_zip_path() -> Path:
    zips = list(AUDIO_ROOT.rglob("*.zip"))
    if len(zips) != 1:
        msg = f"Expected one validation audio zip, found {len(zips)}"
        raise RuntimeError(msg)
    return zips[0]


def audio_members(archive: zipfile.ZipFile) -> dict[str, str]:
    return {Path(name).stem: name for name in archive.namelist() if name.lower().endswith(".wav")}


def pilot_stems(pilot_audio_dir: Path) -> set[str]:
    return {path.stem for path in pilot_audio_dir.glob("*.wav")}


def candidates(
    rows: list[JsonObject],
    available: set[str],
    excluded: set[str],
    min_eojeols: int,
) -> list[Candidate]:
    found: list[Candidate] = []
    for row in rows:
        source_file = text_field(row, "source_file")
        stem = Path(source_file).stem
        if stem not in available or stem in excluded:
            continue
        if int_field(row, "dialect_eojeol_count") < 1 or int_field(row, "eojeol_count") < min_eojeols:
            continue
        cohort_label = cohort(text_field(row, "slice_label"))
        if cohort_label not in COHORTS:
            continue
        found.append(
            Candidate(
                source_file=source_file,
                utterance_id=text_field(row, "utterance_id"),
                speaker_local_id=text_field(row, "speaker_local_id"),
                cohort=cohort_label,
                slice_label=text_field(row, "slice_label"),
                age=text_field(row, "age"),
                sex=text_field(row, "sex"),
                topic=text_field(row, "topic"),
                eojeol_count=int_field(row, "eojeol_count"),
                dialect_eojeol_count=int_field(row, "dialect_eojeol_count"),
            ),
        )
    return found


def select(
    pool: list[Candidate],
    per_cohort: int,
    max_per_speaker: int,
) -> list[Candidate]:
    """Round-robin over speakers so no speaker fills the split before others are reached.

    Candidates are ordered by review_id, which is a content hash, so the choice is deterministic
    without a random seed and does not follow recording order.
    """
    chosen: list[Candidate] = []
    for cohort_label in COHORTS:
        by_speaker: dict[str, list[Candidate]] = {}
        for candidate in sorted(
            (item for item in pool if item.cohort == cohort_label),
            key=lambda item: item.review_id,
        ):
            by_speaker.setdefault(candidate.speaker_key, []).append(candidate)
        taken: list[Candidate] = []
        for round_index in range(max_per_speaker):
            for speaker in sorted(by_speaker):
                if len(taken) >= per_cohort:
                    break
                utterances = by_speaker[speaker]
                if round_index < len(utterances):
                    taken.append(utterances[round_index])
            if len(taken) >= per_cohort:
                break
        chosen.extend(taken[:per_cohort])
    return chosen


def cut_clips(selected: list[Candidate], label_root: Path, padding_seconds: float) -> list[JsonObject]:
    """Extract one recording at a time, cut every clip it owns, then delete the recording."""
    from run_dialect_attribution_probe import label_index

    labels = label_index(label_root)
    by_file: dict[str, list[Candidate]] = {}
    for candidate in selected:
        by_file.setdefault(candidate.source_file, []).append(candidate)
    CLIP_DIR.mkdir(parents=True, exist_ok=True)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[JsonObject] = []
    with zipfile.ZipFile(audio_zip_path()) as archive:
        members = audio_members(archive)
        for index, (source_file, group) in enumerate(sorted(by_file.items()), start=1):
            stem = Path(source_file).stem
            staged = STAGING_DIR / f"{stem}.wav"
            staged.write_bytes(archive.read(members[stem]))
            try:
                payload = payload_for(labels, source_file)
                for candidate in group:
                    utterance = target_utterance(payload, candidate.utterance_id)
                    window = ClipWindow(
                        float(str(utterance.get("start") or 0.0)),
                        float(str(utterance.get("end") or 0.0)),
                    )
                    clip_path = CLIP_DIR / f"{candidate.review_id}.wav"
                    duration = write_clip(ClipRequest(staged, clip_path, window, padding_seconds))
                    row = analysis_units(
                        {
                            "review_id": candidate.review_id,
                            "source_file": source_file,
                            "utterance_id": candidate.utterance_id,
                            "cohort": candidate.cohort,
                        },
                        utterance,
                        CLIP_DIR,
                    )
                    row["clip_duration_sec"] = round(duration, 3)
                    row["speaker_key"] = stable_hash(candidate.speaker_key)
                    row["slice_label"] = candidate.slice_label
                    manifest_rows.append(row)
            finally:
                staged.unlink(missing_ok=True)
            if index % 25 == 0:
                console.print(f"cut {index}/{len(by_file)} recordings")
    STAGING_DIR.rmdir()
    return manifest_rows


def shareable_row(row: JsonObject, candidate: Candidate) -> JsonObject:
    return {
        "review_id": text_field(row, "review_id"),
        "utterance_hash": text_field(row, "utterance_hash"),
        "speaker_key": text_field(row, "speaker_key"),
        "cohort": text_field(row, "cohort"),
        "slice_label": candidate.slice_label,
        "age_band": candidate.age,
        "sex": candidate.sex,
        "topic": candidate.topic,
        "eojeol_count": candidate.eojeol_count,
        "dialect_eojeol_count": candidate.dialect_eojeol_count,
        "clip_duration_sec": row.get("clip_duration_sec"),
    }


def summarize(
    rows: list[JsonObject],
    shareable: list[JsonObject],
    pool_size: int,
    per_cohort: int,
    max_per_speaker: int,
    excluded: set[str],
) -> JsonObject:
    def count_units(key: str) -> int:
        total = 0
        for row in rows:
            value = row.get(key)
            if isinstance(value, list):
                total += len(value)
        return total

    durations = [
        float(str(row.get("clip_duration_sec") or 0.0)) for row in rows
    ]
    return {
        "split": "speaker_disjoint_holdout_from_pilot",
        "candidate_pool": pool_size,
        "selected_utterances": len(rows),
        "target_per_cohort": per_cohort,
        "max_utterances_per_speaker": max_per_speaker,
        "excluded_pilot_recordings": len(excluded),
        "distinct_speakers": len({text_field(row, "speaker_key") for row in shareable}),
        "distinct_recordings": len({text_field(row, "source_file") for row in rows}),
        "cohort_counts": dict(Counter(text_field(row, "cohort") for row in rows).most_common()),
        "age_band_counts": dict(Counter(text_field(row, "age_band") for row in shareable).most_common()),
        "sex_counts": dict(Counter(text_field(row, "sex") for row in shareable).most_common()),
        "dialect_units": count_units("dialect_units"),
        "plain_units": count_units("plain_units"),
        "total_clip_minutes": round(sum(durations) / 60, 2),
        "clip_dir": str(CLIP_DIR),
        "gold_status": "not_gold_no_human_review",
        "numpy_version": np.__version__,
    }


def write_readme(output_dir: Path, summary: JsonObject) -> None:
    text = (
        "# Speaker-Independent Holdout Split\n\n"
        "The 50-utterance pilot reuses 46 recordings and cannot say anything about speaker generalisation.\n"
        "This split shares no recording with the pilot and caps how many utterances one speaker contributes.\n\n"
        f"**Gold status: `{summary['gold_status']}`.**\n\n"
        "## Composition\n\n"
        f"- Candidate pool: {summary['candidate_pool']} utterances with at least one dialect-marked eojeol\n"
        f"- Selected: {summary['selected_utterances']} utterances\n"
        f"- Distinct speakers: {summary['distinct_speakers']}\n"
        f"- Cap per speaker: {summary['max_utterances_per_speaker']} utterances\n"
        f"- Excluded pilot recordings: {summary['excluded_pilot_recordings']}\n"
        f"- Cohorts: {json.dumps(summary['cohort_counts'], ensure_ascii=False)}\n"
        f"- Age bands: {json.dumps(summary['age_band_counts'], ensure_ascii=False)}\n"
        f"- Sex: {json.dumps(summary['sex_counts'], ensure_ascii=False)}\n"
        f"- Dialect units: {summary['dialect_units']}, non-dialect units: {summary['plain_units']}\n"
        f"- Total clip duration: {summary['total_clip_minutes']} minutes\n"
        f"- Clip dir: `{summary['clip_dir']}`\n\n"
        "## How To Use It\n\n"
        "`asr_input_manifest.local.jsonl` uses the same schema as the pilot probe, so the ASR runners, the\n"
        "clustered significance tests, and the critical-span audit all take it without modification.\n\n"
        "Selection is deterministic: candidates are ordered by a content hash and taken round-robin across\n"
        "speakers, so re-running reproduces the same split without a random seed.\n\n"
        "## Limits\n\n"
        "- Speaker identity is only known within a recording, so speaker keys are recording-scoped. If the same\n"
        "  person appears in two recordings under different local ids, this split cannot tell.\n"
        "- The split is disjoint from the pilot by recording, which is the strongest disjointness the metadata\n"
        "  supports. It is not a certified speaker-independent test set.\n"
        "- No human has reviewed any label here.\n\n"
        "The manifest carries transcript text and is local-only.\n"
    )
    (output_dir / "README.md").write_text(text, encoding="utf-8")


def write_outputs(rows: list[JsonObject], shareable: list[JsonObject], summary: JsonObject, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "asr_input_manifest.local.jsonl").open("w", encoding="utf-8") as file:
        for row in rows:
            _ = file.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (output_dir / "split_manifest.jsonl").open("w", encoding="utf-8") as file:
        for row in shareable:
            _ = file.write(json.dumps(row, ensure_ascii=False) + "\n")
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_readme(output_dir, summary)


@app.command()
def main(
    slice_manifest_path: Annotated[Path, typer.Argument(help="Busan slice manifest jsonl or jsonl.gz.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
    label_root: Annotated[Path, typer.Option("--label-root")] = Path("data/raw/aihub_gyeongsang_119"),
    pilot_audio_dir: Annotated[Path, typer.Option("--pilot-audio-dir")] = Path("data/interim/aihub_119_pilot_audio"),
    per_cohort: Annotated[int, typer.Option("--per-cohort", min=1)] = 150,
    max_per_speaker: Annotated[int, typer.Option("--max-per-speaker", min=1)] = 2,
    min_eojeols: Annotated[int, typer.Option("--min-eojeols", min=1)] = 5,
    padding_seconds: Annotated[float, typer.Option("--padding-seconds", min=0.0)] = 0.25,
) -> None:
    if not slice_manifest_path.exists():
        console.print(f"Slice manifest not found: {slice_manifest_path}")
        raise typer.Exit(code=2)
    with zipfile.ZipFile(audio_zip_path()) as archive:
        available = set(audio_members(archive))
    excluded = pilot_stems(pilot_audio_dir)
    pool = candidates(load_manifest(slice_manifest_path), available, excluded, min_eojeols)
    if not pool:
        console.print("No candidate utterances after filtering.")
        raise typer.Exit(code=1)
    selected = select(pool, per_cohort, max_per_speaker)
    console.print(f"Selected {len(selected)} utterances from a pool of {len(pool)}; cutting clips")
    rows = cut_clips(selected, label_root, padding_seconds)
    by_id = {candidate.review_id: candidate for candidate in selected}
    shareable = [shareable_row(row, by_id[text_field(row, "review_id")]) for row in rows]
    summary = summarize(rows, shareable, len(pool), per_cohort, max_per_speaker, excluded)
    write_outputs(rows, shareable, summary, output_dir)
    console.print(f"Wrote {len(rows)} utterances to {output_dir}")


if __name__ == "__main__":
    app()
