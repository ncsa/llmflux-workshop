# Presenter script: live demos

Three demos, in the order of the session's arc: **talk to a model → build with
one → run one at scale on the cluster.** Each has a goal, the steps, what to say,
and a fallback. Rehearse all three on the venue network if you can.

Lines marked **☐ VERIFY** are things to confirm in your own account before the
day. They're written as a user-level view, without admin access.

---

## 1. Illinois Chat — an assistant grounded in *your* documents (≈15 min)

**Goal:** show the step from a generic chatbot to an assistant that answers from
a specific body of documents and shows its sources. This is retrieval-augmented
generation (RAG), the first thing that makes an LLM useful for research work.
Then hand participants that assistant to use during the hands-on.

**Prep (day before, not live — ingestion takes time):**

- [ ] ☐ VERIFY your account can create a project/chatbot and add documents or web pages to it.
- [ ] Create a project, e.g. **"Delta + LLMFlux helper"**, and add:
      the Delta user guide pages (Login, Running Jobs, Filesystems), the LLMFlux
      README, and this repo's `README.md` (the participant guide).
- [ ] ☐ VERIFY which models the project can use, and pick one that answers well with citations.
- [ ] ☐ VERIFY how to share it so participants can open it without your account.
      Put the link on a slide or QR code.
- [ ] Try the demo questions below and note which ones answer well.

**Live steps:**

1. Ask a general chat model a Delta-specific question it can't know,
   e.g. *"What partition should I use for A100 jobs on Delta, and what's the maximum walltime?"*
   Point out the confident but generic or wrong answer.
2. Switch to the grounded project and ask the same question. Point out the
   specific answer **and its citations**: you can click through and check it.
3. Ask something only the workshop docs know: *"What does `submit.sh` do, and why
   is it one job instead of three?"*
4. Ask it to write something: *"Write a new TASKS entry for make_prompts.py that
   extracts the study's limitations as a JSON list."* Keep this answer, because it's
   exactly what participants do in Part 7B of the guide.
5. Share the link: *"This is your helper for the next hour."*

**What to say:** a hosted assistant is the right tool when the work is
conversational and one task at a time. Grounding in your documents plus citations
is what makes it trustworthy enough for research. Its limits: you're working one
conversation at a time, on someone else's compute, with their model choices.

**Fallback:** screenshots of steps 1–4 in the slides.

---

## 2. LLMHub — open models on NCSA hardware, as a service (≈10 min)

**Goal:** the step after a hosted assistant. LLMHub (CAII's platform on NCSA
infrastructure) lets you **pick an open model, launch it on the cluster, chat with
it, share it, and call it from code** through an OpenAI-compatible API. The point
for this audience: *you* choose the model, and the same API your code would send to
a commercial provider now goes to a model running on campus hardware.

**Prep (day before):**

- [ ] ☐ VERIFY the LLMHub URL and that your account can log in on the venue network.
- [ ] ☐ VERIFY your user role can **launch** a deployment from the model library
      (or whether launching needs an admin, in which case use one that's already running).
- [ ] **Launch the deployment you'll demo before the session.** Like any cluster
      job it takes minutes to schedule and load, so don't do it live. Same
      cooking-show approach as demo 3.
- [ ] ☐ VERIFY how to get an API key/endpoint for that deployment, and test the
      snippet below against it from your laptop.

**Live steps:**

1. **Model library.** Scroll it. *"These are open models: Llama, Qwen, Mistral,
   and so on. You can see exactly which model and version you're getting."*
2. **Deployments.** Show the one you launched earlier: it's running on cluster
   GPUs, and you can see its logs. *"This is a Slurm job, like the one we'll see in
   a minute, but managed for you."*
3. **Chat** with it in the browser. Ask the same question you used in demo 1, for
   a direct comparison.
4. **Call it from code.** This is the slide-worthy moment:
   ```python
   from openai import OpenAI
   client = OpenAI(base_url="<deployment endpoint>/v1", api_key="<key>")
   r = client.chat.completions.create(
       model="<model name>",
       messages=[{"role": "user", "content": "Classify this abstract: ..."}])
   print(r.choices[0].message.content)
   ```
   *"That's the standard OpenAI client. Any agent framework or coding agent that
   can use OpenAI can be pointed here instead."*
5. **Sharing** (☐ VERIFY the UI): a deployment can be shared with a colleague,
   so a lab can share one model server.
6. **Bridge to demo 3:** *"An API is right for interactive use and agents. But if
   you need that same call 50,000 times over a dataset, you want a batch job that
   starts, does the work, and gives the GPU back."*

**What to say:** the three tools form a ladder. Illinois Chat is an assistant
that answers from your documents. LLMHub is a model service you choose and call
from code. LLMFlux is batch runs on your own allocation. They're all open models
on campus hardware.

**Fallback:** screenshots of steps 1–4, plus the code snippet on a slide.

---

## 3. LLMFlux on Delta — the same kind of call, at scale (≈5 min live + reveals)

**Goal:** show that the step participants are about to take is small. One command
turns a spreadsheet into a GPU job, and the output is structured data they can
check. Use the "cooking show" approach: submit at the start of the session and
reveal the result later, so nobody watches a model load.

**Right before you start talking** (in a terminal you'll put on screen later;
set up your own workspace in advance with `setup_workshop.sh`, as participants do):

```bash
source ~/llmflux-workshop/workshop.env
python make_prompts.py                    # add --dataset genomics for a bio audience,
                                          # and use the genomics-all file names below
bash submit.sh prompts/all.jsonl          # note the job ID
```

**Near the end of the talk (`TALK.md` slide 8), on screen:**

1. `head -3 data/abstracts.csv`: *"Here's our data: a spreadsheet."*
2. `head -1 prompts/all.jsonl | python -m json.tool`: *"Each row becomes a request,
   in the same format OpenAI's batch API uses."*
3. Scroll back to the `submit.sh` output: *"One command. It wrote a Slurm job,
   which waited for a GPU, loaded the model, answered 48 requests, and released the GPU."*
4. `llmflux jobs --all` and `llmflux logs <id> --tail 30`: show the model load and
   the request throughput lines.
5. `python show_results.py results/all.json`: the reveal. Linger on the
   **extract** section: *"This is structured data your next script can consume,
   and we validate it. Notice the line that tells us how many replies are usable."*

**What to say:** the same model call you just made in a chat window, made 48 times
(or 48,000) without anyone sitting there. It runs on your allocation, with an open
model, and writes its output in a format you can check automatically. Agents and
assistants design the step; batch runs it at scale. `llmflux serve` closes the
loop, putting an OpenAI-compatible endpoint on your allocation that agent tools
can point at.

**Fallback (Delta down, or job not done):** open `sample_results/all.json` from the
dry run and run `show_results.py` on that. It's the same output, made a week
earlier. Say so; it's still real.
