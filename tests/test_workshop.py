"""Tests for the participant scripts in workshop/.

The workshop scripts are what a room of first-time Delta users runs, so these
tests pin the behavior that would otherwise surface as a confusing failure
live: JSONL that LLMFlux rejects, results that can't be read back, a setup
script that half-configures someone, or a submit command missing a flag.
"""

import csv
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from llmflux.converters import validate_jsonl
from llmflux.io.base import OutputResult

WORKSHOP = Path(__file__).resolve().parents[1] / "workshop"
ABSTRACTS = WORKSHOP / "data" / "abstracts.csv"
GENOMICS = WORKSHOP / "data" / "genomics_abstracts.csv"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"workshop_{name}", WORKSHOP / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


make_prompts = _load("make_prompts")
show_results = _load("show_results")


def _row_count():
    with ABSTRACTS.open(newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def _chat_output(content):
    """The chat-completion dict BatchProcessor stores as a result's output."""
    return {"object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                         "finish_reason": "stop"}]}


class TestSampleData(unittest.TestCase):
    def test_every_dataset_csv_has_unique_ids_and_text(self):
        for name, spec in make_prompts.DATASETS.items():
            with self.subTest(dataset=name), spec["csv"].open(newline="") as f:
                rows = list(csv.DictReader(f))
                self.assertGreater(len(rows), 0)
                ids = [r["id"] for r in rows]
                self.assertEqual(len(ids), len(set(ids)))
                for row in rows:
                    self.assertTrue(row["title"].strip(), row["id"])
                    self.assertTrue(row["abstract"].strip(), row["id"])

    def test_every_dataset_defines_labels_and_fields(self):
        for name, spec in make_prompts.DATASETS.items():
            with self.subTest(dataset=name):
                self.assertGreaterEqual(len(spec["labels"]), 2)
                self.assertEqual(len(spec["labels"]), len(set(spec["labels"])))
                self.assertIn("key_result", spec["fields"])

    def test_setup_copies_every_dataset(self):
        # A dataset that setup_workshop.sh doesn't copy would work in the repo
        # and fail on a participant's copy.
        script = (WORKSHOP / "setup_workshop.sh").read_text()
        for spec in make_prompts.DATASETS.values():
            self.assertIn(f"data/{spec['csv'].name}", script)


class TestBuildTask(unittest.TestCase):
    def test_each_task_makes_one_request_per_row(self):
        for task in make_prompts.TASKS:
            with self.subTest(task=task):
                entries = make_prompts.build_task(task, ABSTRACTS)
                self.assertEqual(len(entries), _row_count())

    def test_custom_ids_are_prefixed_with_task(self):
        entries = make_prompts.build_task("extract", ABSTRACTS)
        self.assertEqual(entries[0]["custom_id"], "extract:p01")

    def test_requests_carry_no_model_name(self):
        # BatchProcessor rejects a JSONL model that differs from the engine's
        # internal name (e.g. the HF repo for vLLM), so leave it out entirely.
        for task in make_prompts.TASKS:
            for entry in make_prompts.build_task(task, ABSTRACTS, limit=2):
                self.assertNotIn("model", entry["body"])

    def test_template_is_filled_from_csv_columns(self):
        entry = make_prompts.build_task("summarize", ABSTRACTS, limit=1)[0]
        system, user = entry["body"]["messages"]
        self.assertEqual(system["role"], "system")
        self.assertEqual(user["role"], "user")
        self.assertIn("Tracking glacier retreat", user["content"])
        self.assertIn("Landsat", user["content"])
        self.assertNotIn("{title}", user["content"])

    def test_extract_template_keeps_literal_json_braces(self):
        user = make_prompts.build_task("extract", ABSTRACTS, limit=1)[0]["body"]["messages"][1]
        self.assertIn('{"method":', user["content"])
        self.assertNotIn("{{", user["content"])

    def test_generation_settings_come_from_task(self):
        body = make_prompts.build_task("classify", ABSTRACTS, limit=1)[0]["body"]
        self.assertEqual(body["temperature"], 0.0)
        self.assertEqual(body["max_tokens"], 15)

    def test_limit_takes_first_rows(self):
        entries = make_prompts.build_task("classify", ABSTRACTS, limit=3)
        self.assertEqual([e["custom_id"] for e in entries],
                         ["classify:p01", "classify:p02", "classify:p03"])

    def test_dataset_fills_labels_and_fields(self):
        classify = make_prompts.build_task("classify", GENOMICS, limit=1, dataset="genomics")[0]
        prompt = classify["body"]["messages"][1]["content"]
        self.assertIn("Microbiome & metagenomics", prompt)
        self.assertNotIn("Social Sciences", prompt)
        self.assertNotIn("<LABELS>", prompt)

        extract = make_prompts.build_task("extract", GENOMICS, limit=1, dataset="genomics")[0]
        prompt = extract["body"]["messages"][1]["content"]
        self.assertIn('{"organism": "<species studied, or null>", "technology":', prompt)
        self.assertNotIn("<FIELDS>", prompt)
        self.assertNotIn('"method"', prompt)

    def test_requests_record_what_a_valid_answer_is(self):
        classify = make_prompts.build_task("classify", GENOMICS, limit=1, dataset="genomics")[0]
        self.assertEqual(classify["metadata"]["allowed_labels"], make_prompts.DATASETS["genomics"]["labels"])
        self.assertEqual(classify["metadata"]["dataset"], "genomics")
        extract = make_prompts.build_task("extract", ABSTRACTS, limit=1)[0]
        self.assertEqual(extract["metadata"]["expected_fields"], ["method", "data_size", "key_result"])
        summary = make_prompts.build_task("summarize", ABSTRACTS, limit=1)[0]
        self.assertNotIn("allowed_labels", summary["metadata"])
        self.assertNotIn("expected_fields", summary["metadata"])

    def test_custom_task_without_markers_is_untouched(self):
        self.assertEqual(make_prompts.render_template("Q: {title}", "genomics"), "Q: {title}")

    def test_unreadable_csv_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.csv"
            bad.write_text("id,title\np01,no abstract column\n")
            # The template references {abstract}; csv_to_jsonl fills missing
            # columns with "" rather than failing, so a missing column still
            # converts. An empty file is a real conversion failure.
            empty = Path(tmp) / "empty.csv"
            empty.write_text("")
            with self.assertRaises(RuntimeError):
                make_prompts.build_task("summarize", empty)


class TestMakePromptsMain(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = make_prompts.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_all_tasks_in_one_valid_file(self):
        output = self.tmp / "all.jsonl"
        code, out, _ = self.run_main("--output", str(output))
        self.assertEqual(code, 0)
        self.assertTrue(validate_jsonl(str(output)))
        entries = [json.loads(line) for line in output.read_text().splitlines()]
        self.assertEqual(len(entries), _row_count() * len(make_prompts.TASKS))
        ids = [e["custom_id"] for e in entries]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn(f"Wrote {len(entries)} requests", out)

    def test_command_line_output_is_just_the_summary(self):
        # Run as participants do; llmflux's INFO logging would bury the one line
        # they need to see.
        output = self.tmp / "all.jsonl"
        result = subprocess.run(
            [sys.executable, str(WORKSHOP / "make_prompts.py"), "--limit", "1", "--output", str(output)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(" - INFO - ", result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), f"Wrote 3 requests (summarize, classify, extract; general dataset) to {output}")

    def test_single_task(self):
        output = self.tmp / "x.jsonl"
        code, _, _ = self.run_main("--task", "extract", "--limit", "2", "--output", str(output))
        self.assertEqual(code, 0)
        ids = [json.loads(line)["custom_id"] for line in output.read_text().splitlines()]
        self.assertEqual(ids, ["extract:p01", "extract:p02"])

    def test_genomics_dataset_gets_its_own_file(self):
        with patch.object(make_prompts, "HERE", self.tmp):
            code, out, _ = self.run_main("--dataset", "genomics", "--task", "classify", "--limit", "2")
        self.assertEqual(code, 0)
        output = self.tmp / "prompts" / "genomics-classify.jsonl"
        ids = [json.loads(line)["custom_id"] for line in output.read_text().splitlines()]
        self.assertEqual(ids, ["classify:g01", "classify:g02"])
        self.assertIn("genomics dataset", out)

    def test_dataset_default_comes_from_workshop_settings(self):
        output = self.tmp / "x.jsonl"
        with patch.dict(os.environ, {"WORKSHOP_DATASET": "genomics"}):
            code, _, _ = self.run_main("--task", "classify", "--limit", "1", "--output", str(output))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.read_text())["custom_id"], "classify:g01")

    def test_unknown_dataset_in_settings_is_rejected(self):
        with patch.dict(os.environ, {"WORKSHOP_DATASET": "chemistry"}), \
                redirect_stderr(io.StringIO()) as err, self.assertRaises(SystemExit) as ctx:
            make_prompts.main(["--limit", "1"])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("chemistry", err.getvalue())

    def test_missing_input_fails_cleanly(self):
        code, _, err = self.run_main("--input", str(self.tmp / "nope.csv"),
                                     "--output", str(self.tmp / "o.jsonl"))
        self.assertEqual(code, 1)
        self.assertIn("not found", err)

    def test_nonpositive_limit_rejected(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
            make_prompts.main(["--limit", "0"])
        self.assertEqual(ctx.exception.code, 2)


class TestParsing(unittest.TestCase):
    def test_reply_text(self):
        self.assertEqual(show_results.reply_text({"output": _chat_output("hi")}), "hi")
        self.assertIsNone(show_results.reply_text({"error": "boom"}))
        self.assertIsNone(show_results.reply_text({"output": None}))
        self.assertIsNone(show_results.reply_text({"output": {"choices": []}}))

    def test_parse_json_reply(self):
        self.assertEqual(show_results.parse_json_reply('{"a": 1}'), {"a": 1})
        self.assertEqual(show_results.parse_json_reply('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(show_results.parse_json_reply('Sure! {"a": {"b": 2}} Hope that helps.'),
                         {"a": {"b": 2}})
        self.assertIsNone(show_results.parse_json_reply("no json here"))
        self.assertIsNone(show_results.parse_json_reply('{"a": 1'))
        self.assertIsNone(show_results.parse_json_reply("} backwards {"))
        self.assertIsNone(show_results.parse_json_reply('{"a": 1} and {"b": 2}'))

    def test_summarize_groups_and_flags(self):
        rows = show_results.summarize([
            {"input": {"custom_id": "classify:p01"}, "output": _chat_output("Life Sciences")},
            {"input": {"custom_id": "extract:p02"}, "output": _chat_output('{"method": "GNN"}')},
            {"input": {"custom_id": "extract:p03"}, "output": _chat_output("I can't do that")},
            {"input": {"custom_id": "summarize:p04"}, "output": None, "error": "timeout"},
            {"input": {"custom_id": "no-prefix"}, "output": _chat_output("ok")},
        ])
        self.assertEqual([(r["task"], r["id"], r["ok"]) for r in rows], [
            ("classify", "p01", True),
            ("extract", "p02", True),
            ("extract", "p03", False),
            ("summarize", "p04", False),
            ("-", "no-prefix", True),
        ])
        self.assertEqual(rows[1]["parsed"], {"method": "GNN"})
        self.assertEqual(rows[2]["error"], "reply was not valid JSON")
        self.assertEqual(rows[3]["error"], "timeout")

    def test_classify_answers_are_checked_against_allowed_labels(self):
        def result(answer):
            return {"input": {"custom_id": "classify:p01",
                              "metadata": {"allowed_labels": ["Life Sciences", "Computing & AI"]}},
                    "output": _chat_output(answer)}
        rows = show_results.summarize([result(a) for a in [
            "Life Sciences", "  life sciences.\n", '"Computing & AI"',
            "Biology", "Life Sciences, because it studies cells",
        ]])
        self.assertEqual([r["ok"] for r in rows], [True, True, True, False, False])
        self.assertEqual(rows[3]["error"], "answer is not one of the allowed labels")

    def test_extract_answers_must_have_every_field(self):
        meta = {"expected_fields": ["organism", "key_result"]}
        rows = show_results.summarize([
            {"input": {"custom_id": "extract:g01", "metadata": meta},
             "output": _chat_output('{"organism": "soybean", "key_result": "17 clusters"}')},
            {"input": {"custom_id": "extract:g02", "metadata": meta},
             "output": _chat_output('{"organism": "cattle"}')},
        ])
        self.assertEqual([r["ok"] for r in rows], [True, False])
        self.assertEqual(rows[1]["error"], "JSON is missing key_result")

    def test_results_without_metadata_skip_the_checks(self):
        rows = show_results.summarize([
            {"input": {"custom_id": "classify:p01"}, "output": _chat_output("Anything at all")},
            {"input": {"custom_id": "extract:p01"}, "output": _chat_output('{"x": 1}')},
        ])
        self.assertEqual([r["ok"] for r in rows], [True, True])


class TestShowResultsMain(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = show_results.main([str(a) for a in argv])
        return code, out.getvalue(), err.getvalue()

    def write_results(self, results, **extra):
        path = self.tmp / "results.json"
        path.write_text(json.dumps({"results": results, **extra}))
        return path

    def test_round_trip_from_real_prompts_and_result_format(self):
        # Prompts from make_prompts, results in the exact shape BatchProcessor
        # saves (OutputResult.to_dict), read back by show_results.
        # The expected fields travel inside the request's metadata, so this
        # also checks they survive into the saved results.
        entries = make_prompts.build_task("extract", ABSTRACTS, limit=3)
        complete = '{"method": "CNN", "data_size": "38 years", "key_result": "71% retreating"}'
        results = [
            OutputResult(input=entries[0], output=_chat_output(complete),
                         metadata={"model": "m"}).to_dict(),
            OutputResult(input=entries[1], output=None, error="CUDA OOM",
                         metadata={"error": True}).to_dict(),
            OutputResult(input=entries[2], output=_chat_output('{"method": "GNN"}'),
                         metadata={"model": "m"}).to_dict(),
        ]
        path = self.write_results(results, run_metrics={"total_requests": 3, "latency": {"p50": 1}})
        csv_path = self.tmp / "out" / "replies.csv"
        code, out, _ = self.run_main(path, "--csv", csv_path)
        self.assertEqual(code, 0)
        self.assertIn("=== extract ===", out)
        self.assertIn('p01  {"method": "CNN", "data_size"', out)
        self.assertIn("p02  FAILED: CUDA OOM", out)
        self.assertIn('p03  [JSON is missing data_size, key_result] {"method": "GNN"}', out)
        self.assertIn("1/3 replies usable (2 need attention)", out)
        self.assertIn("total_requests=3", out)
        self.assertNotIn("latency", out)
        with csv_path.open(newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual([(r["id"], r["ok"]) for r in rows],
                         [("p01", "True"), ("p02", "False"), ("p03", "False")])

    def test_long_replies_are_truncated(self):
        path = self.write_results([{"input": {"custom_id": "summarize:p01"},
                                    "output": _chat_output("word " * 100)}])
        _, out, _ = self.run_main(path, "--width", "20")
        line = next(l for l in out.splitlines() if "p01" in l)
        self.assertTrue(line.endswith("..."))
        self.assertEqual(len(line.split("p01  ", 1)[1]), 20)

    def test_missing_file_explains_job_may_be_running(self):
        code, _, err = self.run_main(self.tmp / "nope.json")
        self.assertEqual(code, 1)
        self.assertIn("llmflux jobs", err)

    def test_partial_file_is_reported_not_crashed(self):
        path = self.tmp / "partial.json"
        path.write_text('{"results": [')
        code, _, err = self.run_main(path)
        self.assertEqual(code, 1)
        self.assertIn("not valid JSON", err)

    def test_empty_results(self):
        code, out, _ = self.run_main(self.write_results([]))
        self.assertEqual(code, 1)
        self.assertIn("No results", out)


FILLED_CONF = """\
WORKSHOP_SYSTEM="delta"
WORKSHOP_ACCOUNT="abcd-delta-gpu"
WORKSHOP_RESERVATION="conf res"
WORKSHOP_PARTITION="gpuA100x4"
WORKSHOP_MODEL="Qwen2.5-7B-Instruct"
WORKSHOP_DATASET="general"
WORKSHOP_TIME="00:20:00"
WORKSHOP_HF_HOME="{hf_home}"
WORKSHOP_CONTAINERS_DIR="{containers}"
WORKSHOP_MODULE=""
WORKSHOP_SAMPLE_RESULTS="{samples}"
"""


class ShellTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.home = self.tmp / "home"
        self.home.mkdir()

    def env(self, **extra):
        # A Delta login node unless a test says otherwise; the real hostname of
        # whatever machine runs the tests must not matter.
        env = {"PATH": os.environ["PATH"], "HOME": str(self.home), "WORKSHOP_HOSTNAME": "dt-login03"}
        env.update(extra)
        return env

    def write_conf(self, text):
        conf = self.tmp / "workshop.conf"
        conf.write_text(text)
        return conf

    def setup_workshop(self, conf, *args, **env):
        return subprocess.run(
            ["bash", str(WORKSHOP / "setup_workshop.sh"), *args],
            env=self.env(WORKSHOP_CONF=str(conf), **env), capture_output=True, text=True,
        )

    def filled(self, **changes):
        """FILLED_CONF with no optional paths, and KEY=value overrides."""
        text = FILLED_CONF.format(hf_home="", samples="", containers="")
        lines = [line for line in text.splitlines()
                 if line.split("=", 1)[0] not in changes]
        lines += [f'{key}="{value}"' for key, value in changes.items()]
        return self.write_conf("\n".join(lines) + "\n")

    def source_env(self, dest, command):
        return subprocess.run(
            ["bash", "-c", f'source "{dest}/workshop.env" && {command}'],
            env=self.env(), capture_output=True, text=True,
        )


class TestSetupWorkshop(ShellTestCase):
    def test_shipped_conf_requires_facilitator_to_fill_it_in(self):
        result = self.setup_workshop(WORKSHOP / "workshop.conf")
        self.assertEqual(result.returncode, 1)
        self.assertIn("isn't configured yet", result.stderr)
        self.assertIn("WORKSHOP_ACCOUNT", result.stderr)
        self.assertFalse((self.home / "llmflux-workshop").exists())

    def test_empty_required_value_is_rejected(self):
        conf = self.write_conf(FILLED_CONF.format(hf_home="", samples="", containers="")
                               .replace('WORKSHOP_ACCOUNT="abcd-delta-gpu"', 'WORKSHOP_ACCOUNT=""'))
        result = self.setup_workshop(conf)
        self.assertEqual(result.returncode, 1)
        self.assertIn("WORKSHOP_ACCOUNT is empty", result.stderr)

    def test_copies_files_and_writes_env(self):
        samples = self.tmp / "samples"
        samples.mkdir()
        (samples / "all.json").write_text('{"results": []}')
        conf = self.write_conf(FILLED_CONF.format(hf_home="/shared/hf cache", samples=samples, containers="/shared/sif"))

        result = self.setup_workshop(conf)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        dest = self.home / "llmflux-workshop"
        for f in ["make_prompts.py", "show_results.py", "submit.sh", "data/abstracts.csv",
                  "data/genomics_abstracts.csv", "sample_results/all.json"]:
            self.assertTrue((dest / f).is_file(), f)
        self.assertTrue((dest / "prompts").is_dir())
        self.assertTrue((dest / "results").is_dir())
        self.assertIn(f"source {dest}/workshop.env", result.stdout)

        sourced = self.source_env(dest, 'printf "%s|" "$WORKSHOP_ACCOUNT" "$WORKSHOP_RESERVATION" '
                                        '"$LLMFLUX_WORKSPACE" "$HF_HOME" "$LLMFLUX_CONTAINERS_DIR" "$PWD"')
        self.assertEqual(sourced.returncode, 0, sourced.stderr)
        self.assertEqual(sourced.stdout.split("|")[:6],
                         ["abcd-delta-gpu", "conf res", str(dest), "/shared/hf cache", "/shared/sif", str(dest)])

    def test_sample_results_dir_without_json_is_fine(self):
        samples = self.tmp / "empty-samples"
        samples.mkdir()
        conf = self.write_conf(FILLED_CONF.format(hf_home="", samples=samples, containers=""))
        result = self.setup_workshop(conf)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list((self.home / "llmflux-workshop" / "sample_results").iterdir()), [])

    def test_empty_hf_home_and_module_are_left_out(self):
        conf = self.write_conf(FILLED_CONF.format(hf_home="", samples="", containers=""))
        self.assertEqual(self.setup_workshop(conf).returncode, 0)
        env_text = (self.home / "llmflux-workshop" / "workshop.env").read_text()
        self.assertNotIn("HF_HOME", env_text)
        self.assertNotIn("LLMFLUX_CONTAINERS_DIR", env_text)
        self.assertNotIn("module load", env_text)

    def test_module_is_loaded_only_when_llmflux_missing(self):
        conf = self.write_conf(FILLED_CONF.format(hf_home="", samples="", containers="")
                               .replace('WORKSHOP_MODULE=""', 'WORKSHOP_MODULE="llmflux"'))
        self.assertEqual(self.setup_workshop(conf).returncode, 0)
        env_text = (self.home / "llmflux-workshop" / "workshop.env").read_text()
        self.assertIn("if ! command -v llmflux", env_text)
        self.assertIn("module load llmflux && conda activate base", env_text)

    def test_containers_dir_overrides_module_default(self):
        # The module may set its own LLMFLUX_CONTAINERS_DIR; the workshop value
        # has to come after the module load to win.
        conf = self.write_conf(FILLED_CONF.format(hf_home="", samples="", containers="/shared/sif")
                               .replace('WORKSHOP_MODULE=""', 'WORKSHOP_MODULE="llmflux"'))
        self.assertEqual(self.setup_workshop(conf).returncode, 0)
        env_text = (self.home / "llmflux-workshop" / "workshop.env").read_text()
        self.assertLess(env_text.index("module load"), env_text.index("LLMFLUX_CONTAINERS_DIR"))

    def test_missing_setting_in_older_conf_is_reported(self):
        conf = self.write_conf("\n".join(line for line in
                               FILLED_CONF.format(hf_home="", samples="", containers="").splitlines()
                               if not line.startswith("WORKSHOP_CONTAINERS_DIR")))
        result = self.setup_workshop(conf)
        self.assertEqual(result.returncode, 1)
        self.assertIn("WORKSHOP_CONTAINERS_DIR", result.stderr)

    def test_custom_destination(self):
        conf = self.write_conf(FILLED_CONF.format(hf_home="", samples="", containers=""))
        dest = self.tmp / "elsewhere"
        self.assertEqual(self.setup_workshop(conf, str(dest)).returncode, 0)
        self.assertTrue((dest / "workshop.env").is_file())
        self.assertFalse((self.home / "llmflux-workshop").exists())

    def test_rerun_keeps_edits_but_refreshes_settings(self):
        conf = self.write_conf(FILLED_CONF.format(hf_home="", samples="", containers=""))
        self.assertEqual(self.setup_workshop(conf).returncode, 0)
        dest = self.home / "llmflux-workshop"
        (dest / "make_prompts.py").write_text("# my edits\n")

        conf.write_text(FILLED_CONF.format(hf_home="", samples="", containers="")
                        .replace("conf res", "new-res"))
        rerun = self.setup_workshop(conf)
        self.assertEqual(rerun.returncode, 0, rerun.stderr)
        self.assertEqual(rerun.stderr, "")
        self.assertEqual((dest / "make_prompts.py").read_text(), "# my edits\n")
        self.assertIn("new-res", (dest / "workshop.env").read_text())


class TestSystemChecks(ShellTestCase):
    def test_deltaai_conf_on_deltaai_login(self):
        conf = self.filled(WORKSHOP_SYSTEM="deltaai", WORKSHOP_PARTITION="ghx4",
                           WORKSHOP_ACCOUNT="abcd-dtai-gh", WORKSHOP_DATASET="genomics")
        result = self.setup_workshop(conf, WORKSHOP_HOSTNAME="gh-login02")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        env_text = (self.home / "llmflux-workshop" / "workshop.env").read_text()
        self.assertIn("export WORKSHOP_SYSTEM=deltaai", env_text)
        self.assertIn("export WORKSHOP_DATASET=genomics", env_text)

    def test_logged_in_to_the_wrong_system(self):
        cases = [
            ("delta", "gpuA100x4", "abcd-delta-gpu", "gh-login02", "DeltaAI"),
            ("delta", "gpuA100x4", "abcd-delta-gpu", "gh012", "DeltaAI"),
            ("deltaai", "ghx4", "abcd-dtai-gh", "dt-login03.delta.ncsa.illinois.edu", "dtai-login"),
            ("deltaai", "ghx4", "abcd-dtai-gh", "gpua052", "dtai-login"),
        ]
        for system, partition, account, host, hint in cases:
            with self.subTest(system=system, host=host):
                conf = self.filled(WORKSHOP_SYSTEM=system, WORKSHOP_PARTITION=partition,
                                   WORKSHOP_ACCOUNT=account)
                result = self.setup_workshop(conf, WORKSHOP_HOSTNAME=host)
                self.assertEqual(result.returncode, 1)
                self.assertIn("but you're logged in to", result.stderr)
                self.assertIn(hint, result.stderr)
                self.assertFalse((self.home / "llmflux-workshop").exists())

    def test_unrecognized_host_is_allowed(self):
        # e.g. a laptop during a facilitator's local check, or a node naming
        # scheme we don't know about: don't block on a guess.
        result = self.setup_workshop(self.filled(), WORKSHOP_HOSTNAME="my-laptop")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_partition_must_match_system(self):
        for system, partition, account in [("delta", "ghx4", "abcd-delta-gpu"),
                                           ("deltaai", "gpuA100x4", "abcd-dtai-gh")]:
            with self.subTest(system=system):
                conf = self.filled(WORKSHOP_SYSTEM=system, WORKSHOP_PARTITION=partition,
                                   WORKSHOP_ACCOUNT=account)
                result = self.setup_workshop(conf, WORKSHOP_HOSTNAME="my-laptop")
                self.assertEqual(result.returncode, 1)
                self.assertIn(f"WORKSHOP_PARTITION={partition}", result.stderr)

    def test_account_from_the_other_system_only_warns(self):
        conf = self.filled(WORKSHOP_ACCOUNT="abcd-dtai-gh")
        result = self.setup_workshop(conf)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("doesn't look like a Delta account", result.stderr)

    def test_invalid_system_and_dataset(self):
        result = self.setup_workshop(self.filled(WORKSHOP_SYSTEM="delta-ai"))
        self.assertEqual(result.returncode, 1)
        self.assertIn('must be "delta" or "deltaai"', result.stderr)
        result = self.setup_workshop(self.filled(WORKSHOP_DATASET="chemistry"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("WORKSHOP_DATASET must be", result.stderr)


class TestSubmit(ShellTestCase):
    def setUp(self):
        super().setUp()
        # Stand-in for the real CLI: record the arguments it was called with.
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        fake = self.bin / "llmflux"
        fake.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$FAKE_ARGS"\necho "Job ID: 123"\n')
        fake.chmod(0o755)
        self.args_file = self.tmp / "args.txt"
        self.workspace = self.tmp / "ws"
        (self.workspace / "prompts").mkdir(parents=True)
        (self.workspace / "prompts" / "all.jsonl").write_text("{}\n")

    def submit(self, *args, **env):
        base = {"PATH": f"{self.bin}:{os.environ['PATH']}", "FAKE_ARGS": str(self.args_file),
                "WORKSHOP_SYSTEM": "delta", "WORKSHOP_HOSTNAME": "dt-login03",
                "WORKSHOP_ACCOUNT": "abcd-delta-gpu", "WORKSHOP_RESERVATION": "confres",
                "WORKSHOP_PARTITION": "gpuA100x4", "WORKSHOP_MODEL": "Qwen2.5-7B-Instruct",
                "WORKSHOP_TIME": "00:20:00", "LLMFLUX_WORKSPACE": str(self.workspace)}
        base.update(env)
        base = {k: v for k, v in base.items() if v is not None}
        return subprocess.run(["bash", str(WORKSHOP / "submit.sh"), *args], cwd=self.workspace,
                              env=base, capture_output=True, text=True)

    def recorded_args(self):
        return self.args_file.read_text().splitlines()

    def test_passes_every_setting_as_a_flag(self):
        result = self.submit("prompts/all.jsonl")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded_args(), [
            "run", "--model", "Qwen2.5-7B-Instruct", "--input", "prompts/all.jsonl",
            "--output", f"{self.workspace}/results/all.json",
            "--account", "abcd-delta-gpu", "--partition", "gpuA100x4", "--time", "00:20:00",
            "--sbatch-arg", "reservation=confres",
        ])
        self.assertIn("Running:\n  llmflux run --model", result.stdout)
        self.assertIn("Job ID: 123", result.stdout)

    def test_no_reservation_flag_when_unset(self):
        result = self.submit("prompts/all.jsonl", WORKSHOP_RESERVATION="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("--sbatch-arg", self.recorded_args())

    def test_settings_not_loaded(self):
        result = self.submit("prompts/all.jsonl", WORKSHOP_ACCOUNT=None)
        self.assertEqual(result.returncode, 1)
        self.assertIn("source ~/llmflux-workshop/workshop.env", result.stderr)
        self.assertFalse(self.args_file.exists())

    def test_missing_prompts_file(self):
        result = self.submit("prompts/nope.jsonl")
        self.assertEqual(result.returncode, 1)
        self.assertIn("make_prompts.py", result.stderr)

    def test_wrong_system_is_caught_before_submitting(self):
        result = self.submit("prompts/all.jsonl", WORKSHOP_HOSTNAME="gh-login01")
        self.assertEqual(result.returncode, 1)
        self.assertIn("logged in to DeltaAI", result.stderr)
        self.assertFalse(self.args_file.exists())

    def test_usage(self):
        self.assertEqual(self.submit().returncode, 2)


if __name__ == "__main__":
    unittest.main()
