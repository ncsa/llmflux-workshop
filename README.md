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
**Delta** (NVIDIA A100 GPUs) and **DeltaAI** (NVIDIA GH200 "Grace Hopper"
GPUs). **At the Oct 6 Regional Workshop on AI we're using Delta.** At any other
event, your facilitator will tell you which one. Use that column of this table
for everything below:

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

**If you've already logged in at this workshop** (for example in Monday's Track
1 session), do it the same way. Open OnDemand (option B) is the easiest.

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
setup script inside it, replacing the start of the path below with that one:

```bash
bash /shared/folder/from/facilitator/workshop/setup_workshop.sh
```

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
    --output .../results/all.json --account XXXX-delta-gpu --partition gpuA100x4 \
    --time 00:20:00 --sbatch-arg reservation=XXXX

Job ID: 1234567
```

Here's what each part of that command does:

| Flag | Meaning |
| --- | --- |
| `--model` | Which LLM to run. `llmflux show-models` lists all the options. |
| `--input` / `--output` | Your requests, and where to write the answers |
| `--account` | Which allocation pays for the GPU time |
| `--partition` | Which group of nodes to use (`gpuA100x4` on Delta: nodes with 4 A100 GPUs; `ghx4` on DeltaAI: 4 GH200s) |
| `--time` | The longest the job may run. Slurm stops it after that. Ask for a bit more than you need. |
| `--sbatch-arg reservation=…` | Use the nodes set aside for this workshop |

**Write down your job ID.** You'll use it in the next part.

What just happened: LLMFlux wrote a Slurm job script and handed it to Slurm.
`llmflux run` gives you your prompt back immediately; the job runs on its own.
When it's your turn, Slurm will:

1. give your job one GPU on a compute node
2. start a container with the vLLM inference engine (a container is a packaged software environment, so it runs the same everywhere)
3. load the model's weights onto the GPU
4. send all 48 requests, several at a time
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

## Part 7 — Make it yours (rest of the time)

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
need more than one GPU, so ask a facilitator before you try one here. To run a
different model, change the `--model` value in the `llmflux run` command that
`submit.sh` printed and run that command yourself.

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
API. See the LLMFlux docs.

**What about fine-tuning?** LLMFlux runs models; it doesn't train them. Before
fine-tuning, try better prompts (with a few worked examples), grounding in your
documents, or a more specialized model. If you do fine-tune, LLMFlux can run your
fine-tuned model in batch through a custom model config (see "Custom Model
Configuration" in the LLMFlux docs).

---

## Part 9 — Before you leave

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
```

---

This workshop material is released under the [MIT License](LICENSE).
