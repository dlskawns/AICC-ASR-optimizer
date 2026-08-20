#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "numpy",
#     "torch",
#     "transformers",
# ]
# ///

# ─── How to run ───
# 1. Reuse the existing whisper_proto environment, which already has torch and transformers:
#      ../japko/whisper_proto/.venv/bin/python scripts/run_wav2vec2_korean_pilot_asr.py research/experiments/runs/aihub_119_dialect_attribution_probe/asr_input_manifest.local.jsonl research/experiments/runs/aihub_119_dialect_attribution_probe/wav2vec2_korean.local.jsonl
# 2. Or run with uv:
#      uv run scripts/run_wav2vec2_korean_pilot_asr.py INPUT_MANIFEST.local.jsonl OUTPUT_ASR.local.jsonl [MODEL_ID]
# ──────────────────

"""Transcribe the pilot clips with a Korean-specialised wav2vec2 model.

The pilot so far is Whisper-only, which makes any dialect claim a claim about one model family. This
runner adds a non-Whisper, Korean-trained baseline so the dialect gap can be checked across
architectures. The model is loaded with `local_files_only=True`, so this script never starts a
download; cache the model first with `huggingface_hub.snapshot_download`.

Clips are expected at 16 kHz mono, which is what the pilot clip cutter already produces.
"""

from __future__ import annotations

import json
import sys
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypeAlias, assert_never

import numpy as np
import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]

DEFAULT_MODEL: Final[str] = "kresnik/wav2vec2-large-xlsr-korean"
EXPECTED_RATE: Final[int] = 16000
INT16_FULL_SCALE: Final[float] = 32768.0

USAGE: Final[str] = (
    "Usage: run_wav2vec2_korean_pilot_asr.py "
    "INPUT_MANIFEST.local.jsonl OUTPUT_ASR.local.jsonl [MODEL_ID]\n\n"
    f"Default MODEL_ID is '{DEFAULT_MODEL}'. The model is loaded with local_files_only=True, "
    "so this script never starts a model download."
)


@dataclass(frozen=True, slots=True)
class CliArgs:
    manifest_path: Path
    output_path: Path
    model_id: str


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
    return CliArgs(Path(argv[1]), Path(argv[2]), argv[3] if len(argv) == 4 else DEFAULT_MODEL)


def read_waveform(clip_path: Path) -> np.ndarray:
    """Read a 16 kHz mono PCM clip as float32 in [-1, 1]."""
    with wave.open(str(clip_path), "rb") as source:
        if source.getframerate() != EXPECTED_RATE:
            msg = f"Expected {EXPECTED_RATE} Hz, got {source.getframerate()}: {clip_path}"
            raise RuntimeError(msg)
        if source.getsampwidth() != 2:
            msg = f"Expected 16-bit PCM: {clip_path}"
            raise RuntimeError(msg)
        frames = source.readframes(source.getnframes())
        channels = source.getnchannels()
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / INT16_FULL_SCALE
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples


def transcribe_row(
    processor: Wav2Vec2Processor,
    model: Wav2Vec2ForCTC,
    row: JsonObject,
    model_id: str,
) -> JsonObject:
    clip_path = Path(text_field(row, "clip_path"))
    if not clip_path.exists():
        msg = f"Clip not found: {clip_path}"
        raise RuntimeError(msg)
    started_at = time.monotonic()
    inputs = processor(read_waveform(clip_path), sampling_rate=EXPECTED_RATE, return_tensors="pt", padding=True)
    with torch.no_grad():
        logits = model(inputs.input_values).logits
    hypothesis = processor.batch_decode(torch.argmax(logits, dim=-1))[0]
    return {
        "review_id": text_field(row, "review_id"),
        "utterance_id": text_field(row, "utterance_id"),
        "model": f"wav2vec2:{model_id.split('/')[-1]}",
        "clip_path": str(clip_path),
        "hypothesis": hypothesis.strip(),
        "asr_seconds": round(time.monotonic() - started_at, 3),
    }


def run(args: CliArgs) -> None:
    if not args.manifest_path.exists():
        print(f"Input manifest not found: {args.manifest_path}", file=sys.stderr)
        raise SystemExit(2)
    try:
        processor = Wav2Vec2Processor.from_pretrained(args.model_id, local_files_only=True)
        model = Wav2Vec2ForCTC.from_pretrained(args.model_id, local_files_only=True)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Model is not available locally: {args.model_id}", file=sys.stderr)
        print(str(exc).splitlines()[0], file=sys.stderr)
        raise SystemExit(3) from exc
    _ = model.eval()

    rows = load_manifest(args.manifest_path)
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    with args.output_path.open("w", encoding="utf-8") as file:
        for index, row in enumerate(rows, start=1):
            output = transcribe_row(processor, model, row, args.model_id)
            _ = file.write(json.dumps(output, ensure_ascii=False) + "\n")
            print(f"{index}/{len(rows)} {output['review_id']} {output['asr_seconds']}s")
    print(f"Wrote {len(rows)} ASR outputs: {args.output_path}")


def main() -> None:
    run(parse_args(sys.argv))


if __name__ == "__main__":
    main()
