# Facilitator guide

How to run the **"LLM Flux"** session: a 105-minute talk and hands-on in which
participants new to HPC and ML run batch LLM inference with LLMFlux on NCSA
Delta or DeltaAI. It was written for, and first run at, the NCSA AI/HPC Regional
Workshop on Oct 6 2026. The exact version used there is the git tag
`workshop-2026-10-06`, and this guide uses that event as its worked example.
It covers the plan for the day, prep, queue capacity, and fallbacks.

| Path | Who it's for |
| --- | --- |
| [`../README.md`](../README.md) | Participants: the hands-on guide, step by step |
| [`../presenter/TALK.md`](../presenter/TALK.md) | The presenter: the ~15-minute talk and optional extras |
| [`../presenter/DEMOS.md`](../presenter/DEMOS.md) | The presenter: scripts for the Illinois Chat, LLMHub, and LLMFlux demos |
| [`LEAD_THIS_SESSION.md`](LEAD_THIS_SESSION.md) | **Anyone leading this on short notice**: a pre-flight check, a 10–20 minute demo format, and fallbacks |
| `README.md` (this file) | Facilitators: plan, prep, capacity, fallbacks |
| `workshop/workshop.conf` | Facilitators fill this in **once**, in the shared copy on the cluster. It's the only file with site-specific values. |
| `workshop/setup_workshop.sh` | Participants run this once. It copies the scripts and data and writes `workshop.env`. |
| `workshop/make_prompts.py` | Turns `data/abstracts.csv` into a JSONL batch (summarize / classify / extract) |
| `workshop/submit.sh` | Wraps `llmflux run` with the workshop settings and prints the full command |
| `workshop/show_results.py` | Prints results grouped by task, validates the JSON extraction, writes a CSV |
| `workshop/data/abstracts.csv` | 16 synthetic abstracts across disciplines, written for this workshop |
| `workshop/data/genomics_abstracts.csv` | 16 synthetic genomics abstracts, for bio-focused sessions (`--dataset genomics`, or `WORKSHOP_DATASET`) |

## Session plan (105 minutes)

At the October 2026 workshop the participants were beginner-to-intermediate
researchers from many disciplines. Most had logged in to Delta once, in an
earlier session on Open OnDemand, VS Code, and Jupyter. Some came only for this
session. The times below are from that event (10:00–11:45).

| Time | Min | Segment | Notes |
| --- | --- | --- | --- |
| 10:00 | 2 | **Log in first.** *"Open Open OnDemand like yesterday and get a Delta shell open."* Facilitators help anyone stuck, and pair anyone without a laptop with a neighbor. | Login problems found now get fixed during the talk instead of holding up the hands-on. The presenter submits the demo job now. |
| 10:02 | 15 | **Talk** ([`presenter/TALK.md`](../presenter/TALK.md)), ending with the demo job's results | |
| 10:17 | 13 | **Demos:** Illinois Chat, LLMHub ([`presenter/DEMOS.md`](../presenter/DEMOS.md) §1–2) | **This is the buffer.** Shorten it or cut it if the room is behind. |
| 10:30 | 30 | **Hands-on:** participant guide, Parts 2–7 | Target: **everyone has submitted by 10:45.** Watch `squeue -A $WORKSHOP_ACCOUNT`. While jobs are queued, participants read `sample_results/`. |
| 11:00 | 20 | **Going further:** Parts 9–12. Show `head -1 prompts/all.jsonl \| python -m json.tool` and walk through the keys (Part 9), then run one `llmflux run` by hand (Part 10) and start an `llmflux serve` job (Part 11) on screen. Participants follow along. | Start the serve job at the beginning of this block: it takes a few minutes to load. |
| 11:20 | 15 | **Debrief.** Put two participants' results on screen. Did classify stay in the label set? Did any JSON fail? Then Part 8 (deployment strategies) and Q&A. | |
| 11:35 | 10 | Wrap-up: links, Part 13 (cancel jobs, including any serve job), slack for overruns | |

In October 2026 the original plan gave Parts 2–7 the full 50 minutes, and most
of the room was done by 11:00 with 45 minutes to spare. What people asked for
was how to use LLMFlux directly, so Parts 9–12 now fill that time.

If you're behind, cut the demos first, then shorten Part 7 to option B (an
assistant writes a task), which is the step that ties the demos to the hands-on.
If you're far behind, have participants run `show_results.py` on
`sample_results/` and skip submitting their own job. If you're ahead, start
Parts 9–12 early, or add the "Live change" extra from `TALK.md`.

## Example setup: October 2026

How the account, system, reservation, and shared folder were set up for the
October 2026 workshop. Yours will have different names; the pattern carries over.

