# Facilitator guide

How to run the **"LLM Flux"** session at the NCSA Regional Workshop on AI
(Tuesday Oct 6, 10:00–11:45, Track 1, Room 1030). Participants new to HPC and ML
run batch LLM inference with LLMFlux on NCSA Delta. This guide covers the plan
for the day, prep, queue capacity, and fallbacks.

| Path | Who it's for |
| --- | --- |
| [`../README.md`](../README.md) | Participants: the hands-on guide, step by step |
| [`../presenter/TALK.md`](../presenter/TALK.md) | The presenter: the ~15-minute talk and optional extras |
| [`../presenter/DEMOS.md`](../presenter/DEMOS.md) | The presenter: scripts for the Illinois Chat, LLMHub, and LLMFlux demos |
| `README.md` (this file) | Facilitators: plan, prep, capacity, fallbacks |
| `workshop/workshop.conf` | Facilitators fill this in **once**, in the shared copy on Delta. It's the only file with site-specific values. |
| `workshop/setup_workshop.sh` | Participants run this once. It copies the scripts and data and writes `workshop.env`. |
| `workshop/make_prompts.py` | Turns `data/abstracts.csv` into a JSONL batch (summarize / classify / extract) |
| `workshop/submit.sh` | Wraps `llmflux run` with the workshop settings and prints the full command |
| `workshop/show_results.py` | Prints results grouped by task, validates the JSON extraction, writes a CSV |
| `workshop/data/abstracts.csv` | 16 synthetic abstracts across disciplines, written for this workshop |

## Session plan (Tue 10:00–11:45)

The participants are Track 1 attendees: beginner-to-intermediate researchers
from many disciplines. On Monday morning Track 1 covered logging in to Delta,
Open OnDemand, VS Code, and Jupyter, so most have logged in once. Some will have
come only for this session.

| Time | Min | Segment | Notes |
| --- | --- | --- | --- |
| 10:00 | 2 | **Log in first.** *"Open Open OnDemand like yesterday and get a Delta shell open."* Facilitators help anyone stuck. | Login problems found now get fixed during the talk instead of holding up the hands-on. The presenter submits the demo job now. |
| 10:02 | 15 | **Talk** ([`presenter/TALK.md`](../presenter/TALK.md)), ending with the demo job's results | |
| 10:17 | 13 | **Demos:** Illinois Chat, LLMHub ([`presenter/DEMOS.md`](../presenter/DEMOS.md) §1–2) | **This is the buffer.** Shorten it or cut it if the room is behind. |
| 10:30 | 50 | **Hands-on:** participant guide, Parts 2–7 | Target: **everyone has submitted by 10:50.** Watch `squeue -R <reservation>`. While jobs are queued, participants read `sample_results/`. |
| 11:20 | 15 | **Debrief.** Put two participants' results on screen. Did classify stay in the label set? Did any JSON fail? Then Part 8 (deployment strategies) and Q&A. | |
| 11:35 | 10 | Wrap-up: links, Part 9 (cancel jobs), slack for overruns | |

If you're behind, cut the demos first, then shorten Part 7 to option B (an
assistant writes a task), which is the step that ties the demos to the hands-on.
If you're far behind, have participants run `show_results.py` on
`sample_results/` and skip submitting their own job. If you're ahead, add the
"Live change" or "`llmflux serve`" extras from `TALK.md`.

## Capacity: will the queue keep up?

Each participant job requests **one A100**. Slurm on Delta allocates whole GPUs,
so a reserved `gpuA100x4` node runs **4 jobs at once**. One job =
queue wait + container start + model load + 48 requests. Measure the last three
in your dry run (`sacct -j <id> --format=Elapsed`). A ~4-minute job is a
reasonable guess to plan with before you have a real number.

```
time for the whole room to finish one job ≈ participants × job_minutes / (nodes × 4)
```

| Participants | Reserved nodes | GPUs | Room finishes one run in (at 4 min/job) |
| --- | --- | --- | --- |
| 20 | 1 | 4 | ~20 min |
| 30 | 1 | 4 | ~30 min — tight |
| 30 | 2 | 8 | ~15 min |
| 40 | 3 | 12 | ~14 min |

Part 7 doubles the load. **Request enough nodes to finish one round in ≲15 minutes.**
If you can't, the fallback (`sample_results/`) still lets everyone complete Part 6.

## Before the session

### As soon as possible

- [ ] **Participant accounts.** Confirm every participant has a Delta login, has set
      their password, and has enrolled in NCSA Duo, *before the day*. Send the
      Part 1 instructions out in advance and ask everyone to log in once. This is
      the most likely thing to eat the first 20 minutes.
- [ ] **Reservation.** NCSA ticket for N `gpuA100x4` nodes (see Capacity),
      covering 09:30–12:00 (the extra time before is for your own checks), on the
      participants' account. Ask NCSA to confirm the participants' account is
      allowed to use it.
- [ ] **Account name.** Run `accounts` on Delta as a participant-equivalent user.
      The GPU account ends in `-delta-gpu`.
