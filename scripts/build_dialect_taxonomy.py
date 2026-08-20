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
#      uv run scripts/build_dialect_taxonomy.py data/raw/aihub_gyeongsang_119 research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz --output-dir research/experiments/runs/aihub_119_dialect_taxonomy
# 3. Or make executable and run:
#      chmod +x scripts/build_dialect_taxonomy.py && ./scripts/build_dialect_taxonomy.py data/raw/aihub_gyeongsang_119 research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz --output-dir research/experiments/runs/aihub_119_dialect_taxonomy
# ──────────────────

from __future__ import annotations

import gzip
import hashlib
import json
import zipfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated, Final, Literal, TypeAlias, assert_never

import numpy as np
import typer
from rich.console import Console

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
Category: TypeAlias = Literal["same_surface", "vowel_shift", "coda_shift", "ending_or_particle_variant", "prefix_or_stem_variant", "contraction_or_expansion", "lexical_replacement"]

HANGUL_BASE: Final[int] = 0xAC00
HANGUL_END: Final[int] = 0xD7A3
NCOUNT: Final[int] = 588
TCOUNT: Final[int] = 28
BUSAN_SLICES: Final[frozenset[str]] = frozenset(("busan_strict", "busan_residence", "busan_any"))
console = Console()
app = typer.Typer(add_completion=False)


@dataclass(frozen=True, slots=True)
class Pair:
    standard: str
    dialect: str


@dataclass(frozen=True, slots=True)
class PatternKey:
    cohort: str
    slice_label: str
    category: Category
    signature: str
    pair_hash: str


@dataclass(frozen=True, slots=True)
class Taxonomy:
    pattern_counts: Counter[PatternKey]
    category_counts: Counter[str]
    slice_counts: Counter[str]
    cohort_counts: Counter[str]


def text_field(mapping: dict[str, JsonValue], key: str) -> str:
    match mapping.get(key):
        case str() as value:
            return value.strip()
        case int() | float() | bool() | list() | dict() | None:
            return ""
        case unreachable:
            assert_never(unreachable)


def bool_field(mapping: dict[str, JsonValue], key: str) -> bool:
    match mapping.get(key):
        case bool() as value:
            return value
        case str() | int() | float() | list() | dict() | None:
            return False
        case unreachable:
            assert_never(unreachable)


def list_of_mappings(value: JsonValue) -> list[dict[str, JsonValue]]:
    match value:
        case list() as items:
            mappings: list[dict[str, JsonValue]] = []
            for item in items:
                match item:
                    case dict() as mapping:
                        mappings.append(mapping)
                    case str() | int() | float() | bool() | list() | None:
                        continue
                    case unreachable:
                        assert_never(unreachable)
            return mappings
        case str() | int() | float() | bool() | dict() | None:
            return []
        case unreachable:
            assert_never(unreachable)


