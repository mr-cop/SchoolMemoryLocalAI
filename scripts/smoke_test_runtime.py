#!/usr/bin/env python3
"""Optional MLX load/generation smoke test using synthetic generic text."""

from __future__ import annotations

import argparse
import multiprocessing
from pathlib import Path


def run_model(model_path: str, queue: multiprocessing.Queue) -> None:
    from mlx_lm import generate, load
    model, tokenizer = load(model_path)
    result = generate(model, tokenizer, prompt="Write one short sentence about a circle.", max_tokens=16, verbose=False)
    queue.put(bool(isinstance(result, str) and result.strip()))


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("model_directory", type=Path); parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args(); directory = args.model_directory.resolve()
    for name in ("model.safetensors", "config.json", "tokenizer.json", "tokenizer_config.json"):
        if not (directory / name).is_file(): print(f"ERROR: missing {name}"); return 1
    queue: multiprocessing.Queue = multiprocessing.Queue(); process = multiprocessing.Process(target=run_model, args=(str(directory), queue)); process.start(); process.join(args.timeout)
    if process.is_alive(): process.terminate(); process.join(); print("ERROR: inference timed out and was cancelled"); return 1
    if process.exitcode != 0 or queue.empty() or not queue.get(): print("ERROR: model did not generate non-empty text"); return 1
    print("MLX runtime smoke test passed."); return 0


if __name__ == "__main__": raise SystemExit(main())
