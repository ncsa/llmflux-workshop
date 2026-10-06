# Hands-on: running an LLM over your research data on NCSA Delta

> **Keep this page open** in a browser tab next to your terminal. You'll copy
> commands from it as you go.
>
> *Running or presenting this workshop?* See [`facilitator/`](facilitator/) for
> setup, prep, and the day-of plan, and [`presenter/`](presenter/) for the talk
> and the live demos.

In this session you'll take a small dataset — 16 research abstracts — and have a
large language model (LLM) summarize, classify, and pull structured facts out of
every one of them, running on a GPU on NCSA's **Delta** supercomputer. Then you'll
change the task to something of your own and run it again.

You don't need to have used a supercomputer before, and you don't need to install
anything. Everything you need is already on the cluster. Copy each command exactly as
shown; the text around it explains what it does and why, so you can do this again
on your own later.

**What you'll come away with:**

- How to log in to a cluster and tell where you are on it
- What a batch job is, and why you send work to a queue instead of running it directly
- How to turn a spreadsheet of data into a set of LLM requests
- How to run those requests on a GPU with **LLMFlux**, and read the results
- Where batch jobs fit next to chat assistants, model services, and AI agents

> **Stuck?** Raise your hand, or check [Troubleshooting](#troubleshooting) at the
> bottom. Nothing in this exercise can damage your account or anyone else's work.

---

## The big picture

```
 Your laptop                 Delta
 ───────────    ssh     ┌──────────────┐  llmflux run   ┌──────────────┐
 terminal or  ────────▶ │  LOGIN NODE  │ ─────────────▶ │    SLURM     │
 web browser            │ (you type    │   (submits a   │ (the queue)  │
                        │  here)       │    job)        └──────┬───────┘
                        └──────▲───────┘                       │ when a GPU is free
                               │                               ▼
                               │  results/all.json      ┌──────────────┐
                               └─────────────────────── │ COMPUTE NODE │
                                  (shared filesystem)   │   4 GPUs     │
                                                        │ runs the LLM │
                                                        └──────────────┘
```

You'll type everything on the **login node**. It's shared by everyone logged in to
Delta, so it's only for light work: editing files, preparing inputs, submitting
jobs. The actual LLM runs on a **compute node** with GPUs, which you never log in
to directly. Instead you describe the work you want done and hand it to **Slurm**,
the scheduler that decides whose work runs where and when. LLMFlux writes that
job description for you.

Because the login and compute nodes share the same files, results written on the
compute node show up in your directory on the login node.

### Words you'll see

| Term | What it means here |
| --- | --- |
| **Node** | One computer in the cluster. Delta has hundreds. |
| **Login node** | The computer you land on when you connect. Shared by everyone — don't run heavy work here. |
| **Compute node** | A computer that runs jobs. Ours have 4 NVIDIA GPUs each. |
| **Slurm** | The job scheduler. You submit a job; Slurm queues it and runs it when the resources are free. |
| **Job** | One unit of work submitted to Slurm, with a job ID number. |
| **Partition** | A group of similar nodes, e.g. `gpuA100x4` on Delta or `ghx4` on DeltaAI. |
| **Account / allocation** | Who pays for the GPU time. Yours has been set up for this workshop. |
| **Reservation** | Nodes set aside just for this workshop, so we don't wait behind everyone else on the cluster. |
| **Module** | A way of loading preinstalled software: `module load llmflux`. |
| **LLM** | Large language model — the kind of model behind ChatGPT. We'll use Qwen2.5-7B-Instruct, an open model. |
| **Batch inference** | Sending many prompts to a model in one job, rather than chatting with it one message at a time. |
| **JSONL** | A text file with one JSON object per line. LLMFlux's input format: one line = one request to the model. |

---

## Part 1 — Log in (≈5 min)

NCSA runs two GPU clusters that work almost identically for this exercise:
**Delta** (NVIDIA A100 and A40 GPUs) and **DeltaAI** (NVIDIA GH200 "Grace Hopper"
GPUs). **Your facilitator will tell you which one we're using.** Use that column
of this table for everything below:

| | Delta | DeltaAI |
| --- | --- | --- |
| SSH address | `login.delta.ncsa.illinois.edu` | `dtai-login.delta.ncsa.illinois.edu` |
| Open OnDemand | <https://openondemand.delta.ncsa.illinois.edu/> | <https://gh-ondemand.delta.ncsa.illinois.edu/> |
| Shell menu item | **>_Delta Shell Access** | **>_DeltaAI Shell Access** |
| Login node names start with | `dt-login` | `gh-login` |

You'll need your own laptop (no laptop? Share with the person next to you), your
NCSA username, your password, and the **NCSA Duo** app on your phone. If you
haven't set those up yet, tell a facilitator now; this is the one step that
can't be fixed quickly during the session.

**If you've already logged in at this workshop** (for example in an earlier
session), do it the same way. Open OnDemand (option B) is the easiest.

**Option A — a terminal (Mac, Linux, or Windows PowerShell):**

```bash
ssh YOUR_USERNAME@SSH_ADDRESS_FROM_THE_TABLE
```

