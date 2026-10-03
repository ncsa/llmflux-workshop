#!/usr/bin/env python3
"""Read an LLMFlux results file and print it as something a human can scan.

Usage:

    python show_results.py results/all.json
    python show_results.py results/all.json --csv results/all.csv

LLMFlux writes one JSON file per job: {"results": [...], "run_metrics": {...}}.
Each result holds the original request ("input"), the model's reply
("output", in OpenAI chat-completion format) or an "error". This script pulls
out the reply text, groups it by task, and checks the answers that have a
right format: a classify answer must be one of the allowed labels, and an
extract answer must be valid JSON with every requested field. Those checks are
the point: an LLM's output is data you have to validate, not an answer you can
trust.
"""

import argparse
import csv
import json
import sys
from pathlib import Path


def reply_text(result: dict) -> str | None:
    """Return the assistant's reply from one result, or None if it failed."""
    try:
        return result["output"]["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None


def parse_json_reply(text: str) -> dict | None:
    """Parse a reply that should be a JSON object.

    Models often wrap JSON in a ```json fence or add a sentence around it, so
    take the outermost {...} span rather than requiring the reply to be pure JSON.
    """
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        value = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def normalize_label(text: str) -> str:
    """Forgive case, surrounding whitespace/quotes, and a trailing period."""
    return text.strip().strip("\"'`*").rstrip(".").strip().casefold()


def summarize(results: list[dict]) -> list[dict]:
    """Flatten raw results into rows of {task, id, reply, ok, error}."""
    rows = []
    for result in results:
        request = result.get("input") or {}
        custom_id = request.get("custom_id", "?")
        metadata = request.get("metadata") or {}
        task, _, item_id = custom_id.partition(":") if ":" in custom_id else ("-", "", custom_id)
        text = reply_text(result)
        row = {"task": task, "id": item_id, "reply": text, "ok": text is not None,
               "error": result.get("error")}
        if text is not None and metadata.get("allowed_labels"):
            allowed = {normalize_label(label) for label in metadata["allowed_labels"]}
            if normalize_label(text) not in allowed:
                row["ok"] = False
                row["error"] = "answer is not one of the allowed labels"
        if text is not None and task == "extract":
            row["parsed"] = parse_json_reply(text)
            if row["parsed"] is None:
                row["ok"] = False
                row["error"] = "reply was not valid JSON"
            else:
                missing = [f for f in metadata.get("expected_fields", []) if f not in row["parsed"]]
                if missing:
                    row["ok"] = False
                    row["error"] = f"JSON is missing {', '.join(missing)}"
        rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("results", type=Path, help="results JSON written by llmflux run")
    parser.add_argument("--csv", type=Path, help="also write the replies to this CSV file")
    parser.add_argument("--width", type=int, default=100, help="truncate replies to this many characters")
    args = parser.parse_args(argv)

    if not args.results.exists():
        print(f"{args.results} does not exist yet. If your job is still running, check "
              "`llmflux jobs` - results are written when the job finishes.", file=sys.stderr)
        return 1
    try:
        data = json.loads(args.results.read_text())
    except json.JSONDecodeError as exc:
        print(f"{args.results} is not valid JSON ({exc}). Is the job still writing it?", file=sys.stderr)
        return 1

    rows = summarize(data.get("results", []))
    if not rows:
        print("No results in this file.")
        return 1

    for task in dict.fromkeys(r["task"] for r in rows):
        print(f"\n=== {task} ===")
        for row in (r for r in rows if r["task"] == task):
            if row["reply"] is None:
                shown = f"FAILED: {row['error']}"
            else:
                shown = " ".join(row["reply"].split())
                if len(shown) > args.width:
                    shown = shown[:args.width - 3] + "..."
                if not row["ok"]:
                    shown = f"[{row['error']}] {shown}"
            print(f"{row['id']:>6}  {shown}")

    failed = [r for r in rows if not r["ok"]]
    print(f"\n{len(rows) - len(failed)}/{len(rows)} replies usable", end="")
    print(f" ({len(failed)} need attention)" if failed else "")

    metrics = data.get("run_metrics") or {}
    if metrics:
        shown = {k: v for k, v in metrics.items() if not isinstance(v, (dict, list))}
        print("Run metrics: " + ", ".join(f"{k}={v}" for k, v in shown.items()))

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["task", "id", "ok", "reply", "error"])
            for row in rows:
                writer.writerow([row["task"], row["id"], row["ok"], row["reply"] or "", row["error"] or ""])
        print(f"Wrote {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
