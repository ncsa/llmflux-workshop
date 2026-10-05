# Leading this session on short notice

For whoever runs this without having built it. Everything below is filled in
for **Tuesday Oct 6, 10:00–11:45, Room 1030, on NCSA Delta**: copy the commands
as they are. With 30 minutes you can run the demo; with an hour the day before,
the hands-on too. The full facilitator guide is [`README.md`](README.md), the
talk is [`../presenter/TALK.md`](../presenter/TALK.md) (slides:
[`../presenter/slides.pdf`](../presenter/slides.pdf)), and participants follow
[`../README.md`](../README.md).

**Built by:** Josh Allen. David Bianchi or the organizers can reach him on the day.

## What's already set up

| | |
| --- | --- |
| System | **Delta**. Log in at <https://openondemand.delta.ncsa.illinois.edu/> → **Clusters** → **>_Delta Shell Access**, or `ssh YOUR_USERNAME@login.delta.ncsa.illinois.edu` |
| Shared folder | **`/projects/bccu/llmflux-workshop`**, configured and tested Oct 5 |
| Slurm account | **`bccu-delta-gpu`** (the ACCESS Delta Training project, `delta_bccu`) |
| GPUs | A reservation of 2 nodes with 4 A40 GPUs each, until **Tue 12:00**. Jobs use it automatically; nobody types its name. Other workshop sessions share it. |
| Model | Qwen2.5-7B-Instruct, already downloaded into the shared folder |
| Fallback results | `sample_results/` in the shared folder, from the dry run |
| Repo link for the room | <https://github.com/ncsa/llmflux-workshop> (QR code: `presenter/repo-qr.png`) |

**The one thing you need:** to be in the `delta_bccu` project yourself. Log in
and run `accounts`; `bccu-delta-gpu` must be in the list. If it isn't, ask Greg
Bauer to add you, and do it the day before.

## Pre-flight (20 minutes, before the session)

Log in to Delta (above), then copy these one at a time:

```bash
bash /projects/bccu/llmflux-workshop/workshop/setup_workshop.sh   # once; safe to re-run
source ~/llmflux-workshop/workshop.env                            # after every login
python make_prompts.py                                            # builds 48 requests
bash submit.sh prompts/all.jsonl                                  # prints the command, then "Job ID: ..."
squeue -u $USER -o "%.10i %.8T %.12v %R"                          # your job
```

In the `squeue` output, **RESERVATION should have a name in it**. That means
the job is on the reserved GPUs. It should go RUNNING within a minute and
finish in about 3. Then:

```bash
python show_results.py results/all.json                           # ends with "48/48 replies usable"
```

If that works, everything works: login, account, software, reservation, model.

If it fails, `llmflux logs <job id>` shows why. If there's no time to fix it,
use the dry-run results instead and say that's what they are:
`python show_results.py sample_results/all.json`.

For a bio-focused audience, use the genomics set: `python make_prompts.py --dataset genomics`,
`bash submit.sh prompts/genomics-all.jsonl`, `python show_results.py results/genomics-all.json`.

## Pick a format

| Time you have | Format | Participants need |
| --- | --- | --- |
| **10–20 min**, e.g. a slot inside another session | **A. Demo on your screen.** Submit at the start, talk, show the results at the end. | Nothing: they watch. Share the repo link so they can try it later. |
| **The full 105-min session** | **B. Talk, demos, hands-on.** Follow the session plan in [`README.md`](README.md). | Their own Delta login in `delta_bccu`, and a laptop (or a neighbor's) |

## Format A: the 10–20 minute demo

1. **Before you start talking:** run `bash submit.sh prompts/all.jsonl` again
   (or the genomics one), so a fresh job is running while you talk.
2. **Talk** (pick from [`TALK.md`](../presenter/TALK.md); slides 2, 3, 5, and 10
   are the essentials):
   - Chat tools work one prompt at a time; research data comes in thousands.
   - Three ways to run an LLM: an assistant grounded in documents (Illinois
     Chat), a model running as a service (LLMHub), and a batch job (LLMFlux).
   - *Design interactively, run in batch.* Get the prompt right on 5 examples,
     then run it on 50,000.
   - For a genomics audience: the same pattern applies to literature triage,
     annotation notes, metadata cleanup, and pulling sample and assay details out
     of papers or sample sheets. *Not* to the sequence data itself: that's for
     domain models like the variant callers in the genomics session.
3. **Show it:** `head -3 data/abstracts.csv` (the input), then
   `head -1 prompts/all.jsonl | python -m json.tool` (one request), then
   `python show_results.py results/all.json` (the answers).
4. **Checking the answers:** point at `48/48 replies usable`. *"A script checked
   the format: valid JSON, the fields are there, the labels are allowed ones.
   It can't check that an answer matches the abstract. For that you read a
   sample yourself."*
5. **Close:** share the repo link. *"Everything I did is in here, step by step."*

## Format B: the full session

Follow [`README.md`](README.md): the session plan, capacity, and the "During
the session" commands. The participant guide is written so people can work
through it mostly on their own. Your job is to unblock logins in the first 10
minutes, watch the queue, and run the debrief. Put this on screen for Part 2:

```bash
bash /projects/bccu/llmflux-workshop/workshop/setup_workshop.sh
```

To watch everyone's jobs:

```bash
squeue -A bccu-delta-gpu -o "%.10i %.10u %.8T %.12v %R"
```

## If something breaks

| Problem | Do this |
| --- | --- |
| `accounts` doesn't list `bccu-delta-gpu` | You (or that participant) aren't in `delta_bccu` yet. Ask Greg Bauer. For the demo, use `sample_results/`. |
| Job PENDING and the RESERVATION column is empty | It isn't on the reserved GPUs. Run `scontrol show res \| grep -B3 -A10 bccu-delta-gpu`: if nothing prints, the reservation has ended or doesn't exist. The job will still run in the general queue, just later. Demo from `sample_results/`. |
| Job PENDING with `(Resources)` and a reservation name | The reserved GPUs are busy, maybe with other sessions. It usually starts within a few minutes. |
| Job FAILED | `llmflux logs <id>`. If you can't fix it in 2 minutes, demo from `sample_results/`. |
| `llmflux: command not found` | `source ~/llmflux-workshop/workshop.env` again. |
| No network or projector | The repo's README renders on GitHub from a phone. Talk through Part 3 and Part 6 there. |