Type `yes` if it asks whether to trust the host (first time only). Enter your
**NCSA** password, then complete Duo: type `1` and approve the push on your
phone, or type a passcode from the Duo app. The password prompt won't show
anything as you type. That's normal.

**Option B — your web browser (no terminal needed; easiest on Windows).**

1. Go to the Open OnDemand address from the table and log in through CILogon
   with your **NCSA** username, password, and Duo.
2. In the **Clusters** menu, choose the shell menu item from the table.
3. A terminal opens in a new tab and asks for your NCSA password **again**. Type
   it (nothing will show), press Enter, then do the Duo step as in option A.

You get the same terminal as option A, in a browser tab. The **Files** menu at
the top of the dashboard is a handy way to view and upload files later.

Once you're in, check where you are:

```bash
hostname      # which computer you're on, e.g. dt-login03... or gh-login02...
whoami        # your username
pwd           # your current directory: your home directory, /u/YOUR_USERNAME
```

`hostname` should say `login`. That tells you you're on a login node, which is
where you should be. Check it starts with the right name from the table, too:
the setup in Part 2 will stop you if you're on the wrong cluster.

---

## Part 2 — Set up your workshop folder (≈5 min)

Your facilitator will show a **shared workshop folder** path on screen. Run the
setup script inside it, putting that path in place of `/SHARED/FOLDER`:

```bash
bash /SHARED/FOLDER/workshop/setup_workshop.sh
```

(For example, at the October 2026 NCSA workshop it was
`bash /projects/bccu/llmflux-workshop/workshop/setup_workshop.sh`.)

This creates `~/llmflux-workshop` (the `~` means your home directory) with the
exercise files in it, plus a settings file called `workshop.env`. Now load the
settings:

```bash
source ~/llmflux-workshop/workshop.env
```

`source` runs the file's commands in your current shell. Here it loads the
`llmflux` software (`module load llmflux`), fills in the workshop's account and
reservation names, and moves you into the workshop folder. **Run this again every
time you log in.** Settings don't carry over between logins.

Check that it worked:

```bash
pwd                      # should end in /llmflux-workshop
llmflux --version        # prints a version number
ls                       # data/  make_prompts.py  prompts/  results/  show_results.py  submit.sh ...
```

If `llmflux: command not found` appears, see [Troubleshooting](#troubleshooting).

---

## Part 3 — Look at the data and build the prompts (≈10 min)

Start by looking at the data:

```bash
head -3 data/abstracts.csv
```

It's a normal CSV spreadsheet with an `id`, a `title`, and an `abstract` column.
(These abstracts are made up for this workshop, but they look like real ones.)

There are two sample datasets. Use the one your facilitator says, or whichever
is closer to your own research:

| Dataset | File | What's in it |
| --- | --- | --- |
| `general` (the default) | `data/abstracts.csv` | 16 abstracts across disciplines: climate, materials, neuroscience, agriculture, computing, ... |
| `genomics` | `data/genomics_abstracts.csv` | 16 genomics abstracts: variant calling, single-cell, metagenomics, epigenomics, crop and livestock genomes, ... |

We want the model to do three jobs for every abstract:

| Task | What we ask | Why it's interesting |
| --- | --- | --- |
| `summarize` | Two plain-language sentences | Free-form text, so there's no single right answer |
| `classify` | Pick one category from a fixed list (research fields, or kinds of genomics study) | Does the model stay inside the list? |
| `extract` | Return specific facts as JSON (e.g. `method`, `data_size`, `key_result`; for genomics, `organism`, `technology`, `sample_size`, `key_result`) | The output has to be machine-readable for the next step in a pipeline |

`make_prompts.py` turns each row × each task into one request:

```bash
python make_prompts.py
```

```
Wrote 48 requests (summarize, classify, extract; general dataset) to .../prompts/all.jsonl
```

For the genomics abstracts, add `--dataset genomics`. The file is then called
`prompts/genomics-all.jsonl`; use that name in the commands below, and
`results/genomics-all.json` for the results. (If your facilitator made genomics
the default for this session, plain `python make_prompts.py` already uses it,
and the output line says so.)

That's 16 abstracts × 3 tasks = 48 requests, all in one file. Look at one request,
pretty-printed:

```bash
head -1 prompts/all.jsonl | python -m json.tool
```

Every line follows the same format OpenAI's batch API uses (so tools built for
that format work with it too):

