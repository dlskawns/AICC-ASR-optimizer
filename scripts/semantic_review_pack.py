from __future__ import annotations

import hashlib
import json
import random
import re
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TypeAlias, assert_never

from build_dialect_taxonomy import (
    Category,
    JsonValue,
    Pair,
    bool_field,
    classify_pair,
    cohort,
    list_of_mappings,
    manifest_slices,
    pair_hash,
    text_field,
)

CriticalHint: TypeAlias = Literal[
    "negation",
    "amount",
    "date_time",
    "intent_cue",
    "confirmation",
    "other",
]

AMOUNT_RE: Final[re.Pattern[str]] = re.compile(r"[0-9일이삼사오육칠팔구십백천만억]+ ?(?:원|만원|천원|프로|%)")
DATE_TIME_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:오늘|내일|모레|어제|오전|오후|다음 ?주|이번 ?주|[0-9]+월|[0-9]+일|[0-9]+시|[0-9]+분)",
)
NEGATION_CUES: Final[tuple[str, ...]] = ("안", "못", "없", "아니", "불가")
INTENT_CUES: Final[tuple[str, ...]] = (
    "가입",
    "결제",
    "문의",
    "배송",
    "변경",
    "예약",
    "요금",
    "취소",
    "환불",
    "해지",
)
CONFIRMATION_CUES: Final[tuple[str, ...]] = ("네", "예", "맞", "아니", "그렇")


@dataclass(frozen=True, slots=True)
class DialectSpan:
    span_text: str
    standard_text: str
    dialect_category: Category
    semantic_category_hints: tuple[CriticalHint, ...]
    pair_hash: str


@dataclass(frozen=True, slots=True)
class ReviewCandidate:
    review_id: str
    source_file: str
    utterance_id: str
    cohort: str
    slice_label: str
    speaker_region: str
    speaker_age_band: str
    speaker_sex: str
    topic: str
    dialect_transcript: str
    standard_transcript: str
    primary_category: Category
    category_counts: dict[str, int]
    spans: tuple[DialectSpan, ...]


def source_zips(path: Path) -> list[Path]:
    if path.is_file() and path.suffix == ".zip":
        return [path]
    if path.is_dir():
        return sorted(path.rglob("*.zip"))
    return []


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def load_payload(archive: zipfile.ZipFile, name: str) -> dict[str, JsonValue]:
    payload = json.loads(archive.read(name).decode("utf-8"))
    match payload:
        case dict() as mapping:
            return mapping
        case str() | int() | float() | bool() | list() | None:
            msg = f"JSON root is not an object: {name}"
            raise RuntimeError(msg)
        case unreachable:
            assert_never(unreachable)


def semantic_hints(text: str) -> tuple[CriticalHint, ...]:
    hints: list[CriticalHint] = []
    if any(cue in text for cue in NEGATION_CUES):
        hints.append("negation")
    if AMOUNT_RE.search(text) is not None:
        hints.append("amount")
    if DATE_TIME_RE.search(text) is not None:
        hints.append("date_time")
    if any(cue in text for cue in INTENT_CUES):
        hints.append("intent_cue")
    if any(cue in text for cue in CONFIRMATION_CUES):
        hints.append("confirmation")
    if not hints:
        hints.append("other")
    return tuple(dict.fromkeys(hints))


def speaker_region(speaker: dict[str, JsonValue]) -> str:
    current = text_field(speaker, "current_residence")
    if current:
        return current
    principal = text_field(speaker, "principal_residence")
    if principal:
        return principal
    birth = text_field(speaker, "birthplace")
    if birth:
        return birth
    return "unknown"


def dialect_spans(utterance: dict[str, JsonValue]) -> tuple[DialectSpan, ...]:
    spans: list[DialectSpan] = []
    for eojeol in list_of_mappings(utterance.get("eojeolList")):
        if not bool_field(eojeol, "isDialect"):
            continue
        pair = Pair(text_field(eojeol, "standard"), text_field(eojeol, "eojeol"))
        if not pair.standard or not pair.dialect:
            continue
        category = classify_pair(pair)
        spans.append(
            DialectSpan(
                pair.dialect,
                pair.standard,
                category,
                semantic_hints(f"{pair.standard} {pair.dialect}"),
                pair_hash(pair),
            ),
        )
    return tuple(spans)


