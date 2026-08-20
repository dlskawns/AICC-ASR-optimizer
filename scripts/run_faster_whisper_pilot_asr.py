#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "faster-whisper==1.2.1",
#     "numpy",
# ]
# ///

# ─── How to run ───
# 1. Install uv (if not installed):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Reuse the existing whisper_proto environment without installing packages:
#      ../japko/whisper_proto/.venv/bin/python scripts/run_faster_whisper_pilot_asr.py research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl research/experiments/runs/aihub_119_dialect_attribution_probe/faster_whisper_medium.local.jsonl
# 3. Or run directly with uv:
#      uv run scripts/run_faster_whisper_pilot_asr.py INPUT_MANIFEST.local.jsonl OUTPUT_ASR.local.jsonl [MODEL_OR_PATH]
# ──────────────────

from __future__ import annotations

import json
import sys
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypeAlias, assert_never

from faster_whisper import WhisperModel
from faster_whisper.transcribe import Segment
from huggingface_hub.errors import LocalEntryNotFoundError

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]

USAGE: Final[str] = (
    "Usage: run_faster_whisper_pilot_asr.py "
    "INPUT_MANIFEST.local.jsonl OUTPUT_ASR.local.jsonl [MODEL_OR_PATH]\n\n"
    "Default MODEL_OR_PATH is 'medium'. The model is loaded with local_files_only=True, "
    "so this script never starts a model download."
)


@dataclass(frozen=True, slots=True)
class CliArgs:
    manifest_path: Path
    output_path: Path
    model_size_or_path: str


def text_field(mapping: JsonObject, key: str) -> str:
    match mapping.get(key):
        case str() as value:
            return value.strip()
        case int() | float() | bool() | list() | dict() | None:
            return ""
        case unreachable:
            assert_never(unreachable)


def parse_json_object(line: str) -> JsonObject:
    payload = json.loads(line)
    match payload:
        case dict() as mapping:
            return mapping
        case str() | int() | float() | bool() | list() | None:
            msg = "JSONL row root must be an object"
            raise RuntimeError(msg)
        case unreachable:
            assert_never(unreachable)


def load_manifest(path: Path) -> list[JsonObject]:
    return [parse_json_object(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_args(argv: list[str]) -> CliArgs:
    if len(argv) == 2 and argv[1] in {"-h", "--help"}:
        print(USAGE)
        raise SystemExit(0)
    if len(argv) < 3 or len(argv) > 4:
        print(USAGE, file=sys.stderr)
        raise SystemExit(2)
    return CliArgs(
        manifest_path=Path(argv[1]),
        output_path=Path(argv[2]),
        model_size_or_path=argv[3] if len(argv) == 4 else "medium",
    )


def joined_text(segments: Iterable[Segment]) -> str:
    return " ".join(segment.text.strip() for segment in segments if segment.text.strip())


def transcribe_row(model: WhisperModel, row: JsonObject, model_name: str) -> JsonObject:
    clip_path = Path(text_field(row, "clip_path"))
    if not clip_path.exists():
        msg = f"Clip not found: {clip_path}"
        raise RuntimeError(msg)
    started_at = time.monotonic()
    segments, _info = model.transcribe(str(clip_path), language="ko", beam_size=5, vad_filter=True)
    return {
        "review_id": text_field(row, "review_id"),
        "utterance_id": text_field(row, "utterance_id"),
        "model": f"faster-whisper:{model_name}",
        "clip_path": str(clip_path),
        "hypothesis": joined_text(segments),
        "asr_seconds": round(time.monotonic() - started_at, 3),
    }


def run(args: CliArgs) -> None:
    if not args.manifest_path.exists():
        print(f"Input manifest not found: {args.manifest_path}", file=sys.stderr)
        raise SystemExit(2)
    try:
        model = WhisperModel(
            args.model_size_or_path,
            device="auto",
            compute_type="int8",
            local_files_only=True,
        )
    except (LocalEntryNotFoundError, OSError, RuntimeError, ValueError) as exc:
        print(f"Model is not available locally: {args.model_size_or_path}", file=sys.stderr)
        print(str(exc).splitlines()[0], file=sys.stderr)
        raise SystemExit(3) from exc

    rows = load_manifest(args.manifest_path)
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    with args.output_path.open("w", encoding="utf-8") as file:
        for index, row in enumerate(rows, start=1):
            output = transcribe_row(model, row, args.model_size_or_path)
            file.write(json.dumps(output, ensure_ascii=False) + "\n")
            print(f"{index}/{len(rows)} {output['review_id']} {output['asr_seconds']}s")
    print(f"Wrote {len(rows)} ASR outputs: {args.output_path}")


def main() -> None:
    run(parse_args(sys.argv))


if __name__ == "__main__":
    main()