- `custom_id`: our label for this request (`summarize:p01`), so each answer can be matched back to its question
- `body.messages`: the conversation, made up of a **system** message (the model's standing instructions, e.g. "You are a science writer…") and a **user** message (the actual question, with this abstract filled in)
- `body.temperature`: how random the output is. It's `0` for classify and extract, because we want the same answer every time, and a bit higher for summaries.
- `body.max_tokens`: a cap on how long the answer can be

Open `make_prompts.py` (`nano make_prompts.py`, or **Files → Home Directory**
in Open OnDemand, then the file's **Edit** button) and find `TASKS` near the top. Each task is just a system prompt, a
template with `{title}` and `{abstract}` placeholders, and those generation
settings. You'll add your own task in Part 7.

> **Why one file instead of three?** Each GPU job spends its first minute or two
> loading the model onto the GPU. Answering 48 questions after that takes only
> seconds. One job with everything in it pays that loading cost once, and it keeps
> the queue moving for everyone else in the room.

---

## Part 4 — Submit the job (≈5 min)

```bash
bash submit.sh prompts/all.jsonl
```

`submit.sh` prints the full command before it runs it:

```
Running:
  llmflux run --model Qwen2.5-7B-Instruct --input prompts/all.jsonl \
    --output .../results/all.json --account XXXX-delta-gpu --partition gpuA40x4 \
    --time 00:20:00

Job ID: 1234567
```

Here's what each part of that command does:

| Flag | Meaning |
| --- | --- |
| `--model` | Which LLM to run. `llmflux show-models` lists all the options. |
| `--input` / `--output` | Your requests, and where to write the answers |
| `--account` | Which allocation pays for the GPU time |
| `--partition` | Which group of nodes to use (on Delta, `gpuA40x4` has nodes with 4 NVIDIA A40 GPUs and `gpuA100x4` 4 A100s; `ghx4` on DeltaAI has 4 GH200s) |
| `--time` | The longest the job may run. Slurm stops it after that. Ask for a bit more than you need. |
| `--sbatch-arg reservation=…` | Use the nodes set aside for a workshop. Only there if the workshop names its reservation; some reservations are picked up automatically from the account instead. |

**Write down your job ID.** You'll use it in the next part.

What just happened: LLMFlux wrote a Slurm job script and handed it to Slurm.
`llmflux run` gives you your prompt back immediately; the job runs on its own.
When it's your turn, Slurm will:

1. give your job one GPU on a compute node
2. start a container with the vLLM inference engine (a container is a packaged software environment, so it runs the same everywhere)
3. load the model's weights onto the GPU
4. send the 48 requests to the model, one after another
5. write `results/all.json` and release the GPU

You can log out at this point and the job keeps going. That's the advantage of
batch jobs: they don't need you to stay connected.

---

## Part 5 — Watch it run (≈5–15 min, depending on the queue)

```bash
llmflux jobs                    # your LLMFlux jobs and their state
squeue -u $USER                 # the same thing, straight from Slurm
```

A job goes **PENDING → RUNNING → COMPLETED**. While it's PENDING, the last column of
`squeue` shows why it's waiting:

| Reason | Meaning |
| --- | --- |
| `(Resources)` | Every reserved GPU is busy with someone else's job. You're in line, and it'll start soon. |
| `(Priority)` | Other jobs are ahead of you in line. |
| `(Reservation)` | The reservation hasn't started yet. Tell a facilitator. |

Once it's RUNNING, follow its log live:

```bash
llmflux logs JOB_ID -f
```

You'll see the container start, then vLLM loading the model, then requests being
processed. Press **Ctrl-C** to stop watching. That only stops the log display;
the job keeps running.

```bash
llmflux status JOB_ID           # detailed status for one job
```

**While you wait:** if your facilitator set up sample results, there's a finished
example in `sample_results/`. Skip ahead to Part 6 and try the commands on that
file, then come back for your own.

---

## Part 6 — Read the results (≈10 min)

When `llmflux jobs` shows COMPLETED (or `ls results/` shows `all.json`):

```bash
python show_results.py results/all.json
```

You'll see something like this (your model's wording will differ):

```
=== summarize ===
   p01  Scientists used decades of satellite photos and AI to track Greenland's glaciers...
   ...
=== classify ===
   p01  Earth & Environment
   ...
=== extract ===
   p01  {"method": "convolutional segmentation model", "data_size": "38 years of Landsat imagery...
   ...
48/48 replies usable
```

Everything is also in `results/all.json` in full. To get a spreadsheet you can
open in Excel:

```bash
python show_results.py results/all.json --csv results/all.csv
```

**Look closely.** These are the questions you'd ask in real research:

1. **Classify:** `show_results.py` flags any answer that isn't exactly one of the six allowed labels (it forgives capitalization and a trailing period). Did the model ever reword a label or add a sentence? Do you agree with its choices?
2. **Extract:** `show_results.py` flags any reply that isn't valid JSON or is missing a requested field. Did any fail? The script can't check the harder question: are the extracted numbers really in the abstract, or did the model invent any (this is called hallucination)? Check a few by hand.
3. **Summarize:** are the summaries accurate? Would a high-school student follow them?

What you're seeing is that **an LLM's output is data that needs checking, not a
finished answer**. The same applies to everything an AI agent produces. At 16
abstracts you can check by eye. At 16,000 you'd need checks like the JSON one
built into the pipeline.

---

## Part 7 — Make it yours (≈20 min)

Choose one or more:

**A. Add a new task.** Open `make_prompts.py` and add an entry to `TASKS`. For example:

```python
    "questions": {
        "system_prompt": "You are a thoughtful peer reviewer.",
        "prompt_template": (
            "Write the single most important question a skeptical reviewer would ask "
            "about this study.\n\nTitle: {title}\nAbstract: {abstract}"
        ),
        "api_parameters": {"temperature": 0.7, "max_tokens": 80},
    },
```

Then run just that task:

```bash
python make_prompts.py --task questions
bash submit.sh prompts/questions.jsonl
# ...wait for it to finish...
python show_results.py results/questions.json
```

Other ideas: translate each summary into another language; rate each study's
"real-world impact" from 1 to 5 and explain why; list the limitations the authors
don't mention.

**B. Use an AI assistant to write the task for you.** Open the chat assistant from
the demo (Illinois Chat). Paste one of the existing `TASKS` entries and ask
something like: *"Write another entry in this same format that asks the model to
identify which of the UN Sustainable Development Goals each study contributes to,
and return the answer as JSON."* Paste its answer into `make_prompts.py`, check
that it makes sense, then run it. This is the same loop that AI agents run: an
assistant writes the code, and you review it and send it to the cluster.

**C. Use your own data.** Copy any CSV onto Delta, for example with
`scp mydata.csv YOUR_USERNAME@SSH_ADDRESS:~/llmflux-workshop/data/`
from your laptop, or with the Open OnDemand file browser's upload button. The
CSV needs an `id` column, and the `{placeholders}` in your template must match
its column names:

```bash
python make_prompts.py --input data/mydata.csv --task questions --limit 20
```

Use `--limit` while you're experimenting so you don't spend GPU time on a huge
file before the prompt is right.

**D. Try a different model.** `llmflux show-models` lists everything LLMFlux knows
how to run. Bigger models are often better, but they're slower to load and some
need more than one GPU, so ask a facilitator before you try one here. Part 10
shows how to run `llmflux run` yourself with a different `--model`.

---

## Part 8 — Deployment strategies: where batch fits

There are three common ways to use an LLM on campus, and research work often
uses more than one:

- **A hosted assistant** (Illinois Chat): chat with a model grounded in your documents.
- **A model service** (LLMHub, or `llmflux serve`): a model running on cluster GPUs that you can chat with, or call from your own code through an OpenAI-compatible API.
- **Batch jobs** (LLMFlux, what you just did): run the same prompt over a whole dataset, then give the GPU back.

A model service is also what **AI agents** run on. An agent is an LLM in a loop
with tools: it decides on an action (run this code, search for that, read that
file), sees the result, and decides what to do next. Coding agents that write and
run scripts for you work this way.

Interactive use and batch solve different problems:

| | Chat, agent, or model service | Batch (what you just did) |
| --- | --- | --- |
| Shape of the work | One open-ended task, many steps that depend on each other | The same well-defined step, thousands of times |
| Who's in the loop | You, steering as it goes | You, checking the results afterwards |
| Where it runs | A hosted service, or a model server | A GPU job in the queue that releases the GPU when it finishes |
| Example | "Help me write the analysis script" | "Run that analysis prompt on all 50,000 documents" |

A common pattern is to use an agent or assistant to **design and debug** the step
on a handful of examples (what you did in Part 7B), then hand it to a batch job to
**run at scale**.

LLMFlux can also run a model service. `llmflux serve` starts a model as a
long-running service on a compute node and gives you an address and an API key.
Any tool that speaks the OpenAI API, including many agent frameworks and coding
agents, can then use a model running on *your* allocation instead of a commercial
API. Part 11 walks through it.

**What about fine-tuning?** LLMFlux runs models; it doesn't train them. Before
fine-tuning, try better prompts (with a few worked examples), grounding in your
documents, or a more specialized model. If you do fine-tune, LLMFlux can run your
fine-tuned model in batch through a custom model config (see "Custom Model
Configuration" in the LLMFlux docs).

---

## Going further: LLMFlux on its own

Parts 3–7 used three helper scripts: `make_prompts.py` wrote the requests,
`submit.sh` ran `llmflux run` for you, and `show_results.py` read the answers.
For your own research you'll usually skip the helpers and use LLMFlux directly.
Parts 9–12 show how: what goes in a request file, how to call `llmflux run`
yourself, how to keep a model running as a service, and the rest of the
`llmflux` commands.

These parts describe **LLMFlux 2.0.0** (`llmflux --version`). The examples use
`$WORKSHOP_ACCOUNT` and `$WORKSHOP_PARTITION`, which `workshop.env` sets for you.
Outside the workshop, put your own account (`accounts` lists them) and partition
in their place.

---

## Part 9 — What's in a request file

A request file is **JSONL**: one JSON object per line, one line per request.
The lines are long, so pretty-print one to read it:

```bash
head -1 prompts/all.jsonl | python -m json.tool
```

```json
{
    "custom_id": "summarize:p01",
    "method": "POST",
    "url": "/v1/chat/completions",
    "body": {
        "messages": [
            {"role": "system", "content": "You are a science writer. ..."},
            {"role": "user", "content": "Summarize this research abstract ...\n\nTitle: ...\nAbstract: ..."}
        ],
        "temperature": 0.3,
        "max_tokens": 150
    },
    "metadata": {"csv_row": {"id": "p01", "...": "..."}, "dataset": "general"}
}
```

### The top-level keys

| Key | Required? | What LLMFlux does with it |
| --- | --- | --- |
| `custom_id` | No (a random ID if missing) | Nothing except copy it to the output. It's **your** name for the request, so you can match each answer to its input. Make it unique. |
| `body` | Yes | The request itself. See below. |
| `url` | No (default `/v1/chat/completions`) | Picks the kind of request: `/v1/chat/completions` reads `body.messages` (a conversation); `/v1/completions` reads `body.prompt`, which LLMFlux sends as a single user message. Any other value fails that request. |
| `method` | No (default `POST`) | Only recorded in the output. Leave it as `POST`. |
| `metadata` | No | Not read at all. Copied into that request's result, so it's the place for anything you want to carry through to the analysis: the source row, a sample ID, a file name. |

### Inside `body`

| Key | What it does | What to put |
| --- | --- | --- |
| `messages` | The conversation the model replies to. A list of `{"role": ..., "content": ...}`. | Usually two: a **`system`** message (who the model should be, and rules like "answer only with JSON") and a **`user`** message (the task plus the data for this item). |
| `prompt` | A single piece of text, for `/v1/completions` only. | Rarely needed; use `messages`. |
| `temperature` | Randomness. `0` gives the same answer every time; higher values vary more. | `0` for classifying and extracting; `0.3`–`0.7` for writing. |
| `max_tokens` | The longest reply allowed, in tokens (a token is roughly ¾ of a word). | Enough for a full answer. Too low cuts replies off mid-sentence, which also breaks JSON. |
| `top_p` | Another randomness control. | Leave it out. |
| `stop` | A list of strings; the model stops when it writes one. | Leave it out unless you need it. |
| `model` | Must exactly match the engine's internal model name (e.g. `Qwen/Qwen2.5-7B-Instruct`), or the request fails. | **Leave it out.** LLMFlux fills it in from `--model`. |

Settings you leave out come from the model's defaults in LLMFlux. **Any other key
in `body` is ignored in LLMFlux 2.0.0** ([issue #154](https://github.com/Center-for-AI-Innovation/LLMFlux/issues/154)). That includes `response_format` (the
"JSON mode" some APIs have), `seed`, and `tools`. Also, every result says
`"finish_reason": "stop"`, even when `max_tokens` cut the reply off, so check for
truncated answers yourself. To get JSON, ask for it in the
prompt, then check what comes back, as `show_results.py` does.

### What you'd change for your own work

- **The `user` message**: the instructions, and the data for this one item.
  That's the only part that changes from line to line.
- **The `system` message**: the role and the rules. Usually the same on every line.
- **`temperature` and `max_tokens`**, to suit the task.
- **`custom_id`**: one unique ID per item, ideally the ID your data already has.

### Writing a request file yourself

Don't build JSON by hand: quotes and line breaks inside your data will break it.
Let Python write it. Save this as `my_prompts.py` in `~/llmflux-workshop`, then
`python my_prompts.py`:

```python
import csv
import json

with open("data/abstracts.csv") as f, open("prompts/organisms.jsonl", "w") as out:
    for row in csv.DictReader(f):
        request = {
            "custom_id": row["id"],
            "body": {
                "messages": [
                    {"role": "system", "content": "You are a careful research assistant. Answer only with what the text says."},
                    {"role": "user", "content": "Which organisms, if any, does this study use? "
                                                "Answer with a comma-separated list, or 'none'.\n\n" + row["abstract"]},
                ],
                "temperature": 0,
                "max_tokens": 60,
            },
            "metadata": {"title": row["title"]},
        }
        out.write(json.dumps(request) + "\n")
```

### What comes back

The output file is one JSON object. `results` has one entry per request, in the
same order as the input file:

```json
{
  "results": [
    {
      "input":    { ...your request, exactly as you wrote it... },
      "output":   { "choices": [ { "message": { "content": "THE MODEL'S REPLY" } } ], "usage": {...} },
      "metadata": { "model": "...", "request_latency_ms": 412.5, "retry_count": 0, ...your metadata... }
    }
  ],
  "run_metrics": { "elapsed_sec": 21.4, ... }
}
```

A request that failed after its retries has `"output": null` and an `"error"`
message instead. To read the replies in your own script:

```python
import json

data = json.load(open("results/organisms.json"))
for result in data["results"]:
    item = result["input"].get("custom_id")
    if result.get("output"):
        print(item, "->", result["output"]["choices"][0]["message"]["content"])
    else:
        print(item, "-> FAILED:", result.get("error"))
```

---

## Part 10 — Running `llmflux run` yourself

`submit.sh` only fills in the options for you. Here is the same job, typed out:

```bash
llmflux run --model Qwen2.5-7B-Instruct \
    --input prompts/all.jsonl --output results/all-direct.json \
    --account $WORKSHOP_ACCOUNT --partition $WORKSHOP_PARTITION --time 00:20:00
```

Only `--model` and `--input` are required, but set the others every time:
without `--account` Slurm may reject the job, the default partition (`a100`)
doesn't exist on Delta, and without `--output` the results land in
`data/output/results_<timestamp>.json`.

### Examples

**Run the file you wrote in Part 9:**

```bash
llmflux run --model Qwen2.5-7B-Instruct \
    --input prompts/organisms.jsonl --output results/organisms.json \
    --account $WORKSHOP_ACCOUNT --partition $WORKSHOP_PARTITION --time 00:20:00
```

**A bigger model on one GPU.** Qwen2.5-14B-Instruct has twice the parameters.
The first run of any model downloads its weights (about 30 GB here) before it
starts, so give it more time:

```bash
llmflux run --model Qwen2.5-14B-Instruct \
    --input prompts/all.jsonl --output results/all-14b.json \
    --account $WORKSHOP_ACCOUNT --partition $WORKSHOP_PARTITION --time 01:00:00
```

**A model too big for one GPU.** At full precision a model needs about 2 GB of
GPU memory per billion parameters, plus working room. A 32B model needs about
65 GB, so split it across GPUs with `--gpus-per-node` (vLLM then runs it with
tensor parallelism):

```bash
llmflux run --model Qwen2.5-32B-Instruct --gpus-per-node 2 \
    --input prompts/all.jsonl --output results/all-32b.json \
    --account $WORKSHOP_ACCOUNT --partition $WORKSHOP_PARTITION --time 01:30:00
```

Two of Delta's A40s (48 GB each) are enough for this. Its A100s have 40 GB each,
so on an A100 partition use `--gpus-per-node 4`. Every extra GPU is charged to
the allocation, so in a workshop, ask a facilitator first.

**Gated models** (Llama, Gemma, MedGemma). Their makers require you to accept a
license on HuggingFace first. Accept it on the model's HuggingFace page, create
an access token in your HuggingFace settings, then:

```bash
export HF_TOKEN=hf_your_token_here     # this login only; don't put it in shared files
llmflux run --model Llama-3.1-8B-Instruct \
    --input prompts/all.jsonl --output results/all-llama.json \
    --account $WORKSHOP_ACCOUNT --partition $WORKSHOP_PARTITION --time 01:00:00
```

**Long documents.** vLLM limits how long one request can be (its context
length). To change that or other vLLM settings, pass them as a **JSON object**:

```bash
llmflux run --model Qwen2.5-7B-Instruct \
    --vllm-engine-args '{"max-model-len": 32768}' \
    --input prompts/long.jsonl --output results/long.json \
    --account $WORKSHOP_ACCOUNT --partition $WORKSHOP_PARTITION --time 01:00:00
```

The single quotes matter. A plain string like `"--max-model-len 32768"` is not
valid JSON: LLMFlux prints an `Invalid JSON` warning when you submit, then runs
the job without those settings ([issue #153](https://github.com/Center-for-AI-Innovation/LLMFlux/issues/153)).

**Get an email when the job ends, or use a reservation.** `--sbatch-arg KEY=VALUE`
adds any Slurm option to the job; repeat it for more than one:

```bash
llmflux run --model Qwen2.5-7B-Instruct \
    --input prompts/all.jsonl --output results/all-mail.json \
    --account $WORKSHOP_ACCOUNT --partition $WORKSHOP_PARTITION --time 00:20:00 \
    --sbatch-arg mail-type=END,FAIL --sbatch-arg mail-user=you@illinois.edu \
    --sbatch-arg reservation=RESERVATION_NAME
```

**A large file.** LLMFlux sends requests to the model one after another ([issue #152](https://github.com/Center-for-AI-Innovation/LLMFlux/issues/152)), saves
partial results to the output file every 100 requests, and tries a failed
request up to 3 more times. The main thing to set is `--time`:

```bash
llmflux run --model Qwen2.5-7B-Instruct \
    --input prompts/big.jsonl --output results/big.json \
    --account $WORKSHOP_ACCOUNT --partition $WORKSHOP_PARTITION --time 04:00:00
```

Estimate `--time` from a small test first (`make_prompts.py --limit`, or the
first few lines of your file): the Part 6 run took about 0.5 seconds per request,
plus about 2 minutes to start. Longer prompts and replies take longer.

**See the job script LLMFlux writes.** `--debug` keeps it as `job.sh` in
`~/llmflux-workshop`. Reading it is a good way to learn what a GPU job needs:

```bash
llmflux run --debug --model Qwen2.5-7B-Instruct \
    --input prompts/all.jsonl --output results/all-debug.json \
    --account $WORKSHOP_ACCOUNT --partition $WORKSHOP_PARTITION --time 00:20:00
less ~/llmflux-workshop/job.sh
```

**Shorter commands.** LLMFlux reads its Slurm defaults from these variables:

```bash
export SLURM_ACCOUNT=$WORKSHOP_ACCOUNT SLURM_PARTITION=$WORKSHOP_PARTITION SLURM_TIME=00:20:00
llmflux run --model Qwen2.5-7B-Instruct --input prompts/all.jsonl --output results/all-short.json
```

They last until you log out. Add the `export` line to `~/.bashrc` to keep them.

### All `llmflux run` options

| Option | Default | What it does |
| --- | --- | --- |
| `--model` | *(required)* | Model key from `llmflux show-models` |
| `--input` | *(required)* | Your JSONL request file |
| `--output` | `data/output/results_<time>.json` | Where to write the results |
| `--account` | `$SLURM_ACCOUNT` | Allocation to charge |
| `--partition` | `$SLURM_PARTITION`, else `a100` | Which nodes |
| `--time` | `$SLURM_TIME`, else `00:30:00` | Longest the job may run |
| `--gpus-per-node` | `1` | GPUs; more than one splits the model across them |
| `--nodes` | `1` | Nodes; more than one splits a very large model across nodes |
| `--mem`, `--cpus-per-task` | `32G`, `4` | Memory and CPU cores for the job |
| `--sbatch-arg KEY=VALUE` | | Any other Slurm option, repeatable |
| `--batch-size`, `--save-frequency`, `--max-retries`, `--retry-delay` | `4`, `50`, `3`, `1.0` s | Grouping, partial saves, and retries. **Accepted but ignored in LLMFlux 2.0.0** ([issue #144](https://github.com/Center-for-AI-Innovation/llmflux/issues/144)): the defaults always apply. |
| `--vllm-engine-args` | | Extra vLLM settings, as a JSON object |
| `--custom-config-path` | | A model not in the list, e.g. one you fine-tuned (vLLM only) |
| `--engine` | `vllm` | `vllm` or `ollama` |
| `--debug` | | Keep the generated `job.sh` |
| `--rebuild` | | Rebuild the container image (rarely needed) |
| `--temperature`, `--max-tokens`, `--top-p`, `--top-k` | | **Accepted but ignored in LLMFlux 2.0.0** (issue #144). Set these per request in `body` (Part 9). |

---

## Part 11 — A model as a service: `llmflux serve`

A batch job loads the model, answers a file, and stops. `llmflux serve` starts a
model and **keeps it running** for as long as you ask, so you can send it
requests whenever you like: from a script, a notebook, or any tool that works
with the OpenAI API, including many agent frameworks. It uses a GPU for the whole
time, busy or not, so ask for as long as you need and cancel it when you're done.

**1. Start it.** `--email` is required: Slurm emails you when the job starts.

```bash
llmflux serve --model Qwen2.5-7B-Instruct --email you@illinois.edu \
    --account $WORKSHOP_ACCOUNT --partition $WORKSHOP_PARTITION --time 01:00:00
```

```
Serve job submitted: 1234567
...
You will receive an email at you@illinois.edu when the service is ready.
Then run: llmflux connect 1234567
```

**2. Get the address.** Once the job is RUNNING (the email, or `llmflux jobs`):

```bash
llmflux connect 1234567
```

It waits for the model to finish loading (up to 10 minutes), then prints
everything you need:

```
Service is ready.

  Endpoint:  http://gpub004.delta.ncsa.illinois.edu:8000/v1
  API Key:   (a long random string)
  Model:     Qwen/Qwen2.5-7B-Instruct
  Engine:    vllm
```

Your endpoint and key will be different. Copy them into variables:

```bash
export LLM_URL=http://...                      # the Endpoint line
export LLM_KEY=...                             # the API Key line
export LLM_MODEL=Qwen/Qwen2.5-7B-Instruct      # the Model line
```

**3. Talk to it from the login node with `curl`:**

```bash
curl -s $LLM_URL/models -H "Authorization: Bearer $LLM_KEY"     # is it up? what model?

curl -s $LLM_URL/chat/completions \
    -H "Authorization: Bearer $LLM_KEY" -H "Content-Type: application/json" \
    -d '{"model": "'"$LLM_MODEL"'", "max_tokens": 100,
         "messages": [{"role": "user", "content": "Explain a Slurm reservation in one sentence."}]}' \
    | python -m json.tool
```

**4. Or from Python**, with the standard OpenAI client. If
`python -c "import openai"` fails, run `pip install --user openai` first.

```python
import os
from openai import OpenAI

client = OpenAI(base_url=os.environ["LLM_URL"], api_key=os.environ["LLM_KEY"])
reply = client.chat.completions.create(
    model=os.environ["LLM_MODEL"],
    messages=[{"role": "user", "content": "Suggest three titles for a talk on batch LLM inference."}],
    max_tokens=150,
)
print(reply.choices[0].message.content)
```

This is the same code you'd write for a commercial API; only `base_url` and
`api_key` differ. Many tools read those two from the environment, so this is
often all it takes to point them at your model:

```bash
export OPENAI_BASE_URL=$LLM_URL OPENAI_API_KEY=$LLM_KEY
```

**From your laptop.** The endpoint is only reachable inside the cluster. To use it
from your own machine, open an SSH tunnel through the login node. Replace
`NODE` and `PORT` with the node name and port from the Endpoint line
(`http://NODE:PORT/v1`), and leave that terminal open:

```bash
ssh -N -L 8000:NODE:PORT YOUR_USERNAME@login.delta.ncsa.illinois.edu
```

Then use `http://localhost:8000/v1` as the endpoint on your laptop. If
`llmflux connect` says the node is *unreachable*, it prints a similar tunnel
command to run on the login node.

**5. Stop it** when you're done, so the GPU is released:

```bash
llmflux cancel 1234567
```

Anyone who has both the endpoint and the key can use your model on your
allocation, so don't post them anywhere public.

---

## Part 12 — The other `llmflux` commands

```bash
llmflux --version                     # which LLMFlux you're running
llmflux show-models                   # every model key you can pass to --model
llmflux show-models | grep -i qwen    # ...just one family

llmflux jobs                          # your current LLMFlux jobs
llmflux jobs --all                    # ...including finished ones
llmflux jobs --all --state FAILED     # ...only failures (repeat --state for more)

llmflux status 1234567                # details for one job: state, times, node, files

llmflux logs 1234567                  # last 100 lines of the job's output and errors
llmflux logs 1234567 --tail 30        # ...last 30
llmflux logs 1234567 -f               # follow it live (Ctrl-C stops watching, not the job)
llmflux logs 1234567 --stderr-only    # ...errors only (also: --stdout-only)

llmflux cancel 1234567                # stop a job
llmflux cancel 1234567 --force        # ...if it won't stop
```

**`llmflux benchmark`** measures how fast a model runs on a given GPU. It makes
its own test prompts, so you don't need a file:

```bash
llmflux benchmark --model Qwen2.5-7B-Instruct --num-prompts 50 \
    --account $WORKSHOP_ACCOUNT --partition $WORKSHOP_PARTITION --time 00:30:00
```

Use it to compare models or GPU types before a big run. It takes most of the
`llmflux run` options, including `--gpus-per-node` and `--input` (to benchmark
with your own prompts).

LLMFlux only keeps track of jobs that LLMFlux started. Slurm's own commands see
everything:

```bash
squeue -u $USER                       # all your jobs
sacct -X -S today --format=JobID,JobName%40,State,Elapsed   # today's jobs, finished ones too
```

---

## Part 13 — Before you leave

```bash
llmflux jobs            # make sure nothing is still running
llmflux cancel JOB_ID   # cancel anything you don't need any more
```

The workshop reservation ends after the session, but your files stay in
`~/llmflux-workshop`, and you can keep using LLMFlux on Delta or DeltaAI with any
allocation you have:

```bash
module load llmflux && conda activate base
llmflux run --model Qwen2.5-7B-Instruct --input prompts/all.jsonl \
    --account YOUR_ACCOUNT --partition gpuA100x4 --time 00:30:00    # ghx4 on DeltaAI
```

(`accounts` lists the allocations you can charge to.) Without the
reservation, your job waits in the general queue, so expect anywhere from a few
minutes to a few hours.

- This guide and the scripts: you're reading it. Bookmark it, or clone it with `git clone`.
- LLMFlux documentation: <https://github.com/Center-for-AI-Innovation/llmflux>
- Delta documentation: <https://docs.ncsa.illinois.edu/systems/delta/en/latest/>
- DeltaAI documentation: <https://docs.ncsa.illinois.edu/systems/deltaai/en/latest/>

---

## Troubleshooting

| What you see | What to do |
| --- | --- |
| `Permission denied` when logging in | Wrong password, or the Duo approval wasn't completed. Try again slowly. If it keeps failing, ask a facilitator. |
| `The workshop isn't configured yet` | Not your fault. Tell a facilitator. |
| `llmflux: command not found` | Run `source ~/llmflux-workshop/workshop.env` again. You need to do this every time you log in. |
| `Workshop settings aren't loaded` | Same fix: `source ~/llmflux-workshop/workshop.env` |
| `No such file: prompts/all.jsonl` | Run `python make_prompts.py` first, from inside `~/llmflux-workshop` (`cd ~/llmflux-workshop`). |
| Job stays PENDING with `(Resources)` | It's waiting for a free GPU. Everyone shares the same few nodes, so this is normal. Use the time to read the sample results. |
| Job stays PENDING with `(Reservation)` or `(ReqNodeNotAvail)` | Tell a facilitator. The reservation might not be active. |
| Job FAILED | Run `llmflux logs JOB_ID` and show a facilitator the last lines. |
| `results/all.json does not exist yet` | The job hasn't finished. Check `llmflux jobs`. |
| A reply is flagged `not valid JSON`, `JSON is missing …`, or `not one of the allowed labels` | The model didn't follow the instructions. That's a real result, not a bug in your setup. Look at what it wrote instead. |
| `This workshop runs on DeltaAI, but you're logged in to Delta` (or the reverse) | Log out and log in to the other system, using the table in Part 1. |
| Anything else | Copy the whole error message, and raise your hand. |

## Cheat sheet

```bash
source ~/llmflux-workshop/workshop.env          # every login
python make_prompts.py [--task NAME] [--limit N] [--input data/x.csv]
bash submit.sh prompts/NAME.jsonl               # submit; prints the job ID
llmflux jobs                                    # what's running
llmflux logs JOB_ID -f                          # follow a job (Ctrl-C to stop watching)
llmflux cancel JOB_ID                           # stop a job
python show_results.py results/NAME.json [--csv results/NAME.csv]

# LLMFlux directly (Parts 9-12)
head -1 prompts/NAME.jsonl | python -m json.tool   # read one request
llmflux run --model MODEL --input prompts/NAME.jsonl --output results/NAME.json \
    --account $WORKSHOP_ACCOUNT --partition $WORKSHOP_PARTITION --time 00:20:00
llmflux serve --model MODEL --email YOU@illinois.edu \
    --account $WORKSHOP_ACCOUNT --partition $WORKSHOP_PARTITION --time 01:00:00
llmflux connect JOB_ID                          # endpoint and API key for a serve job
llmflux show-models                             # model keys for --model
llmflux status JOB_ID                           # details for one job
llmflux jobs --all                              # finished jobs too
```

---

This workshop material is released under the [MIT License](LICENSE).
