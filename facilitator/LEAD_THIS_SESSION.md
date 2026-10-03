# Leading this session on short notice

For whoever runs this without having built it. If you have 30 minutes and a
Delta or DeltaAI login, you can run the demo. If you have an hour the day
before, you can run the hands-on too. Everything else is in
[`README.md`](README.md) (the full facilitator guide), [`../presenter/TALK.md`](../presenter/TALK.md)
(what to say), and [`../README.md`](../README.md) (what participants follow).

**Built by:** Josh Allen. David Bianchi or the organizers can reach him on the day.

## What you need

- [ ] An NCSA login on the system the workshop is configured for, and membership
      in the workshop's Slurm account. To check: log in and run `accounts`. The
      account named in the shared `workshop/workshop.conf` must be listed.
- [ ] The **shared folder** path (a clone of this repo on the cluster, with
      `workshop/workshop.conf` filled in). Ask whoever set it up, or check the
      facilitator guide's prep notes.
- [ ] This repo open in a browser, to put on screen and share.

## Pick a format

| Time you have | Format | Participants need |
| --- | --- | --- |
| **10–20 min**, e.g. a slot inside another session | **A. Demo on your screen.** Submit at the start, talk, show the results at the end. Use the genomics dataset in a bio-focused session. | Nothing: they watch. Share the repo link so they can try it later. |
| **The full 105-min session** | **B. Talk, demos, hands-on.** Follow the session plan in [`README.md`](README.md). | Working logins, a reservation, and a dry run done beforehand |

## Pre-flight (20 minutes, do it before the session starts)

Log in to the system from the conf (`WORKSHOP_SYSTEM`), then:

```bash
bash /SHARED/FOLDER/workshop/setup_workshop.sh      # once; safe to re-run
source ~/llmflux-workshop/workshop.env               # every login
llmflux --version                                    # prints a version
python make_prompts.py --dataset genomics            # or leave off --dataset for the general set
bash submit.sh prompts/genomics-all.jsonl            # prints the command, then "Job ID: ..."
llmflux jobs                                         # PENDING, then RUNNING
```

If setup says the workshop **isn't configured**, or that you're on the **wrong
system**, the message says what to fix. If the job reaches RUNNING, then the
software, the account, and the reservation all work. When it finishes:

```bash
python show_results.py results/genomics-all.json
```

If it fails, `llmflux logs <job id>` shows why. If there's no time to fix it, use
the dry-run results in `sample_results/` for the demo, and say that's what they are.

## Format A: the 10–20 minute demo

1. **Before you start talking:** run the `make_prompts.py` and `submit.sh` lines
   above (with a fresh job), so it's running while you talk.
2. **Talk** (pick from [`TALK.md`](../presenter/TALK.md); slides 2, 4, 5, and 10
   are the essentials):
   - Chat tools work one prompt at a time; research data comes in thousands.
   - Three ways to use an LLM on campus: a hosted assistant (Illinois Chat), a
     model service (LLMHub), and batch jobs (LLMFlux).
   - *Design interactively, run in batch.* Get the prompt right on 5 examples,
     then run it on 50,000.
   - For a genomics audience: the same pattern applies to literature triage,
     annotation notes, metadata cleanup, and pulling sample and assay details out
     of papers or sample sheets. *Not* to the sequence data itself: that's for
     domain models like the variant callers in the genomics session.
3. **Show it:** `head -3 data/genomics_abstracts.csv` (the input), then
   `head -1 prompts/genomics-all.jsonl | python -m json.tool` (one request), then
   `python show_results.py results/genomics-all.json` (the answers).
4. **Land the lesson:** point at the validation summary. *"The model's output is
   data you have to check. This script flags answers outside the allowed labels
   and JSON with missing fields. What it can't catch is a number the model made
   up, so you check a few by hand."*
5. **Close:** share the repo link. *"Everything I did is in here, step by step.
   And the LLM Flux session on Tuesday is the hands-on version."*

## Format B: the full session

Follow [`README.md`](README.md): the session plan, capacity, and the "During
the session" commands. The participant guide is written so people can work
through it mostly on their own. Your job is to unblock logins in the first 10
minutes, watch the queue, and run the debrief.

## If something breaks

| Problem | Do this |
| --- | --- |
| Job stuck PENDING with `(Reservation)` or `(ReqNodeNotAvail)` | The reservation isn't active for this account or time. Demo from `sample_results/`. |
| Job FAILED | `llmflux logs <id>`. If you can't fix it in 2 minutes, demo from `sample_results/`. |
| `llmflux: command not found` | `source ~/llmflux-workshop/workshop.env` again. |
| No network or projector | The repo's README renders on GitHub from a phone. Talk through Part 3 and Part 6 there. |
