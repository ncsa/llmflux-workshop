# The talk: ~15 minutes, leading into the hands-on







For the **"LLM Flux"** session: Tuesday Oct 6, 10:00–11:45, Track 1, Room 1030,
at the NCSA Regional Workshop on AI. The session listing promises *"LLM workflows,
fine-tuning, and deployment strategies"*, so the talk is built around those three.

This is a teaching talk, not a product pitch. The goal is for people to understand
how batch LLM inference on a cluster works and when it's the right tool. LLMFlux
is how we do it today, not the subject.

The slides themselves are [`slides/slides.pdf`](slides/slides.pdf), built from
[`slides/slides.typ`](slides/slides.typ) with [Typst](https://typst.app). To
edit, change `slides.typ`, then run `typst compile slides.typ` in that folder
(or `tinymist preview slides.typ` to see changes live). This file is the
speaker's outline:
slide *content*, not formatted slides. Each numbered item is roughly one slide at
about 1.5 minutes. The talk contains one small live demo, started at the
beginning and shown near the end. The full session plan, with the hands-on, is in
[`facilitator/README.md`](../facilitator/README.md).

The numbers below were measured in the Oct 2 and Oct 4 dry runs (Qwen2.5-7B-Instruct, one
GPU, model already in the shared cache, no reservation). On the day, quote the
numbers from your own job if they differ: `sacct -j <id> -o Elapsed` and the
"Run metrics" line from `show_results.py`.

## Who's in the room

Beginner-to-intermediate academic researchers from many disciplines, mostly new
to ML. Most of them were in Track 1 on Monday, which covered logging in to Delta,
Open OnDemand, VS Code, and Jupyter, so they've seen the cluster once. Don't
assume they remember Slurm, and don't assume they've used an LLM for anything
beyond chat.

## Before you walk up

- **The slides**, full screen, from your laptop:
  ```bash
  evince --presentation ~/code/llmflux-workshop/presenter/slides/slides.pdf
  ```
  Arrow keys, Page Down, or a clicker to move; **B** blanks the screen (for
  switching to the terminal); **Esc** leaves. Set the projector to **mirror**
  your screen (Settings → Displays), so the room sees the terminal too. Backup:
  the same PDF opens from GitHub on any machine.
- A terminal logged in to Delta (Open OnDemand → **Clusters** → **>_Delta Shell
  Access**), with these already run:
  ```bash
  bash /projects/bccu/llmflux-workshop/workshop/setup_workshop.sh   # once
  source ~/llmflux-workshop/workshop.env                            # every login
  cd ~/llmflux-workshop                                             # run everything from here
  python make_prompts.py
  ```
- The fallback is already in your workspace: `sample_results/all.json`, from the dry run.
- The repo link (and a QR code for it) is on your last slide.
- **Decide in advance:** if the job hasn't finished by slide 10, show the sample
  results and say so ("this one ran during my dry run").

## Slides

1. **Opening: a familiar problem, and start the demo job.** Start with a task
   most of the room will recognize: *"Say you have 2,000 open-ended survey
   responses, or the methods sections of 500 papers. You want each one
   summarized, sorted into categories, and a few facts pulled out into a
   spreadsheet. By hand, or one at a time in a chat window, that's weeks of
   work."* Then ask: *"What's that pile in your own research?"* Take two or three
   answers, a minute at most. They make good examples for slide 6 and the
   debrief. Then, on screen: `bash submit.sh prompts/all.jsonl`. *"This sends 16
   research abstracts to a model on Delta, with three tasks for each one:
   summarize, classify, and pull out key facts. That's 48 requests. It'll wait
   its turn and run while I talk, and we'll look at the results near the end."*

2. **The big picture: AI in biological work.** A quick bridge, under a
   minute. Builds on David's talk on Monday. The examples on the slide
   (annotating thousands of images, protein structure prediction, generating
   synthetic records, screening imaging for diagnosis) share one shape: the
   same model applied to a very large number of items. That's the kind of work batch jobs are for, and it
   leads into the next slide. Note: AlphaFold is a deep-learning model for
   protein structures, not a language model, so say "AI models" for that
   example rather than "LLMs."

3. **Why run an LLM in batch?** Chat tools handle one prompt at a time. Many
   research questions involve hundreds or thousands of documents or records, and
   doing those one by one in a chat window isn't practical. Sending the data to a
   commercial API is one option, but it raises cost and data-handling questions
   (unpublished data, data covered by IRB rules or data-use agreements). Running
   an open model on a cluster you already have access to is another.

4. **Deployment strategies: three ways to run an LLM.** Each fits a different
   kind of work. Campus examples in parentheses.
   - **An assistant grounded in your documents** (Illinois Chat): you ask questions and it answers with citations. *Good for conversation and exploration.*
   - **A model running as a service** (LLMHub): always on, and you call it from code through an API. *Good for interactive tools, applications, and agents.*
   - **A batch job** (LLMFlux): starts, processes a whole dataset, and releases the GPU. *Good for applying the same step to many items.*

   The tradeoff is responsiveness versus throughput: a service answers right
   away but holds a GPU the whole time; a batch job waits in the queue but uses
   the GPU only while there's work. The hands-on uses batch, because it's the
   one that fits how an HPC cluster is shared.

5. **A closer look at the batch option: an LLM workflow with LLMFlux.** It's
   the same shape as any other computational pipeline. Diagram:

   ```
   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌──────────┐
   │Your data│──▶│ Prompts │──▶│ Model   │──▶│ Answers │──▶│ Checks  │──▶│ Analysis │
   │CSV, text│   │ (JSONL) │   │on a GPU │   │ (JSON)  │   │         │   │          │
   └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘   └──────────┘
   └──────── you ────────┘     └ LLMFlux ┘   └──────────────── you ─────────────────┘
      make_prompts.py          llmflux run     show_results.py, then your usual tools
   ```

   The tool runs the middle step: it reads the prompts, runs the model, and
   writes the answers. It doesn't look at what the model said. Turning your data
   into prompts, and checking and analyzing the answers, stay your job. (Slide
   11 shows why the checking matters.) The usual habits apply: version your
   inputs, record which model and settings you used, and check your outputs.

6. **The pattern to remember.** *Design interactively, run in batch.* Use a chat
   assistant or an AI agent (an LLM with tools, in a loop) to get the prompt right
   on 5 examples. Then run it as a batch job over 50,000. This is the main
   takeaway of the talk.

7. **What a batch inference job actually does.** Walk through the steps:
   Slurm assigns a GPU; a container starts with the software; an inference
   engine (vLLM) loads the model's weights into GPU memory; every request in the
   input file is run through the model; the answers are written out; the GPU is
   released. The input is JSONL, one request per line, in a format (OpenAI's
   batch format) that many tools share. Diagram: login node → Slurm → GPU node →
   results. (Borrow the "Big picture" diagram from the participant guide.)

8. **Doing it yourself, or with a tool.** You can script each of those steps
   yourself: a Slurm script, the container, the engine, checking it's ready,
   retrying failed requests, saving progress partway. LLMFlux is one tool that
   wraps them into a single command:
   `llmflux run --model Qwen2.5-7B-Instruct --input prompts.jsonl`.
   It's worth knowing the steps anyway, because they're what you debug when a
   job fails. Tradeoffs of running open models on your own allocation:
   - You spend allocation hours instead of paying per request.
   - The data stays on systems you're already approved to use.
   - You can record the exact model version, which helps reproducibility.
   - Open models of this size are less capable than the largest commercial
     models, so check whether one is good enough for your task (slide 11).

9. **What about fine-tuning?** It's in the session listing, so address it
   directly. Fine-tuning means training an existing model further on your own
   labeled examples, so it gets better at one task. It's the most expensive way
   to improve results, so try the cheaper ones first, in this order. **The first
   three involve no training at all.**

   | | What it means | In this workflow |
   | --- | --- | --- |
   | **1. Better instructions** | Rewrite the prompt, and add two or three worked examples of an input and the answer you want. | Edit the task in `make_prompts.py`. Try it in a chat window first, then run it in batch (slide 6). |
   | **2. Give the model the reference text** | Put what it needs to know into the prompt itself: the document, a codebook, definitions of your labels. When a tool finds the relevant passages for you automatically, that's called RAG; it's what Illinois Chat does. | Already happening: every request includes its abstract. Add your codebook or label definitions to the instructions. |
   | **3. A different model** | A larger or more specialized model. Change one setting and rerun. Larger models use more GPU time per run, but there's still no training. | `--model`. `llmflux show-models` lists medical (MedGemma), code, math, and vision models. |
   | **4. Fine-tuning** | Train a model on your labeled examples, usually hundreds or more. Needs that labeled data, a separate GPU training job, and time to test the result. | LLMFlux doesn't train models. You train with other tools (for example Hugging Face's libraries on Delta's GPUs). LLMFlux can then run the result: write a small config file pointing at the trained model's folder and pass it with `--custom-config-path` (vLLM engine only; see "Custom Model Configuration" in LLMFlux's `docs/MODELS.md`). |

   Options 1 and 3 take minutes, 2 takes some writing, and 4 takes labeled data
   and a training run. ☐ *Replace or extend this slide if you plan to say more
   about fine-tuning on Delta.*

10. **The results.** Back to the terminal. `llmflux jobs --all`, then
   `python show_results.py results/all.json`. *"48 requests: about two minutes
   to start the container and load the model, then under a minute to answer
   them all."* (Oct 5 test on the reservation's A40s: just under 3 minutes in
   total, 48 seconds answering.) The point to land: **loading the model takes most of the time**,
   so one job with many requests is far more efficient than many small jobs.
   Spend some time on the **extract** section.

11. **Checking the answers.** The model did well: `48/48 replies usable`, and
    most of the answers are right. Checking is still part of the method, the same
    way you'd spot-check a research assistant's coding before using it in a
    paper. There are two kinds of check:
    - **Format checks**, which a script can do: is the reply valid JSON, are the
      requested fields there, is the label one of the allowed ones? That's what
      `show_results.py` checks, and every reply passed.
    - **Correctness checks**, which need a person: does the answer match the
      abstract? Put one abstract next to its answer and read them together.
      Examples from the Oct 4 dry run (pick your own from the demo job, since
      answers can vary between runs):
      - `p09`: the "method" is *"Linking high-resolution land surface
        temperature"*, the first words of the abstract rather than a method.
        The field is filled in, so the format check passes.
      - `p06`: the abstract doesn't give a sample size, and the model wrote the
        word `"null"` in quotes. A script counting missing values would count
        that as a real answer.

    At 16 items you can read them all. At 16,000 you read a random sample, say
    50, count how many are wrong, and report that rate along with your results.

12. **Now you.** The repo link, <https://github.com/ncsa/llmflux-workshop>,
    and its QR code (already on the slide; also `presenter/repo-qr.svg`).
    *"Open Open OnDemand like yesterday, and open this page next to it.
    Everything I just did, you're about to do."*
    → hands-on.

## For a genomics audience

Same talk, with the genomics data: `python make_prompts.py --dataset genomics`,
then `bash submit.sh prompts/genomics-all.jsonl` and
`python show_results.py results/genomics-all.json`. Adjust these slides:

- **1 (opening):** use a genomics pile as the example: *"the methods sections of 500 papers, where you want the organism, assay, and sample size from each,"* or a few thousand rows of free-text sample metadata.
- **3 (the gap):** add a point about genomic and clinical data: it often *can't*
  go to a commercial API, so running open models on campus hardware matters more here.
- **6 (the pattern):** genomics examples: triaging literature for a review,
  pulling organism, assay, and sample size out of methods sections, cleaning up
  inconsistent free-text sample metadata.
- **11 (checking):** examples from the genomics dry run: `g15`'s
  "sample_size" came back as *230 metagenome-assembled genomes*, which is a
  result, not a sample size; `g12`'s "technology" came back as *deep mutational
  scanning*, where the training data came from, when the method is a protein
  language model; and `g14`, a long-read splicing study, was classified as
  *Epigenomics*.
- **Be clear about scope:** these models read *text about* genomics. Sequence
  data itself is the job of domain models, like the deep-learning variant
  callers in the genomics session. A good line: *"An LLM can read 10,000 methods
  sections. It shouldn't be calling your variants."*

For a 10–20 minute version, use the "Format A" plan in
[`facilitator/LEAD_THIS_SESSION.md`](../facilitator/LEAD_THIS_SESSION.md).

## Optional extras, if there's time

| Block | Adds | What happens |
| --- | --- | --- |
| **Live change** | +5 min | Ask Illinois Chat (or an LLMHub chat) to write a new `TASKS` entry, e.g. *"extract the study's limitations as a JSON list"*. Paste it into `make_prompts.py`, run `python make_prompts.py --task <name>` and `bash submit.sh prompts/<name>.jsonl`, and show the result in the debrief. It's the "design interactively, run in batch" pattern, live. Participants do the same thing in Part 7B. |
| **`llmflux serve`** | +5 min | The fourth deployment strategy: your own OpenAI-compatible endpoint on your allocation, for agents and apps. Show `llmflux serve --help` and the `connect` output from one you started earlier. Don't start one live; loading takes minutes. |