def manifest_slices(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    with gzip.open(path, "rt", encoding="utf-8") as file:
        for line in file:
            row = json.loads(line)
            match row:
                case dict() as fields:
                    key = f"{text_field(fields, 'source_file')}:{text_field(fields, 'utterance_id')}"
                    mapping[key] = text_field(fields, "slice_label")
                case str() | int() | float() | bool() | list() | None:
                    continue
                case unreachable:
                    assert_never(unreachable)
    return mapping


def hangul_parts(char: str) -> tuple[int, int, int] | None:
    codepoint = ord(char)
    if codepoint < HANGUL_BASE or codepoint > HANGUL_END:
        return None
    index = codepoint - HANGUL_BASE
    return index // NCOUNT, (index % NCOUNT) // TCOUNT, index % TCOUNT


def common_prefix_len(left: str, right: str) -> int:
    count = 0
    for left_char, right_char in zip(left, right, strict=False):
        if left_char != right_char:
            break
        count += 1
    return count


def common_suffix_len(left: str, right: str) -> int:
    reversed_left = left[::-1]
    reversed_right = right[::-1]
    return common_prefix_len(reversed_left, reversed_right)


def syllable_shift_category(pair: Pair) -> Category | None:
    if len(pair.standard) != len(pair.dialect):
        return None
    vowel_only = False
    coda_only = False
    for standard_char, dialect_char in zip(pair.standard, pair.dialect, strict=True):
        standard_parts = hangul_parts(standard_char)
        dialect_parts = hangul_parts(dialect_char)
        match (standard_parts, dialect_parts):
            case ((s_initial, s_vowel, s_coda), (d_initial, d_vowel, d_coda)):
                if s_initial == d_initial and s_coda == d_coda and s_vowel != d_vowel:
                    vowel_only = True
                    continue
                if s_initial == d_initial and s_vowel == d_vowel and s_coda != d_coda:
                    coda_only = True
                    continue
                if standard_char != dialect_char:
                    return None
            case (None, None):
                if standard_char != dialect_char:
                    return None
            case (tuple(), None) | (None, tuple()):
                return None
            case unreachable:
                assert_never(unreachable)
    if vowel_only and not coda_only:
        return "vowel_shift"
    if coda_only and not vowel_only:
        return "coda_shift"
    return None


def classify_pair(pair: Pair) -> Category:
    if pair.standard == pair.dialect:
        return "same_surface"
    syllable_category = syllable_shift_category(pair)
    if syllable_category is not None:
        return syllable_category
    prefix = common_prefix_len(pair.standard, pair.dialect)
    suffix = common_suffix_len(pair.standard[prefix:], pair.dialect[prefix:])
    standard_tail = len(pair.standard) - prefix - suffix
    dialect_tail = len(pair.dialect) - prefix - suffix
    if prefix >= 1 and standard_tail <= 4 and dialect_tail <= 4:
        return "ending_or_particle_variant"
    if suffix >= 1 and standard_tail <= 4 and dialect_tail <= 4:
        return "prefix_or_stem_variant"
    if pair.standard in pair.dialect or pair.dialect in pair.standard:
        return "contraction_or_expansion"
    return "lexical_replacement"


def signature(pair: Pair) -> str:
    prefix = common_prefix_len(pair.standard, pair.dialect)
    suffix = common_suffix_len(pair.standard[prefix:], pair.dialect[prefix:])
    standard_tail = len(pair.standard) - prefix - suffix
    dialect_tail = len(pair.dialect) - prefix - suffix
    return f"p{prefix}:s{suffix}:std{standard_tail}:dia{dialect_tail}"


def pair_hash(pair: Pair) -> str:
    payload = f"{pair.standard}\t{pair.dialect}".encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def cohort(slice_label: str) -> str:
    if slice_label in BUSAN_SLICES:
        return "busan"
    if slice_label == "gyeongsang_other":
        return "gyeongsang_other"
    return "other"


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


def build_taxonomy(zips: list[Path], slices: dict[str, str]) -> Taxonomy:
    taxonomy = Taxonomy(Counter(), Counter(), Counter(), Counter())
    for zip_path in zips:
        with zipfile.ZipFile(zip_path) as archive:
            for name in sorted(item for item in archive.namelist() if item.endswith(".json")):
                payload = load_payload(archive, name)
                for utterance in list_of_mappings(payload.get("utterance")):
                    key = f"{name}:{text_field(utterance, 'id')}"
                    slice_label = slices.get(key, "other")
                    for eojeol in list_of_mappings(utterance.get("eojeolList")):
                        if not bool_field(eojeol, "isDialect"):
                            continue
                        pair = Pair(text_field(eojeol, "standard"), text_field(eojeol, "eojeol"))
                        category = classify_pair(pair)
                        pattern = PatternKey(
                            cohort(slice_label),
                            slice_label,
                            category,
                            signature(pair),
                            pair_hash(pair),
                        )
                        taxonomy.pattern_counts[pattern] += 1
                        taxonomy.category_counts[f"{pattern.cohort}:{category}"] += 1
                        taxonomy.slice_counts[f"{slice_label}:{category}"] += 1
                        taxonomy.cohort_counts[pattern.cohort] += 1
    return taxonomy


def write_outputs(taxonomy: Taxonomy, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with gzip.open(output_dir / "pattern_counts.jsonl.gz", "wt", encoding="utf-8") as file:
        for pattern, count in taxonomy.pattern_counts.most_common():
            row = asdict(pattern)
            row["count"] = count
            _ = file.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary: dict[str, JsonValue] = {
        "cohort_counts": dict(taxonomy.cohort_counts.most_common()),
        "category_counts": dict(taxonomy.category_counts.most_common()),
        "slice_counts": dict(taxonomy.slice_counts.most_common()),
        "unique_pattern_count": len(taxonomy.pattern_counts),
        "numpy_version": np.__version__,
    }
    _ = (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(summary, output_dir / "summary.md")


def write_markdown(summary: dict[str, JsonValue], output_path: Path) -> None:
    category_counts = summary["category_counts"]
    cohort_counts = summary["cohort_counts"]
    match (category_counts, cohort_counts):
        case (dict() as categories, dict() as cohorts):
            lines = ["# Dialect Error Taxonomy", "", "## Cohort Counts", ""]
            lines.extend(f"- `{key}`: {value}" for key, value in cohorts.items())
            lines.extend(("", "## Category Counts", ""))
            lines.extend(f"- `{key}`: {value}" for key, value in categories.items())
            lines.extend(("", "Patterns are hashed and do not include raw utterance text."))
            output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        case _:
            msg = "summary has an invalid shape"
            raise RuntimeError(msg)


@app.command()
def main(
    input_path: Annotated[Path, typer.Argument(help="AI-Hub label zip or directory.")],
    manifest_path: Annotated[Path, typer.Argument(help="Busan slice manifest jsonl.gz.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
) -> None:
    zips = [input_path] if input_path.is_file() and input_path.suffix == ".zip" else sorted(input_path.rglob("*.zip"))
    if not zips:
        console.print(f"No zip files found under {input_path}")
        raise typer.Exit(code=2)
    taxonomy = build_taxonomy(zips, manifest_slices(manifest_path))
    write_outputs(taxonomy, output_dir)
    console.print(f"Wrote {output_dir}")


if __name__ == "__main__":
    app()
