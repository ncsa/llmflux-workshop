# The talk: ~15 minutes, leading into the hands-on

For the **"LLM Flux"** session: Tuesday Oct 6, 10:00–11:45, Track 1, Room 1030,
at the NCSA Regional Workshop on AI. The session listing promises *"LLM workflows,
fine-tuning, and deployment strategies"*, so the talk is built around those three.

Slide *content*, not formatted slides. Each numbered item is roughly one slide at
about 1.5 minutes. The talk contains one small live demo, started at the
beginning and shown near the end. The full session plan, with the hands-on, is in
[`facilitator/README.md`](../facilitator/README.md).

Fill the `[from dry run]` placeholders with numbers measured on Delta, not
estimates. A specific measured number is more credible than a round guess.

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
   `python show_results.py results/all.json`. *"48 requests: [from dry run] min
   in the queue, [from dry run] to load the model, [from dry run] seconds to
   answer them all."* Linger on the **extract** section.

10. **The lesson: LLM output is data you have to check.** Show the validation line
    (`48/48 replies usable`, or better, one that isn't). If the dry run produced a
    label outside the list or a made-up number, put it on this slide. A real
    failure is more memorable than a clean run. At 16 items you check by eye; at
    16,000 the check has to be part of the pipeline.

11. **Now you.** The repo link and QR code. *"Open Open OnDemand like yesterday,
    and open this page next to it. Everything I just did, you're about to do."*
    → hands-on.

## Optional extras, if there's time

| Block | Adds | What happens |
| --- | --- | --- |
| **Live change** | +5 min | Ask Illinois Chat (or an LLMHub chat) to write a new `TASKS` entry, e.g. *"extract the study's limitations as a JSON list"*. Paste it into `make_prompts.py`, run `python make_prompts.py --task <name>` and `bash submit.sh prompts/<name>.jsonl`, and show the result in the debrief. It's the "design interactively, run in batch" pattern, live. Participants do the same thing in Part 7B. |
| **`llmflux serve`** | +5 min | The fourth deployment strategy: your own OpenAI-compatible endpoint on your allocation, for agents and apps. Show `llmflux serve --help` and the `connect` output from one you started earlier. Don't start one live; loading takes minutes. |
