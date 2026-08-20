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
#      uv run scripts/build_semantic_review_pack.py data/raw/aihub_gyeongsang_119 research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz --output-dir research/experiments/runs/aihub_119_semantic_review_pack
# 3. Or make executable and run:
#      chmod +x scripts/build_semantic_review_pack.py && ./scripts/build_semantic_review_pack.py data/raw/aihub_gyeongsang_119 research/experiments/runs/aihub_119_busan_slice/manifest.jsonl.gz --output-dir research/experiments/runs/aihub_119_semantic_review_pack
# ──────────────────

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from semantic_review_pack import build_pack

app = typer.Typer(add_completion=False)
console = Console()


@app.command()
def main(
    input_path: Annotated[Path, typer.Argument(help="AI-Hub label zip or directory.")],
    manifest_path: Annotated[Path, typer.Argument(help="Busan slice manifest jsonl.gz.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
    samples_per_group: Annotated[int, typer.Option("--samples-per-group")] = 50,
    seed: Annotated[int, typer.Option("--seed")] = 119,
) -> None:
    try:
        build_pack(input_path, manifest_path, output_dir, samples_per_group, seed)
    except RuntimeError as error:
        console.print(str(error))
        raise typer.Exit(code=2) from error
    console.print(f"Wrote {output_dir}")


if __name__ == "__main__":
    app()