Attendees were added to the ACCESS **Delta Training** project, `delta_bccu`.
That gave them two Slurm accounts:

| Slurm account | Use |
| --- | --- |
| `bccu-delta-gpu` | **This one.** Every workshop job requests a GPU. |
| `bccu-delta-cpu` | CPU-only jobs. Not used by this session. |

These are Delta accounts, so **the workshop ran on Delta**. Participants had
no DeltaAI allocation through this project.

**The reservation** was *magnetic*: any `bccu-delta-gpu` job
that fits the reserved nodes goes into it without naming it. Its GPU nodes are
**A40** nodes, so jobs must ask for the **`gpuA40x4`** partition. A job that asks
for `gpuA100x4` skips the reservation and waits in the general queue. Find it,
and its time window, with:

```bash
scontrol show res | grep -B3 -A10 bccu-delta-gpu     # Flags=...MAGNETIC, the GPU nodes, start and end
```

It covers the whole workshop, not just this session: other sessions' `bccu`
participants use the same nodes. So the room gets *up to* 8 GPUs (2 nodes × 4
A40s), not a guaranteed 8.

In the shared `workshop.conf` set:

```bash
WORKSHOP_SYSTEM="delta"
WORKSHOP_ACCOUNT="bccu-delta-gpu"
WORKSHOP_RESERVATION=""          # magnetic: jobs land in it anyway
WORKSHOP_PARTITION="gpuA40x4"    # where the reservation's GPU nodes are
```

Leave the reservation name out. Jobs reach it without one, and a job that names
a reservation that has ended is rejected, so after the reservation ends,
participants' jobs still work and just go to the general queue.

Do that in the copy on Delta only, not in the repo (see `CLAUDE.md`).

Files participants need to read go in **`/projects/bccu`** (`/work/hdd/bccu`
also works). `/projects/bccu/llmflux-workshop` held the clone, the shared
weights cache, and the sample results. Below, `/projects/PROJECT/llmflux-workshop`
stands for your equivalent.

The materials support DeltaAI too (the table at the top of `workshop.conf`
lists its values).

## Laptops

Attendees bring their own laptop. Anyone without one shoulder-surfs with
another participant: pair them up during the log-in at the start, not at the start of
the hands-on. Pairs share one job, so they don't add to the queue.

## Capacity: will the queue keep up?

Each participant job requests **one GPU**. Slurm allocates whole GPUs, so a
reserved 4-GPU node (`gpuA40x4`, `gpuA100x4`, or `ghx4`) runs **4 jobs at once**. Measured in
the Oct 2–5 dry runs (Qwen2.5-7B, 48 requests, weights already in the shared cache):

| | **Delta (A40), the reservation** | Delta (A100) | DeltaAI (GH200) |
| --- | --- | --- | --- |
| Whole job (container start + model load + 48 requests) | **~3 min** (2:50) | ~2.5 min | ~1 min |
| Of which: answering the 48 requests | **48 s** | 21–26 s | 9–11 s |
| First job ever (also downloads the 15 GB of weights) | n/a | n/a | ~2 min |

```
time for the whole room to finish one job ≈ participants × job_minutes / (nodes × 4)
```

| Participants | Reserved nodes | GPUs | Room finishes one run in, A40 | A100 | DeltaAI |
| --- | --- | --- | --- | --- | --- |
| 20 | 1 | 4 | ~14 min | ~13 min | ~5 min |
| 30 | 1 | 4 | ~21 min, too slow | ~19 min, tight | ~8 min |
| **30** | **2** | **8** | **~11 min (Oct 6)** | ~10 min | ~4 min |
| 40 | 3 | 12 | ~9 min | ~9 min | ~4 min |

**Oct 6:** 2 reserved A40 nodes, 8 GPUs, but shared with other `bccu` sessions,
so expect somewhat longer than ~11 min if they're running jobs too.

These assume jobs don't slow each other down. Thirty jobs reading the same
shared cache at once may load more slowly than one did, so treat them as best
cases. Part 7 doubles the load. **Request enough nodes to finish one round in ≲15 minutes.**
If you can't, the fallback (`sample_results/`) still lets everyone complete Part 6.

## Before the session

### As soon as possible

- [ ] **Participant accounts.** Confirm every participant has a login on the
      right system, is in the workshop's Slurm account (the organizers add them), has set
      their password, and has enrolled in NCSA Duo, *before the day*. Send the
      Part 1 instructions out in advance and ask everyone to log in once. This is
      the most likely thing to eat the first 20 minutes.
