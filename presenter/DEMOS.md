# Presenter script: live demos

Three demos, one for each of the deployment strategies in `TALK.md` slide 3:
**an assistant grounded in documents, a model running as a service, and a batch
job.** The point of each is to show how that kind of tool works and what it's
suited to, not to promote the tool. Each has a goal, the steps, what to say, and a
fallback. Rehearse all three on the venue network if you can.

Lines marked **☐ VERIFY** are things to confirm in your own account before the
day. They're written as a user-level view, without admin access.

---

## 1. Illinois Chat — an assistant grounded in *your* documents (≈15 min)

**Goal:** show the difference between a general chatbot and an assistant that
answers from a specific set of documents and shows its sources. The technique is
called retrieval-augmented generation (RAG): the system finds relevant passages
first, then gives them to the model along with the question. Then share the
assistant so participants can use it during the hands-on.

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
   Point out that the answer sounds confident either way, even when it's
   generic or wrong. Models don't signal when they're guessing.
2. Switch to the grounded project and ask the same question. Point out the
   specific answer **and its citations**: you can click through and check it.
3. Ask something only the workshop docs know: *"What does `submit.sh` do, and why
   is it one job instead of three?"*
4. Ask it to write something: *"Write a new TASKS entry for make_prompts.py that
   extracts the study's limitations as a JSON list."* Keep this answer, because it's
   exactly what participants do in Part 7B of the guide.
5. Share the link: *"You can use this during the hands-on. Check its answers
   against the guide, the same way we just checked its citations."*

**What to say:** a hosted assistant suits work that's conversational and one
question at a time. Grounding it in your documents makes its answers more
relevant, and citations let you check them. They don't make it always right: it
can still misread a source, so you click through. Its limits: one conversation
at a time, on a service someone else runs, with the models they've chosen to
offer.

**Fallback:** screenshots of steps 1–4 in the slides.

---

## 2. LLMHub — open models on NCSA hardware, as a service (≈10 min)

**Goal:** show what it means to run a model as a service. LLMHub (CAII's
platform on NCSA infrastructure) starts an open model on cluster GPUs and keeps it
running, so you can chat with it in a browser or send it requests from code. The
concept to teach: the request format most tools use (OpenAI's API format) isn't
tied to one company. The same code can talk to a commercial provider or to a model
running on campus hardware, by changing the address it sends to.

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
4. **Call it from code.** Put this on a slide too:
   ```python
   from openai import OpenAI
   client = OpenAI(base_url="<deployment endpoint>/v1", api_key="<key>")
   r = client.chat.completions.create(
       model="<model name>",
       messages=[{"role": "user", "content": "Classify this abstract: ..."}])
   print(r.choices[0].message.content)
   ```
   *"That's the standard OpenAI client library. Only the address and the key
   changed. Most tools that work with OpenAI's API, including agent frameworks,
   let you change the address the same way."*
5. **Sharing** (☐ VERIFY the UI): a deployment can be shared with a colleague,
   so a lab can share one model server.
6. **Bridge to demo 3:** *"An API is right for interactive use and agents. But if
   you need that same call 50,000 times over a dataset, you want a batch job that
   starts, does the work, and gives the GPU back."*

**What to say:** a model service suits interactive use: an application, an
agent, or a script that sends requests as it goes. The cost is that it holds a
GPU the whole time it's running, whether or not anyone is using it. That's the
tradeoff the next demo addresses.

**Fallback:** screenshots of steps 1–4, plus the code snippet on a slide.

---

## 3. LLMFlux on Delta — the same kind of call, at scale (≈5 min live + reveals)

**Goal:** show what a batch job does from start to finish, before participants
run one themselves: data in a spreadsheet, a file of requests, a job in the queue,
and structured output they then check. Use the "cooking show" approach: submit at the start of the session and
reveal the result later, so nobody watches a model load.

**Right before you start talking** (in a terminal you'll put on screen later;
set up your own workspace in advance with `setup_workshop.sh`, as participants do):

```bash
source ~/llmflux-workshop/workshop.env
python make_prompts.py                    # add --dataset genomics for a bio audience,
                                          # and use the genomics-all file names below
bash submit.sh prompts/all.jsonl          # note the job ID
```

**Near the end of the talk (`TALK.md` slide 9), on screen:**

1. `head -3 data/abstracts.csv`: *"Here's our data: a spreadsheet."*
2. `head -1 prompts/all.jsonl | python -m json.tool`: *"Each row becomes a request,
   in the same format OpenAI's batch API uses."*
3. Scroll back to the `submit.sh` output and walk through what happened: *"This
   wrote a Slurm job. The job waited for a GPU, started a container, loaded the
   model, answered 48 requests, and released the GPU."*
4. `llmflux jobs --all` and `llmflux logs <id> --tail 30`: show the model load and
   the request throughput lines.
5. `python show_results.py results/all.json`: the results. Spend time on the
   **extract** section: *"This is structured data a script can use. Before we
   trust it, we check it. This line says how many replies passed the format
   checks. Next, we'll look at what those checks can't catch."*

**What to say:** it's the same kind of request you'd type in a chat window, sent
48 times (or 48,000) without anyone sitting there. A batch job uses the GPU only
while there's work, and writes output in a format you can check automatically.
The tradeoff is the wait: it queues like any other job, and loading the model
takes longer than answering. Use an assistant or a service to design the step,
and a batch job to run it over the whole dataset.

**Fallback (Delta down, or job not done):** open `sample_results/all.json` from the
dry run and run `show_results.py` on that. It's the same kind of output, from
the dry run before the session. Say so; it's still real.