def primary_category(spans: tuple[DialectSpan, ...]) -> Category:
    counts: Counter[Category] = Counter(span.dialect_category for span in spans)
    return counts.most_common(1)[0][0]


def review_candidate(
    source_file: str,
    metadata: dict[str, JsonValue],
    speaker: dict[str, JsonValue],
    utterance: dict[str, JsonValue],
    slice_label: str,
) -> ReviewCandidate | None:
    spans = dialect_spans(utterance)
    if not spans:
        return None
    candidate_cohort = cohort(slice_label)
    if candidate_cohort == "other":
        return None
    utterance_id = text_field(utterance, "id")
    category = primary_category(spans)
    counts: Counter[str] = Counter(span.dialect_category for span in spans)
    return ReviewCandidate(
        f"semrev-{stable_hash(f'{source_file}:{utterance_id}:{category}')}",
        source_file,
        utterance_id,
        candidate_cohort,
        slice_label,
        speaker_region(speaker),
        text_field(speaker, "age"),
        text_field(speaker, "sex"),
        text_field(metadata, "topic"),
        text_field(utterance, "dialect_form") or text_field(utterance, "form"),
        text_field(utterance, "standard_form"),
        category,
        dict(counts.most_common()),
        spans,
    )


def collect_candidates(zips: list[Path], slices: dict[str, str]) -> list[ReviewCandidate]:
    candidates: list[ReviewCandidate] = []
    for zip_path in zips:
        with zipfile.ZipFile(zip_path) as archive:
            names = sorted(item for item in archive.namelist() if item.endswith(".json"))
            for name in names:
                payload = load_payload(archive, name)
                metadata = payload.get("metadata")
                metadata_map = metadata if isinstance(metadata, dict) else {}
                speakers = {
                    text_field(speaker, "id"): speaker
                    for speaker in list_of_mappings(payload.get("speaker"))
                }
                for utterance in list_of_mappings(payload.get("utterance")):
                    key = f"{name}:{text_field(utterance, 'id')}"
                    speaker = speakers.get(text_field(utterance, "speaker_id"))
                    if speaker is None:
                        continue
                    candidate = review_candidate(
                        name,
                        metadata_map,
                        speaker,
                        utterance,
                        slices.get(key, "other"),
                    )
                    if candidate is not None:
                        candidates.append(candidate)
    return candidates


def choose_samples(
    candidates: list[ReviewCandidate],
    samples_per_group: int,
    seed: int,
) -> tuple[list[ReviewCandidate], dict[str, int]]:
    groups: dict[tuple[str, Category], list[ReviewCandidate]] = {}
    for candidate in candidates:
        groups.setdefault((candidate.cohort, candidate.primary_category), []).append(candidate)
    rng = random.Random(seed)
    selected: list[ReviewCandidate] = []
    pool_counts: dict[str, int] = {}
    for cohort_label, category in sorted(groups):
        pool = sorted(groups[(cohort_label, category)], key=lambda item: item.review_id)
        pool_counts[f"{cohort_label}:{category}"] = len(pool)
        chosen = rng.sample(pool, samples_per_group) if len(pool) > samples_per_group else pool
        selected.extend(sorted(chosen, key=lambda item: item.review_id))
    return selected, pool_counts


def build_pack(
    input_path: Path,
    manifest_path: Path,
    output_dir: Path,
    samples_per_group: int,
    seed: int,
) -> None:
    zips = source_zips(input_path)
    if not zips:
        msg = f"No zip files found under {input_path}"
        raise RuntimeError(msg)
    candidates = collect_candidates(zips, manifest_slices(manifest_path))
    selected, pool_counts = choose_samples(candidates, samples_per_group, seed)
    from semantic_review_outputs import write_outputs

    write_outputs(selected, pool_counts, output_dir, samples_per_group, seed)