- [ ] **Shared folder.** Clone this repo somewhere every participant can read:
      ```bash
      git clone <this repo's URL> /projects/<project>/llmflux-workshop
      ```
      The weights cache and sample results (below) go in there too. Participants
      then run `bash /projects/<project>/llmflux-workshop/workshop/setup_workshop.sh`.
      Fill in `workshop/workshop.conf` in this copy only. Don't commit real
      account or reservation names back to the public repo. Check the group:
      participants must be in the group that owns it (`ls -ld`, and `groups` as a
      participant). For the pathology hackathon, `/projects/bhws` turned out not to
      be readable by the account that needed it, so check this as a real
      participant, not as yourself.

### This weekend / Monday: dry run

The event was confirmed on Friday Oct 2, so there's no week of slack. Do the
dry run as early as possible, so there's still time to fix what it finds.

Do all of this as a test participant account if you can get one, and without the
reservation (`WORKSHOP_RESERVATION=""`) if it isn't active yet.

1. **Check the module.**
   ```bash
   module load llmflux && conda activate base
   llmflux --version                 # note it; the scripts here target 2.x
   module show llmflux               # does it set LLMFLUX_CONTAINERS_DIR?
   ls "$LLMFLUX_CONTAINERS_DIR"/llm_processor.sif
   ```
   If the module doesn't point at a prebuilt `llm_processor.sif`, build one once
   (on a compute node, not the login node) into the shared folder and set
   `WORKSHOP_CONTAINERS_DIR`. **If neither is set, every participant's first
   `llmflux run` builds the container on the login node.**
2. **Stage the model weights** into a shared `HF_HOME` so participants don't each
   download ~15 GB. Once, as yourself:
   ```bash
   export HF_HOME=/projects/<project>/llmflux-workshop/hf-cache
   huggingface-cli download Qwen/Qwen2.5-7B-Instruct    # `hf download` on newer huggingface_hub
   chmod -R g+rwX "$HF_HOME" && find "$HF_HOME" -type d -exec chmod g+s {} +
   ```
   Group-*writable* on purpose: the HuggingFace library takes lock files in the
   cache even when the weights are already there. **Test a run as a second user**
   to confirm a read-only cache isn't a problem (or that group-write fixes it).
   This is the step most likely to work for you and fail for participants.
3. **Fill in `workshop/workshop.conf`** in the shared copy.
4. **Run the participant guide end to end** exactly as a participant would, Parts 2–6.
   Note the job's elapsed time for the Capacity math, and check how long it sits
   in each state.
5. **Keep the results as the sample:**
   ```bash
   mkdir -p /projects/<project>/llmflux-workshop/sample_results
   cp ~/llmflux-workshop/results/all.json /projects/<project>/llmflux-workshop/sample_results/
   ```
   Set `WORKSHOP_SAMPLE_RESULTS` to that directory. Participants who've already
   run setup get it by re-running `setup_workshop.sh`.
6. **Concurrency test.** Submit 8–10 jobs at once (`for i in $(seq 10); do bash submit.sh prompts/all.jsonl; done`
   with different output names) to see how the shared cache and filesystem hold up.
   Note that `submit.sh` names its output after the input file, so copy the input
   to `prompts/all-$i.jsonl` first.

### Morning of

- [ ] `scontrol show res <name>`: it's active and the nodes are idle
- [ ] Run setup as a fresh user and submit one job: it starts, finishes, and `show_results.py` reads it
- [ ] **Submit the presenter's demo job at 10:00** (`presenter/DEMOS.md` §3) so it's done when you reach it
- [ ] Have the shared folder path and Open OnDemand URL ready to put on screen
- [ ] Screenshots or recordings of each live demo, in case the venue Wi-Fi fails

## During the session

```bash
squeue -R <reservation>                         # everyone's jobs on the reservation
squeue -R <reservation> -t PENDING | wc -l      # how backed up the queue is
sacct -X -a -r <reservation> -S 10:00 --format=User,JobID,State,Elapsed   # who's finished
```

Common rescues:

| Symptom | Fix |
| --- | --- |
| Participant's job FAILED | `llmflux logs <id>` on their terminal. Most likely: the shared cache isn't readable or writable for them, or the container dir isn't set. |
| Queue backed up past ~10 min | Announce the sample results; have participants do Part 6 on `sample_results/all.json` while they wait. |
| Many jobs stuck `(Reservation)` | Account isn't authorized for the reservation. Drop `WORKSHOP_RESERVATION` to `""` in the conf and have participants re-run setup and resubmit. They'll go to the general queue, which is slow, but jobs will still run. |
| Someone ran a big model and it's stuck loading | `scancel <id>` with their permission. |

## Known limits

- Everything here was written against LLMFlux 2.0.0 and **has not yet been run on
  Delta**. The dry run above is the real test. The tests (`python -m pytest`)
  cover the scripts' logic, with Slurm and `llmflux` faked out.
- The participant JSONL leaves `model` out of each request on purpose. LLMFlux
  rejects a request whose `body.model` doesn't exactly match the engine's internal
  name (the HuggingFace repo, for vLLM), which is a confusing error for
  first-timers. LLMFlux fills it in from `--model`.
- LLMFlux finds its `.env` relative to its own install, not the participant's
  directory, so `workshop.env` is a file participants `source` rather than a
  `.env` they edit.