- [ ] **Reservation.** Find out what was requested: how many nodes, on which
      partition, and which day and time. It needs to cover the session plus
      about 30 minutes before it, for your own checks. Ask NCSA to confirm the
      workshop's account is allowed to use it (`scontrol show res <name>` lists
      the accounts), and whether it's magnetic. If it is, set
      `WORKSHOP_PARTITION` to its partition and leave `WORKSHOP_RESERVATION`
      empty (see the October 2026 example above).
- [ ] **Account.** Run `accounts` as a participant-equivalent user and check
      the workshop's account is listed.
- [ ] **Shared folder.** Clone this repo somewhere every participant can read:
      ```bash
      git clone <this repo's URL> /projects/PROJECT/llmflux-workshop
      ```
      The weights cache and sample results (below) go in there too. Participants
      then run `bash /projects/PROJECT/llmflux-workshop/workshop/setup_workshop.sh`.
      Fill in `workshop/workshop.conf` in this copy only. Don't commit real
      account or reservation names back to the public repo. Check the group:
      participants must be in the group that owns it (`ls -ld`, and `groups` as a
      participant; in October 2026 it was `delta_bccu`). For the pathology hackathon, `/projects/bhws` turned out not to
      be readable by the account that needed it, so check this as a real
      participant, not as yourself.

### A few days before: dry run

Do the dry run as early as possible, so there's still time to fix what it finds.
(In October 2026 the event was confirmed four days ahead, which was barely enough.)

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
   export HF_HOME=/projects/PROJECT/llmflux-workshop/hf-cache
   hf download Qwen/Qwen2.5-7B-Instruct    # `huggingface-cli` no longer works on Delta
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
   mkdir -p /projects/PROJECT/llmflux-workshop/sample_results
   cp ~/llmflux-workshop/results/{all,genomics-all}.json /projects/PROJECT/llmflux-workshop/sample_results/
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
- [ ] **Submit the presenter's demo job when the session starts** (`presenter/DEMOS.md` §3) so it's done when you reach it
- [ ] Have the shared folder path and Open OnDemand URL ready to put on screen
- [ ] Screenshots or recordings of each live demo, in case the venue Wi-Fi fails

## During the session

```bash
# $WORKSHOP_ACCOUNT is set once you've sourced your own workshop.env
squeue -A $WORKSHOP_ACCOUNT -o "%.10i %.10u %.8T %.12v %R"   # everyone's jobs; %v = the reservation each one is in
squeue -A $WORKSHOP_ACCOUNT -t PENDING | wc -l                # how backed up the queue is
sacct -X -a -A $WORKSHOP_ACCOUNT -S today --format=User,JobID,State,Elapsed   # who's finished
```

Common rescues:

| Symptom | Fix |
| --- | --- |
| Participant's job FAILED | `llmflux logs <id>` on their terminal. Most likely: the shared cache isn't readable or writable for them, or the container dir isn't set. |
| Queue backed up past ~10 min | Announce the sample results; have participants do Part 6 on `sample_results/all.json` while they wait. |
| Jobs pending, with an empty reservation column in the `squeue` above | They didn't land in the reservation. Check `WORKSHOP_PARTITION` is the reservation's partition and that the reservation is still active (`scontrol show res`). |
| Jobs pending with `(Resources)` while the reservation is in use | The reserved GPUs are busy, possibly with other sessions' jobs. Normal for a few minutes; past ~10, announce the sample results. |
| Someone ran a big model and it's stuck loading | `scancel <id>` with their permission. |
| Serve jobs still running at the end | Each holds a GPU until its `--time` runs out. Remind everyone to `llmflux cancel` theirs (Part 13); `squeue -A $WORKSHOP_ACCOUNT` shows any left. |

## Known limits

- Everything here was written against LLMFlux 2.0.0, dry-run on Delta and
  DeltaAI (the Capacity numbers), and used with a full room on Delta in October
  2026. The tests (`python -m pytest`) cover the scripts' logic, with Slurm and
  `llmflux` faked out.
- In LLMFlux 2.0.0, `llmflux run`'s tuning options (`--temperature`,
  `--max-tokens`, `--top-p`, `--top-k`, `--batch-size`, `--save-frequency`,
  `--max-retries`, `--retry-delay`) are accepted but ignored (LLMFlux issue #144).
  Sampling settings only take effect in each request's `body`. Part 10 of the
  participant guide says so.
- The participant JSONL leaves `model` out of each request on purpose. LLMFlux
  rejects a request whose `body.model` doesn't exactly match the engine's internal
  name (the HuggingFace repo, for vLLM), which is a confusing error for
  first-timers. LLMFlux fills it in from `--model`.
- LLMFlux reads `~/.env` (the home directory), not a `.env` in the workshop
  folder, so `workshop.env` is a file participants `source` rather than a
  `.env` they edit. A participant with their own `~/.env` gets its settings in
  their jobs too.
