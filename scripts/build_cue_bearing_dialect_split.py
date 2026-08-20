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
#      uv run scripts/build_cue_bearing_dialect_split.py data/raw/aihub_gyeongsang_119 research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz --output-dir research/experiments/runs/aihub_119_cue_bearing_split
# ──────────────────

"""Collect utterances where a dialect-marked eojeol itself carries the AICC cue, and pair them.

Round 5 found that dialect marking somewhere in an utterance does not raise AICC critical-span loss,
which suggests dialect fragility is local to the dialect tokens. That reading makes a sharp prediction:
when the AICC cue *is* the dialect token, loss should rise.

Testing it needs cases where the cue-bearing eojeol is itself dialect-marked. Those are rare in any
random sample - five of ninety-three in the round 4 holdout - so this script mines the full label set
for them, then pairs each one with an utterance from the same speaker where the same cue category is
carried by a non-dialect eojeol.

Inside a pair the speaker, the recording, and the cue category are fixed. The only difference is
whether the cue word is dialect-marked.
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
from build_dialect_taxonomy import JsonValue, cohort, list_of_mappings, text_field
from build_pilot_review_packet import ClipRequest, ClipWindow, write_clip
from remine_critical_spans import clean, mine, slot_rows, tokens
from rich.console import Console
from run_dialect_attribution_probe import analysis_units, label_index, payload_for, target_utterance
from semantic_review_pack import stable_hash

JsonObject: TypeAlias = dict[str, JsonValue]

CLIP_DIR: Final[Path] = Path("data/interim/aihub_119_cue_clips")
AUDIO_ROOT: Final[Path] = Path("data/raw/aihub_gyeongsang_119_validation_audio")
STAGING_DIR: Final[Path] = Path("data/interim/aihub_119_cue_staging")
COHORTS: Final[tuple[str, ...]] = ("busan", "gyeongsang_other")


@dataclass(frozen=True, slots=True)
class CueHit:
    source_file: str
    utterance_id: str
    speaker_local_id: str
    cohort: str
    category: str
    span_text: str
    evidence_eojeol: str
    dialect_marked: bool
    spans: tuple[JsonObject, ...]

    @property
    def speaker_key(self) -> str:
        return f"{self.source_file}:{self.speaker_local_id}"

    def review_id(self, arm: str) -> str:
        return f"cue{arm}-{stable_hash(f'{self.source_file}:{self.utterance_id}:{self.category}')}"


app = typer.Typer(add_completion=False)
console = Console()


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


def dialect_surfaces(utterance: JsonObject) -> set[str]:
    surfaces: set[str] = set()
    for eojeol in list_of_mappings(utterance.get("eojeolList")):
        if eojeol.get("isDialect") is not True:
            continue
        for key in ("eojeol", "standard"):
            surface = clean(text_field(eojeol, key))
            if surface:
                surfaces.add(surface)
    return surfaces


def cue_hits(utterance: JsonObject, source_file: str, speaker: str, cohort_label: str) -> list[CueHit]:
    """Mine the utterance, then mark each cue by whether its eojeol is dialect-marked."""
    dialect_text = text_field(utterance, "dialect_form") or text_field(utterance, "form")
    standard_text = text_field(utterance, "standard_form")
    spans = mine(f"{standard_text} {dialect_text}".strip())
    if not spans:
        return []
    surfaces = dialect_surfaces(utterance)
    hits: list[CueHit] = []
    for span in spans:
        evidence = clean(text_field(span, "evidence_eojeol"))
        if not evidence:
            continue
        marked = any(evidence == surface or evidence.startswith(surface) or surface.startswith(evidence) for surface in surfaces)
        hits.append(
            CueHit(
                source_file=source_file,
                utterance_id=text_field(utterance, "id"),
                speaker_local_id=speaker,
                cohort=cohort_label,
                category=text_field(span, "category"),
                span_text=text_field(span, "span_text"),
                evidence_eojeol=evidence,
                dialect_marked=marked,
                spans=tuple(spans),
            ),
        )
    return hits


def collect(
    label_root: Path,
    slices: dict[str, str],
    speakers: dict[str, str],
    available: set[str],
    excluded: set[str],
) -> tuple[list[CueHit], list[CueHit]]:
    """Return (cue-bearing dialect hits, non-dialect cue hits) across the whole label set."""
    marked: list[CueHit] = []
    plain: list[CueHit] = []
    for zip_path in sorted(label_root.rglob("*.zip")):
        with zipfile.ZipFile(zip_path) as archive:
            for name in sorted(item for item in archive.namelist() if item.endswith(".json")):
                stem = Path(name).stem
                if stem not in available or stem in excluded:
                    continue
                payload = json.loads(archive.read(name).decode("utf-8"))
                source_file = Path(name).name
                for utterance in list_of_mappings(payload.get("utterance")):
                    utterance_id = text_field(utterance, "id")
                    cohort_label = cohort(slices.get(f"{source_file}:{utterance_id}", "other"))
                    if cohort_label not in COHORTS:
                        continue
                    speaker = speakers.get(utterance_id, "")
                    for hit in cue_hits(utterance, source_file, speaker, cohort_label):
                        (marked if hit.dialect_marked else plain).append(hit)
    return marked, plain


def pair_hits(
    marked: list[CueHit],
    plain: list[CueHit],
    per_speaker: int,
    categories: tuple[str, ...] | None = None,
) -> list[tuple[CueHit, CueHit]]:
    """Match each cue-bearing dialect hit to a same-speaker, same-category, non-dialect hit."""
    pool: dict[tuple[str, str], list[CueHit]] = defaultdict(list)
    for hit in plain:
        pool[(hit.speaker_key, hit.category)].append(hit)
    for key in pool:
        pool[key].sort(key=lambda item: item.utterance_id)
    used: set[str] = set()
    taken: Counter[str] = Counter()
    pairs: list[tuple[CueHit, CueHit]] = []
    for hit in sorted(marked, key=lambda item: (item.speaker_key, item.category, item.utterance_id)):
        if categories is not None and hit.category not in categories:
            continue
        if taken[hit.speaker_key] >= per_speaker:
            continue
        candidates = pool.get((hit.speaker_key, hit.category), [])
        control = next(
            (item for item in candidates if item.utterance_id not in used and item.utterance_id != hit.utterance_id),
            None,
        )
        if control is None:
            continue
        used.add(control.utterance_id)
        used.add(hit.utterance_id)
        taken[hit.speaker_key] += 1
        pairs.append((hit, control))
    return pairs


def cut_and_describe(
    pairs: list[tuple[CueHit, CueHit]],
    label_root: Path,
    padding_seconds: float,
) -> tuple[list[JsonObject], list[JsonObject], list[JsonObject]]:
    labels = label_index(label_root)
    by_file: dict[str, list[tuple[CueHit, str]]] = defaultdict(list)
    for case, control in pairs:
        by_file[case.source_file].append((case, "case"))
        by_file[control.source_file].append((control, "control"))
    CLIP_DIR.mkdir(parents=True, exist_ok=True)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[JsonObject] = []
    annotation_rows: list[JsonObject] = []
    with zipfile.ZipFile(audio_zip_path()) as archive:
        members = audio_members(archive)
        for index, (source_file, group) in enumerate(sorted(by_file.items()), start=1):
            payload = payload_for(labels, source_file)
            stem = Path(source_file).stem
            staged = STAGING_DIR / f"{stem}.wav"
            staged.write_bytes(archive.read(members[stem]))
            try:
                for hit, arm in group:
                    utterance = target_utterance(payload, hit.utterance_id)
                    window = ClipWindow(
                        float(str(utterance.get("start") or 0.0)),
                        float(str(utterance.get("end") or 0.0)),
                    )
                    review_id = hit.review_id(arm)
                    clip_path = CLIP_DIR / f"{review_id}.wav"
                    duration = write_clip(ClipRequest(staged, clip_path, window, padding_seconds))
                    row = analysis_units(
                        {
                            "review_id": review_id,
                            "source_file": source_file,
                            "utterance_id": hit.utterance_id,
                            "cohort": hit.cohort,
                        },
                        utterance,
                        CLIP_DIR,
                    )
                    row["clip_duration_sec"] = round(duration, 3)
                    row["arm"] = arm
                    manifest_rows.append(row)
                    annotation_rows.append(
                        {
                            "utterance_id": hit.utterance_id,
                            "review_id": review_id,
                            "arm": arm,
                            "cue_category": hit.category,
                            "cue_span_text": hit.span_text,
                            "cue_evidence_eojeol": hit.evidence_eojeol,
                            "cue_is_dialect_marked": hit.dialect_marked,
                            "dialect_transcript": text_field(row, "dialect_transcript"),
                            "standard_transcript": text_field(row, "standard_transcript"),
                            "critical_spans": [
                                {
                                    "span_text": hit.span_text,
                                    "category": hit.category,
                                    "business_risk": "high",
                                    "expected_asr_preservation": f"preserve {hit.category} meaning",
                                    "evidence_eojeol": hit.evidence_eojeol,
                                },
                            ],
                            "slots": slot_rows(list(hit.spans)),
                        },
                    )
            finally:
                staged.unlink(missing_ok=True)
            if index % 25 == 0:
                console.print(f"cut {index}/{len(by_file)} recordings")
    STAGING_DIR.rmdir()
    pair_rows = [
        {
            "case_review_id": case.review_id("case"),
            "control_review_id": control.review_id("control"),
            "speaker_key": stable_hash(case.speaker_key),
            "cohort": case.cohort,
            "cue_category": case.category,
        }
        for case, control in pairs
    ]
    return manifest_rows, annotation_rows, pair_rows


def summarize(
    marked: list[CueHit],
    plain: list[CueHit],
    pairs: list[tuple[CueHit, CueHit]],
    manifest_rows: list[JsonObject],
) -> JsonObject:
    durations = [float(str(row.get("clip_duration_sec") or 0.0)) for row in manifest_rows]
    return {
        "design": "within_speaker_within_category_pairing_of_cue_bearing_eojeols",
        "label_status": "weak_preannotation_not_gold",
        "cue_bearing_dialect_hits_found": len(marked),
        "non_dialect_cue_hits_found": len(plain),
        "pairs_built": len(pairs),
        "distinct_speakers": len({stable_hash(case.speaker_key) for case, _ in pairs}),
        "distinct_recordings": len({row for case, control in pairs for row in (case.source_file, control.source_file)}),
        "cohort_counts": dict(Counter(case.cohort for case, _ in pairs).most_common()),
        "cue_category_counts": dict(Counter(case.category for case, _ in pairs).most_common()),
        "clips": len(manifest_rows),
        "total_clip_minutes": round(sum(durations) / 60, 2),
        "clip_dir": str(CLIP_DIR),
        "matching_rule": "same speaker, same cue category, cue eojeol dialect-marked versus not",
    }


def write_readme(output_dir: Path, summary: JsonObject) -> None:
    text = (
        "# Cue-Bearing Dialect Split\n\n"
        "Round 5 showed that dialect marking somewhere in an utterance does not raise AICC critical-span\n"
        "loss, which points to dialect fragility being local to the dialect tokens themselves. That reading\n"
        "predicts something testable: when the AICC cue word *is* the dialect-marked eojeol, loss should rise.\n\n"
        "Such cases are rare in a random sample, so this split mines the whole label set for them and pairs\n"
        "each with an utterance from the same speaker where the same cue category is carried by a non-dialect\n"
        "eojeol. Speaker, recording, and cue category are fixed inside a pair; only the dialect marking of the\n"
        "cue word differs.\n\n"
        f"**Label status: `{summary['label_status']}`.**\n\n"
        "## Composition\n\n"
        f"- Cue-bearing dialect hits found: {summary['cue_bearing_dialect_hits_found']}\n"
        f"- Non-dialect cue hits available for matching: {summary['non_dialect_cue_hits_found']}\n"
        f"- Pairs built: {summary['pairs_built']}\n"
        f"- Distinct speakers: {summary['distinct_speakers']}, recordings: {summary['distinct_recordings']}\n"
        f"- Cohorts: {json.dumps(summary['cohort_counts'], ensure_ascii=False)}\n"
        f"- Cue categories: {json.dumps(summary['cue_category_counts'], ensure_ascii=False)}\n"
        f"- Clips: {summary['clips']}, {summary['total_clip_minutes']} minutes\n\n"
        f"Matching rule: {summary['matching_rule']}.\n\n"
        "## Limits\n\n"
        "- The cue inventory that survives boundary-safe mining is dominated by confirmation and negation\n"
        "  markers. Amount and intent cues almost never appear on a dialect-marked eojeol in this corpus, so\n"
        "  this split cannot speak for those categories.\n"
        "- Whether a speaker renders a cue in dialect form is not randomly assigned.\n"
        "- Labels are weak and unreviewed.\n\n"
        "Manifests carry transcript text and are local-only.\n"
    )
    (output_dir / "README.md").write_text(text, encoding="utf-8")


def write_outputs(
    manifest_rows: list[JsonObject],
    annotation_rows: list[JsonObject],
    pair_rows: list[JsonObject],
    summary: JsonObject,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "asr_input_manifest.local.jsonl").open("w", encoding="utf-8") as file:
        for row in manifest_rows:
            _ = file.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (output_dir / "cue_annotations.local.jsonl").open("w", encoding="utf-8") as file:
        for row in annotation_rows:
            _ = file.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (output_dir / "pair_manifest.jsonl").open("w", encoding="utf-8") as file:
        for row in pair_rows:
            _ = file.write(json.dumps(row, ensure_ascii=False) + "\n")
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_readme(output_dir, summary)


@app.command()
def main(
    label_root: Annotated[Path, typer.Argument(help="AI-Hub label zip directory.")],
    slice_manifest_path: Annotated[Path, typer.Argument(help="Busan slice manifest jsonl or jsonl.gz.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
    pilot_audio_dir: Annotated[Path, typer.Option("--pilot-audio-dir")] = Path("data/interim/aihub_119_pilot_audio"),
    per_speaker: Annotated[int, typer.Option("--per-speaker", min=1)] = 1,
    max_pairs: Annotated[int, typer.Option("--max-pairs", min=1)] = 250,
    category: Annotated[
        list[str] | None,
        typer.Option("--category", help="Restrict to these cue categories; repeatable."),
    ] = None,
    padding_seconds: Annotated[float, typer.Option("--padding-seconds", min=0.0)] = 0.25,
) -> None:
    if not slice_manifest_path.exists():
        console.print(f"Slice manifest not found: {slice_manifest_path}")
        raise typer.Exit(code=2)
    with zipfile.ZipFile(audio_zip_path()) as archive:
        available = set(audio_members(archive))
    excluded = {path.stem for path in pilot_audio_dir.glob("*.wav")}
    slice_rows = load_manifest(slice_manifest_path)
    slices = {
        f"{text_field(row, 'source_file')}:{text_field(row, 'utterance_id')}": text_field(row, "slice_label")
        for row in slice_rows
    }
    speakers = {text_field(row, "utterance_id"): text_field(row, "speaker_local_id") for row in slice_rows}
    console.print("Scanning label set for cue-bearing dialect eojeols")
    marked, plain = collect(label_root, slices, speakers, available, excluded)
    console.print(f"Found {len(marked)} cue-bearing dialect hits and {len(plain)} non-dialect cue hits")
    wanted = tuple(category) if category else None
    if wanted:
        console.print(f"Restricting to cue categories: {', '.join(wanted)}")
    pairs = pair_hits(marked, plain, per_speaker, wanted)[:max_pairs]
    if not pairs:
        console.print("No pair could be formed.")
        raise typer.Exit(code=1)
    console.print(f"Cutting clips for {len(pairs)} pairs")
    manifest_rows, annotation_rows, pair_rows = cut_and_describe(pairs, label_root, padding_seconds)
    summary = summarize(marked, plain, pairs, manifest_rows)
    write_outputs(manifest_rows, annotation_rows, pair_rows, summary, output_dir)
    console.print(f"Built {len(pairs)} cue pairs into {output_dir}")


if __name__ == "__main__":
    app()
