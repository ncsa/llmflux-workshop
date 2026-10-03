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
    python make_prompts.py --dataset genomics      # the genomics abstracts instead

To try your own task, add an entry to TASKS below - see the workshop guide (README.md), Part 7.
To use your own CSV, pass --input; it needs id, title, and abstract columns
(or change the {placeholders} in the templates to match your columns).
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

# Each dataset is a CSV plus what counts as a valid answer for it: the labels
# the classify task may choose from, and the fields the extract task must
# return. show_results.py checks every answer against these.
DATASETS = {
    "general": {
        "csv": HERE / "data" / "abstracts.csv",
        "labels": ["Earth & Environment", "Life Sciences", "Physical Sciences",
                   "Computing & AI", "Social Sciences", "Agriculture"],
        "fields": {
            "method": "main technique used",
            "data_size": "how much data, with units, or null",
            "key_result": "the headline number or finding",
        },
    },
    "genomics": {
        "csv": HERE / "data" / "genomics_abstracts.csv",
        "labels": ["Clinical & variant genomics", "Single-cell & spatial transcriptomics",
                   "Population & evolutionary genomics", "Epigenomics & gene regulation",
                   "Microbiome & metagenomics", "Plant & animal genomics"],
        "fields": {
            "organism": "species studied, or null",
            "technology": "sequencing or assay technology used",
            "sample_size": "number of samples, cells, or genomes, with units",
            "key_result": "the headline number or finding",
        },
    },
}

# Each task is a system prompt (the model's standing instructions), a prompt
# template filled in from the CSV columns ({title}, {abstract}, ...), and the
# generation settings for that task. Low temperature = more deterministic,
# which is what you want when the output has to be machine-readable.
# <LABELS> and <FIELDS> are filled in from the dataset chosen with --dataset.
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
        "system_prompt": "You label research papers by category. You answer with the label only.",
        "prompt_template": (
            "Which ONE category best fits this paper? Answer with exactly one of: "
            "<LABELS>.\n\n"
            "Title: {title}\nAbstract: {abstract}"
        ),
        "api_parameters": {"temperature": 0.0, "max_tokens": 15},
    },
    "extract": {
        "system_prompt": "You extract structured data from text. You reply with a single JSON object and nothing else.",
        "prompt_template": (
            "Extract these fields from the abstract and reply with JSON only:\n"
            "<FIELDS>\n\n"
            "Title: {title}\nAbstract: {abstract}"
        ),
        "api_parameters": {"temperature": 0.0, "max_tokens": 200},
    },
}


def render_template(template: str, dataset: str) -> str:
    """Fill the dataset-specific <LABELS>/<FIELDS> markers in a task template."""
    spec = DATASETS[dataset]
    fields = ", ".join(f'"{name}": "<{hint}>"' for name, hint in spec["fields"].items())
    # Doubled braces: csv_to_jsonl runs str.format on the template, which
    # turns {{ }} back into the literal braces of the JSON example.
    return (template
            .replace("<LABELS>", ", ".join(spec["labels"]))
            .replace("<FIELDS>", "{{" + fields + "}}"))


def build_task(task: str, input_csv: Path, limit: int | None = None,
               dataset: str = "general") -> list[dict]:
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
            prompt_template=render_template(spec["prompt_template"], dataset),
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
        # Record what a valid answer looks like, so show_results.py can check
        # it later without needing to know which dataset this came from.
        metadata = entry.setdefault("metadata", {})
        metadata["dataset"] = dataset
        if "<LABELS>" in spec["prompt_template"]:
            metadata["allowed_labels"] = DATASETS[dataset]["labels"]
        if "<FIELDS>" in spec["prompt_template"]:
            metadata["expected_fields"] = list(DATASETS[dataset]["fields"])
    return entries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--task", choices=[*TASKS, "all"], default="all")
    parser.add_argument("--dataset", choices=list(DATASETS),
                        default=os.environ.get("WORKSHOP_DATASET") or "general",
                        help="which sample data, labels, and fields to use (default: general)")
    parser.add_argument("--input", type=Path, help="your own CSV instead of the dataset's")
    parser.add_argument("--output", type=Path,
                        help="default: prompts/<task>.jsonl, or prompts/<dataset>-<task>.jsonl")
    parser.add_argument("--limit", type=int, help="only use the first N rows of the CSV")
    args = parser.parse_args(argv)

    # argparse doesn't check a default against choices, and this one can come
    # from the environment.
    if args.dataset not in DATASETS:
        parser.error(f"unknown dataset {args.dataset!r} (from WORKSHOP_DATASET); "
                     f"choose from {', '.join(DATASETS)}")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    args.input = args.input or DATASETS[args.dataset]["csv"]
    if not args.input.exists():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 1

    tasks = list(TASKS) if args.task == "all" else [args.task]
    # Non-default datasets get a prefix so switching datasets doesn't overwrite
    # earlier prompts (or, through submit.sh's naming, earlier results).
    name = args.task if args.dataset == "general" else f"{args.dataset}-{args.task}"
    output = args.output or HERE / "prompts" / f"{name}.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)

    entries = []
    for task in tasks:
        entries.extend(build_task(task, args.input, args.limit, args.dataset))

    with output.open("w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    print(f"Wrote {len(entries)} requests ({', '.join(tasks)}; {args.dataset} dataset) to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
