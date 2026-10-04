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
| [`LEAD_THIS_SESSION.md`](LEAD_THIS_SESSION.md) | **Anyone leading this on short notice**: a pre-flight check, a 10–20 minute demo format, and fallbacks |
| `README.md` (this file) | Facilitators: plan, prep, capacity, fallbacks |
| `workshop/workshop.conf` | Facilitators fill this in **once**, in the shared copy on Delta. It's the only file with site-specific values. |
| `workshop/setup_workshop.sh` | Participants run this once. It copies the scripts and data and writes `workshop.env`. |
| `workshop/make_prompts.py` | Turns `data/abstracts.csv` into a JSONL batch (summarize / classify / extract) |
| `workshop/submit.sh` | Wraps `llmflux run` with the workshop settings and prints the full command |
| `workshop/show_results.py` | Prints results grouped by task, validates the JSON extraction, writes a CSV |
| `workshop/data/abstracts.csv` | 16 synthetic abstracts across disciplines, written for this workshop |
| `workshop/data/genomics_abstracts.csv` | 16 synthetic genomics abstracts, for bio-focused sessions (`--dataset genomics`, or `WORKSHOP_DATASET`) |

## Session plan (Tue 10:00–11:45)

The participants are Track 1 attendees: beginner-to-intermediate researchers
from many disciplines. On Monday morning Track 1 covered logging in to Delta,
Open OnDemand, VS Code, and Jupyter, so most have logged in once. Some will have
come only for this session.

| Time | Min | Segment | Notes |
| --- | --- | --- | --- |
| 10:00 | 2 | **Log in first.** *"Open Open OnDemand like yesterday and get a Delta shell open."* Facilitators help anyone stuck, and pair anyone without a laptop with a neighbor. | Login problems found now get fixed during the talk instead of holding up the hands-on. The presenter submits the demo job now. |
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

## Account, system, and shared folder

Confirmed by Greg Bauer on Oct 4: attendees are being added to the ACCESS
**Delta Training** project, `delta_bccu`. That gives them two Slurm accounts:

| Slurm account | Use |
| --- | --- |
| `bccu-delta-gpu` | **This one.** Every workshop job requests a GPU. |
| `bccu-delta-cpu` | CPU-only jobs. Not used by this session. |

These are Delta accounts, so **the workshop runs on Delta** (A100s, partition
`gpuA100x4`). Participants have no DeltaAI allocation through this project. In
the shared `workshop.conf` set:

```bash
WORKSHOP_SYSTEM="delta"
WORKSHOP_ACCOUNT="bccu-delta-gpu"
WORKSHOP_PARTITION="gpuA100x4"
```

Do that in the copy on Delta only, not in the repo (see `CLAUDE.md`).

Files participants need to read go in **`/projects/bccu`** (`/work/hdd/bccu`
also works). Use `/projects/bccu/llmflux-workshop` for the clone, the shared
weights cache, and the sample results. The paths below assume it.

The materials still support DeltaAI (the table at the top of `workshop.conf`
lists its values), for reuse at another event.

## Laptops

Attendees bring their own laptop. Anyone without one shoulder-surfs with
another participant: pair them up during the 10:00 log-in, not at the start of
the hands-on. Pairs share one job, so they don't add to the queue.

## Capacity: will the queue keep up?

Each participant job requests **one GPU**. Slurm allocates whole GPUs, so a
reserved 4-GPU node (`gpuA100x4` or `ghx4`) runs **4 jobs at once**. Measured in
the Oct 2 dry run (Qwen2.5-7B, 48 requests, weights already in the shared cache):

| | Delta (A100) | DeltaAI (GH200) |
| --- | --- | --- |
| Whole job (container start + model load + 48 requests) | ~2.5 min | ~1 min |
| Of which: answering the 48 requests | 21–26 s | 9–11 s |
| First job ever (also downloads the 15 GB of weights) | n/a: DeltaAI's job had already cached them | ~2 min |

```
time for the whole room to finish one job ≈ participants × job_minutes / (nodes × 4)
```

| Participants | Reserved nodes | GPUs | Room finishes one run in, Delta | DeltaAI |
| --- | --- | --- | --- | --- |
| 20 | 1 | 4 | ~13 min | ~5 min |
| 30 | 1 | 4 | ~19 min, tight | ~8 min |
| 30 | 2 | 8 | ~10 min | ~4 min |
| 40 | 3 | 12 | ~9 min | ~4 min |

These assume jobs don't slow each other down. Thirty jobs reading the same
shared cache at once may load more slowly than one did, so treat them as best
cases. Part 7 doubles the load. **Request enough nodes to finish one round in ≲15 minutes.**
If you can't, the fallback (`sample_results/`) still lets everyone complete Part 6.

## Before the session

### As soon as possible

- [ ] **Participant accounts.** Confirm every participant has a Delta login, is
      in `delta_bccu` (Greg Bauer's team is adding them), has set
      their password, and has enrolled in NCSA Duo, *before the day*. Send the
      Part 1 instructions out in advance and ask everyone to log in once. This is
      the most likely thing to eat the first 20 minutes.
- [ ] **Reservation.** Find out what was requested: how many
      nodes on `gpuA100x4`, and which day and time. It needs to cover Tuesday
      09:30–12:00 (the extra time before is for your own checks), and Monday
      12:45–2:30 too if the genomics-session fill might be hands-on rather than a
      demo. Ask NCSA to confirm `bccu-delta-gpu` is allowed to use it
      (`scontrol show res <name>` lists the accounts).
- [ ] **Account.** Run `accounts` as a participant-equivalent user and check
      `bccu-delta-gpu` is listed.
- [ ] **Shared folder.** Clone this repo somewhere every participant can read:
      ```bash
      git clone <this repo's URL> /projects/bccu/llmflux-workshop
      ```
      The weights cache and sample results (below) go in there too. Participants
      then run `bash /projects/bccu/llmflux-workshop/workshop/setup_workshop.sh`.
      Fill in `workshop/workshop.conf` in this copy only. Don't commit real
      account or reservation names back to the public repo. Check the group:
      participants must be in the group that owns it (`ls -ld`, and `groups` as a
      participant; expect `bccu`). For the pathology hackathon, `/projects/bhws` turned out not to
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
   export HF_HOME=/projects/bccu/llmflux-workshop/hf-cache
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
5. **Keep the results as the sample**, for both datasets:
   ```bash
   python make_prompts.py --dataset genomics && bash submit.sh prompts/genomics-all.jsonl
   # ...once both jobs finish:
   mkdir -p /projects/bccu/llmflux-workshop/sample_results
   cp ~/llmflux-workshop/results/{all,genomics-all}.json /projects/bccu/llmflux-workshop/sample_results/
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

- Everything here was written against LLMFlux 2.0.0 and dry-run on Delta and
  DeltaAI on Oct 2 (the Capacity numbers), but **not yet as a `delta_bccu`
  participant** or with a full room's jobs at once. The tests (`python -m pytest`)
  cover the scripts' logic, with Slurm and `llmflux` faked out.
- The participant JSONL leaves `model` out of each request on purpose. LLMFlux
  rejects a request whose `body.model` doesn't exactly match the engine's internal
  name (the HuggingFace repo, for vLLM), which is a confusing error for
  first-timers. LLMFlux fills it in from `--model`.
- LLMFlux finds its `.env` relative to its own install, not the participant's
  directory, so `workshop.env` is a file participants `source` rather than a
  `.env` they edit.
