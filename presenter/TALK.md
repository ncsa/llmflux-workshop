# The talk: ~15 minutes, plus add-on blocks

Slide *content*, not formatted slides. Each numbered item is roughly one slide at
about 1.5 minutes. The talk contains one small live demo, started at the beginning
and shown near the end, so it fits even if you only get 15 minutes. If you get
more time, the add-on blocks at the bottom can be added or skipped one by one.

Fill the `[from dry run]` placeholders with numbers measured on Delta, not
estimates. A specific measured number is more credible than a round guess.

## Before you walk up

- Your workspace is set up (`setup_workshop.sh`), and prompts are built (`python make_prompts.py`).
- A terminal is logged in to Delta with `source ~/llmflux-workshop/workshop.env` already run.
- `sample_results/all.json` from the dry run is in place as a fallback.
- **Decide in advance:** if your talk slot isn't covered by the reservation, the
  job may sit in Delta's general queue and miss the reveal. Slide 8 then uses
  the sample results, and you say so ("this one ran during my dry run").

## Slides

1. **Hook.** Ask the room: *"Who has thousands of documents, images, or records
   they wish they could ask an LLM about?"* Then, on screen:
   `bash submit.sh prompts/all.jsonl`. *"I'm starting something now; we'll come
   back to it."*

2. **The gap.** Chat tools work one prompt at a time, but research data comes in
   thousands. Copy-pasting doesn't scale. Commercial APIs bring costs and
   data-handling questions (unpublished data, data covered by IRB rules or data-use agreements).

3. **What an agent is.** An LLM, plus tools, in a loop: decide what to do, act,
   look at the result, decide again. Coding agents that write and run scripts
   for you work this way. It's powerful for open-ended work with many steps. It's
   the wrong shape for the same step done 50,000 times.

4. **The ladder: three campus tools, three shapes of work.**
   - **Illinois Chat**: an assistant grounded in your documents, with citations. *Conversational.*
   - **LLMHub**: pick an open model, run it on NCSA hardware, chat with it or call it through an OpenAI-compatible API. *Interactive and agents.*
   - **LLMFlux**: batch jobs on your own allocation. *The same step, at scale.*

   All three use open models on campus hardware.

5. **The pattern to remember.** *Design with an agent, run at scale in batch.*
   Use an assistant to get the prompt and code right on 5 examples, then a batch
   job to run them on 50,000. If people remember one slide, it should be this one.

6. **What LLMFlux is.** JSONL in (one request per line, OpenAI batch format),
   JSON out, one command. Diagram: login node → Slurm → GPU node → results.
   (Borrow the "Big picture" diagram from the participant guide.)

7. **What it hides.** Without it you write the Slurm script, set up the
   container, configure the GPU environment, download the model, start and
   health-check the inference engine (vLLM), retry failed requests, and save
   progress partway through. With it:
   `llmflux run --model Qwen2.5-7B-Instruct --input prompts.jsonl`.
   Plus open models on your allocation: no per-token bill, data stays on campus
   systems, and a pinned model version for reproducibility. `llmflux show-models` lists 80+.

8. **The reveal.** Back to the terminal. `llmflux jobs --all`, then
   `python show_results.py results/all.json`. *"48 requests: [from dry run] min
   in the queue, [from dry run] to load the model, [from dry run] seconds to
   answer them all."* Linger on the **extract** section.

9. **The lesson: LLM output is data you have to check.** Show the validation line
   (`48/48 replies usable`, or better, one that isn't). If the dry run produced
   a label outside the list or a made-up number, put it on this slide. A real
   failure is more memorable than a clean run. At 16 items you check by eye; at
   16,000 the check has to be part of the pipeline.

10. **Closing the loop with agents.** `llmflux serve` (or an LLMHub deployment)
    gives you an OpenAI-compatible endpoint on campus hardware. Agent frameworks
    and coding agents can use it instead of a commercial API. The ladder connects
    in both directions.

11. **Get started.** The repo link, or a QR code; the guide stands on its own.
    `module load llmflux`, then three commands. *"If we have time, let's do it
    together right now."* That line leads into block 3.

## Add-on blocks

Decide at each boundary based on the clock. Every block can be skipped.

| Block | Adds | What happens | Go/no-go |
| --- | --- | --- | --- |
| **1. Live change** | +5 min | Ask Illinois Chat (or an LLMHub chat) to write a new `TASKS` entry, e.g. *"extract the study's limitations as a JSON list"*. Paste it into `make_prompts.py`, run `python make_prompts.py --task <name>` and `bash submit.sh prompts/<name>.jsonl`, and show the result at the end of Q&A. | Your terminal works. This is the most memorable 5 minutes you can add: an assistant writes the step and the cluster runs it. |
| **2. Hosted assistants** | +10–15 min | `DEMOS.md` §1 (Illinois Chat) and §2 (LLMHub) | Demos prepared the day before, venue Wi-Fi works |
| **3. Hands-on** | +45 min | The participant guide (repo README), Parts 1–7 | **Only if** participant logins were tested beforehand and the reservation is active. Otherwise share the link and move on. See `facilitator/README.md`. |

If time is short, move the Q&A to the end of block 1 so its results reveal
happens during questions.
