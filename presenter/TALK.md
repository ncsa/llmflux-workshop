# The talk: ~15 minutes, leading into the hands-on

For the **"LLM Flux"** session: Tuesday Oct 6, 10:00–11:45, Track 1, Room 1030,
at the NCSA Regional Workshop on AI. The session listing promises *"LLM workflows,
fine-tuning, and deployment strategies"*, so the talk is built around those three.

Slide *content*, not formatted slides. Each numbered item is roughly one slide at
about 1.5 minutes. The talk contains one small live demo, started at the
beginning and shown near the end. The full session plan, with the hands-on, is in
[`facilitator/README.md`](../facilitator/README.md).

The numbers below were measured in the Oct 2 dry run (Qwen2.5-7B-Instruct, one
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

- Your workspace is set up (`setup_workshop.sh`), and prompts are built (`python make_prompts.py`).
- A terminal is logged in to Delta with `source ~/llmflux-workshop/workshop.env` already run.
- `sample_results/all.json` from the dry run is in place as a fallback.
- The repo link (and a QR code for it) is on your last slide.
- **Decide in advance:** if the job hasn't finished by slide 9, show the sample
  results and say so ("this one ran during my dry run").

## Slides

1. **Hook + start the clock.** Ask the room: *"Who has thousands of documents,
   images, or records they wish they could ask an LLM about?"* Then, on screen:
   `bash submit.sh prompts/all.jsonl`. *"I'm starting something now; we'll come
   back to it in ten minutes."*

2. **The gap.** Chat tools work one prompt at a time, but research data comes in
   thousands. Copy-pasting doesn't scale. Commercial APIs bring costs and
   data-handling questions (unpublished data, data covered by IRB rules or data-use agreements).

3. **An LLM workflow, in research terms.** Data → prompts → model → outputs →
   validation → analysis. It's the same shape as any other computational
   pipeline, and the same habits apply: version your inputs, record which model
   and settings you used, and check your outputs.

4. **Deployment strategies: three ways to use an LLM on campus.**
   - **Hosted assistant, Illinois Chat:** chat with an assistant grounded in your documents, with citations. *For conversation and exploration.*
   - **Model service, LLMHub:** pick an open model, run it on NCSA hardware, chat with it or call it through an OpenAI-compatible API. *For interactive use, applications, and agents.*
   - **Batch jobs, LLMFlux:** a job on your allocation that starts, processes the whole dataset, and gives the GPU back. *For the same step, at scale.*

   All three use open models on campus hardware. The rest of the session is about the third.

5. **The pattern to remember.** *Design interactively, run in batch.* Use a chat
   assistant or an AI agent (an LLM with tools, in a loop) to get the prompt right
   on 5 examples. Then run it as a batch job over 50,000. If people remember one
   slide, it should be this one.

6. **What LLMFlux is.** JSONL in (one request per line, in OpenAI's batch
   format), JSON out, one command. Diagram: login node → Slurm → GPU node →
   results. (Borrow the "Big picture" diagram from the participant guide.)

7. **What it hides.** Without it you write the Slurm script, set up the
   container, configure the GPU environment, download the model, start and
   health-check the inference engine (vLLM), retry failed requests, and save
   progress partway through. With it:
   `llmflux run --model Qwen2.5-7B-Instruct --input prompts.jsonl`.
   You also get open models on your own allocation: no per-token bill, data
   stays on campus systems, and a pinned model version for reproducibility.
   `llmflux show-models` lists 80+.

8. **What about fine-tuning?** Address it directly, since it's in the session
   listing: **LLMFlux runs models; it doesn't train them.** The practical advice:
   try the cheaper options first, in this order:
   (1) better prompts and a few worked examples in the prompt,
   (2) grounding in your documents (what Illinois Chat does),
   (3) a bigger or more specialized model (`show-models` has medical, code, math, and vision models),
   and only then (4) fine-tuning, which needs labeled data and a training job.
   If you do fine-tune (for example with Hugging Face's libraries on Delta's
   GPUs), LLMFlux can run *your* model in batch: write a small custom config
   whose `hf_name` points at the fine-tuned model's directory on the cluster,
   then pass `--custom-config-path` (vLLM engine; see "Custom Model Configuration"
   in LLMFlux's `docs/MODELS.md`). Fine-tuning and batch inference complement
   each other. ☐ *Replace or extend this slide if you plan to
   say more about fine-tuning on Delta.*

9. **The reveal.** Back to the terminal. `llmflux jobs --all`, then
   `python show_results.py results/all.json`. *"48 requests: seconds in the
   queue, about a minute to start the container and load the model, then
   10 seconds to answer them all."* (That's DeltaAI. On Delta's A100s, loading
   took about 2 minutes and answering about 25 seconds.) The point to land: **the
   model loading dominates**, so one job with many requests beats many small
   jobs. Linger on the **extract** section.

10. **The lesson: LLM output is data you have to check.** Show the validation line:
    `48/48 replies usable`. Then show what it *didn't* catch. In the dry run, every
    reply passed the format checks, and still (check your own run for its versions):
    - `"data_size": "null"`: the text "null" instead of a real JSON null, in some rows but not others
    - genomics `g15`: "sample_size" came back as *230 metagenome-assembled genomes*, which is a result, not a sample size
    - genomics `g12`: "technology" came back as *deep mutational scanning*, which is where the training data came from; the method is a protein language model
    - genomics `g14`: a long-read splicing study labeled *Epigenomics*

    Format checks are automatic; correctness checks aren't. At 16 items you check
    by eye; at 16,000 you sample and spot-check, and you build both kinds of check
    into the pipeline.

11. **Now you.** The repo link and QR code. *"Open Open OnDemand like yesterday,
    and open this page next to it. Everything I just did, you're about to do."*
    → hands-on.

## For a genomics audience

Same talk, with the genomics data: `python make_prompts.py --dataset genomics`,
then `bash submit.sh prompts/genomics-all.jsonl` and
`python show_results.py results/genomics-all.json`. Adjust these slides:

- **1 (hook):** *"Who has a stack of papers, sample sheets, or annotation notes they'd like to mine?"*
- **2 (the gap):** add a point about genomic and clinical data: it often *can't*
  go to a commercial API, so running open models on campus hardware matters more here.
- **5 (the pattern):** genomics examples: triaging literature for a review,
  pulling organism, assay, and sample size out of methods sections, cleaning up
  inconsistent free-text sample metadata.
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
