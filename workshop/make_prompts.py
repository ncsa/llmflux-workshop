#!/usr/bin/env python3
"""Turn a CSV of research abstracts into an LLMFlux batch input file (JSONL).

Each row of the CSV becomes one request per task. With the default
``--task all`` you get every task in a single JSONL file, so one GPU job does
all of the work - on a shared reservation that matters, because every job
pays the cost of loading the model onto a GPU once.

Usage (from your workshop directory):

    python make_prompts.py                         # all tasks, all rows
    python make_prompts.py --task extract          # just one task
    python make_prompts.py --limit 3 --task summarize

To try your own task, add an entry to TASKS below - see the workshop guide (README.md), Part 7.
"""

import argparse
import json
import logging
import os
import sys
import tempfile
from pathlib import Path

# Configure logging before importing llmflux: its modules call basicConfig at
# INFO on import, which is a no-op once logging is set up. Participants only
# need the one-line summary this script prints (and any warnings).
logging.basicConfig(level=logging.WARNING)

from llmflux.converters import csv_to_jsonl  # noqa: E402

HERE = Path(__file__).resolve().parent

# Each task is a system prompt (the model's standing instructions), a prompt
# template filled in from the CSV columns ({title}, {abstract}, ...), and the
# generation settings for that task. Low temperature = more deterministic,
# which is what you want when the output has to be machine-readable.
TASKS = {
    "summarize": {
        "system_prompt": "You are a science writer. You explain research clearly to a general audience.",
        "prompt_template": (
            "Summarize this research abstract in two plain-language sentences "
            "that a high-school student could follow.\n\n"
            "Title: {title}\nAbstract: {abstract}"
        ),
        "api_parameters": {"temperature": 0.3, "max_tokens": 150},
    },
    "classify": {
        "system_prompt": "You label research papers by field. You answer with the label only.",
        "prompt_template": (
            "Which ONE field best fits this paper? Answer with exactly one of: "
            "Earth & Environment, Life Sciences, Physical Sciences, "
            "Computing & AI, Social Sciences, Agriculture.\n\n"
            "Title: {title}\nAbstract: {abstract}"
        ),
        "api_parameters": {"temperature": 0.0, "max_tokens": 10},
    },
    "extract": {
        "system_prompt": "You extract structured data from text. You reply with a single JSON object and nothing else.",
        "prompt_template": (
            "Extract these fields from the abstract and reply with JSON only:\n"
            '{{"method": "<main technique used>", '
            '"data_size": "<how much data, with units, or null>", '
            '"key_result": "<the headline number or finding>"}}\n\n'
            "Title: {title}\nAbstract: {abstract}"
        ),
        "api_parameters": {"temperature": 0.0, "max_tokens": 200},
    },
}


def build_task(task: str, input_csv: Path, limit: int | None = None) -> list[dict]:
    """Return the JSONL entries for one task, with custom_ids like ``extract:p01``.

    The ``task:`` prefix keeps ids unique when several tasks share one file,
    and lets show_results.py group the answers back by task.
    """
    spec = TASKS[task]
    pandas_kwargs = {"nrows": limit} if limit else {}

    fd, tmp_path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    try:
        result = csv_to_jsonl(
            input_path=str(input_csv),
            output_path=tmp_path,
            prompt_template=spec["prompt_template"],
            system_prompt=spec["system_prompt"],
            id_column="id",
            api_parameters=spec["api_parameters"],
            # No model here on purpose: LLMFlux fills in the model you pass to
            # `llmflux run --model`. A model name written into the JSONL must
            # match the engine's internal name exactly, or every request fails.
            model=None,
            **pandas_kwargs,
        )
        if not result["success"]:
            raise RuntimeError(f"Could not convert {input_csv}: {result['error']}")
        entries = [json.loads(line) for line in Path(tmp_path).read_text().splitlines() if line.strip()]
    finally:
        os.unlink(tmp_path)

    for entry in entries:
        entry["custom_id"] = f"{task}:{entry['custom_id']}"
        # Drop the null model key entirely so the request body stays clean.
        if entry["body"].get("model") is None:
            entry["body"].pop("model", None)
    return entries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--task", choices=[*TASKS, "all"], default="all")
    parser.add_argument("--input", type=Path, default=HERE / "data" / "abstracts.csv")
    parser.add_argument("--output", type=Path, help="default: prompts/<task>.jsonl")
    parser.add_argument("--limit", type=int, help="only use the first N rows of the CSV")
    args = parser.parse_args(argv)

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if not args.input.exists():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 1

    tasks = list(TASKS) if args.task == "all" else [args.task]
    output = args.output or HERE / "prompts" / f"{args.task}.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)

    entries = []
    for task in tasks:
        entries.extend(build_task(task, args.input, args.limit))

    with output.open("w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    print(f"Wrote {len(entries)} requests ({', '.join(tasks)}) to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
