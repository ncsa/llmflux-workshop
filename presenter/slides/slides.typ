// LLMFlux talk, NCSA AI/HPC Regional Workshop, Oct 6 2026.
// Build:   typst compile slides.typ        (makes slides.pdf)
// Preview: tinymist preview slides.typ     (or: typst watch slides.typ)
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#import "dna.typ": dna

// ---- The "master slide": size, margins, DNA strip, slide number ----------
#set page(width: 28cm, height: 15.75cm,
  // Content starts right of the DNA strip.
  margin: (left: 4.6cm, right: 1.2cm, top: 0.9cm, bottom: 1.2cm),
  background: place(left + top, dx: 1cm, dy: 0.1cm, dna()),
  footer: context align(right, text(14pt, counter(page).display())))
#set text(font: "Liberation Serif", size: 21pt)
#set list(marker: [•], indent: 0.3cm, body-indent: 0.5cm, spacing: 0.9em)
// Second-level bullets are a bit smaller.
#show list: it => { show list: set text(0.85em); show list: set block(above: 0.5em); it }
#show raw: set text(font: "DejaVu Sans Mono")
#show link: set text(fill: rgb("#1a5fb4"))

// ---- Layouts --------------------------------------------------------------
// A title and content.
#let slide(title, body, size: 21pt) = {
  pagebreak(weak: true)
  align(center, text(33pt, title))
  v(0.7cm)
  set text(size)
  body
}
// Bullets on the left, a picture on the right.
#let beside(body, picture, width: 40%, align-picture: horizon) = grid(
  columns: (1fr, width), column-gutter: 0.8cm,
  align: (left + top, center + align-picture),
  body, picture)

// ---- 1. Title -------------------------------------------------------------
#align(center)[
  #text(33pt)[LLMFlux: Batch Processing with LLMs]
  #v(2.2cm)
  Joshua Allen \
  Senior Research Programmer, NCSA Genomics \
  10/6/2026 \
  NCSA AI/HPC Regional Workshop
]
#place(bottom + left, stack(dir: ltr, spacing: 0.3cm,
  image("images/ilogo.png", height: 1.1cm),
  align(horizon, text(13pt, font: "Liberation Sans", weight: "bold",
    fill: rgb("#13294b"))[NCSA #h(0.15cm) | #h(0.15cm) ILLINOIS])))

// ---- 2. ---------------------------------------------------------------------
#slide[How AI is used Practically today][
  - Annotate thousands of photos from the web site
  - Protein structure prediction (AlphaFold)
  - Generate synthetic data (hundreds of records for each of millions of patients)
  - Analyze thousands of imaging files and make diagnostic predictions
  - Assist RSEs in writing \ research software
  #place(bottom + right, image("images/alphafold_image.jpg", width: 11cm))
]

// ---- 3. ---------------------------------------------------------------------
#slide[File after File after File etc.][
  #beside(width: 38%, align-picture: bottom)[
    - Genomics Data
      #grid(columns: 2, column-gutter: 2.5cm)[
        - Reads data
        - BAMs
      ][
        - Vcf
        - BigWig
      ]
    - Financial Records
    - Survey Forms
    - Patient Records
    - Scan Data
      - CAT
      - MRI
  ][#image("images/files_stock.png")]
]

// ---- 4. ---------------------------------------------------------------------
#slide[LLM services (at UIUC)][
  #beside(width: 38%, align-picture: top)[
    - Illinois Chat
      - Ask a model direct questions
      - Get answers with citations
    - LLMHub
      - Always on chat models that you interact with via API or a Frontend
      - Arbitrary models, several model styles
    - LLMFlux
      - Runs in the background, applies the same process to many inputs at
        once, then releases the GPU
  ][#image("images/illinois_chat_screenshot.png")]
]

// ---- 5. ---------------------------------------------------------------------
#let you = rgb("#e8eef6")      // your steps
#let flux = rgb("#fde6d8")     // the step LLMFlux runs
#let step(body) = text(17pt, body)
#let cmd(body) = text(font: "DejaVu Sans Mono", size: 14pt, body)
// Labels under the groups: same height, top-aligned, so they line up.
#let who(body) = box(height: 3.4em, align(center + top, body))

#slide[Enter Batch Processing][
  #v(1fr)
  #align(center, diagram(
    spacing: (0.55cm, 0.6cm),
    node-stroke: 1pt,
    node-corner-radius: 4pt,
    node-inset: 8pt,
    edge-stroke: 1pt,
    mark-scale: 80%,

    // The pipeline
    node((0, 0), step[Your data \ #text(15pt)[CSV, text]], fill: you, name: <data>),
    node((1, 0), step[Prompts \ #text(15pt)[JSONL]], fill: you, name: <prompts>),
    node((2, 0), step[Model \ #text(15pt)[on a GPU]], fill: flux, name: <model>),
    node((3, 0), step[Answers \ #text(15pt)[JSON]], fill: you, name: <answers>),
    node((4, 0), step[Checks], fill: you, name: <checks>),
    node((5, 0), step[Analysis], fill: you, name: <analysis>),
    edge(<data>, <prompts>, "-|>"),
    edge(<prompts>, <model>, "-|>"),
    edge(<model>, <answers>, "-|>"),
    edge(<answers>, <checks>, "-|>"),
    edge(<checks>, <analysis>, "-|>"),

    // Who does each part
    node(enclose: (<data>, <prompts>), stroke: (paint: gray, dash: "dashed"),
      inset: 8pt, corner-radius: 8pt),
    node(enclose: (<model>,), stroke: (paint: rgb("#d9622b"), dash: "dashed"),
      inset: 8pt, corner-radius: 8pt),
    node(enclose: (<answers>, <checks>, <analysis>), stroke: (paint: gray, dash: "dashed"),
      inset: 8pt, corner-radius: 8pt),

    node((0.5, 1.3), stroke: none, who[*You* \ #cmd[make_prompts.py]]),
    node((2, 1.3), stroke: none, who[*LLMFlux* \ #cmd[llmflux run]]),
    node((4, 1.3), stroke: none,
      who[*You* \ #cmd[show_results.py] \ #text(16pt)[then your usual tools]]),
  ))
  #v(1fr)
  #align(center, text(20pt)[LLMFlux: #link("https://github.com/Center-for-AI-Innovation/llmflux")])
  #v(1fr)
]

// ---- 6. ---------------------------------------------------------------------
#slide[Design Interactively, Run in Batch][
  - Set up the prompt interactively on a chat for a subset of examples
  - Translate the prompt to JSONL
  - Process 50,000 samples in one go in bulk
]

// ---- 7. ---------------------------------------------------------------------
#slide[Under the Hood][
  #align(center, text(18pt)[login node → Slurm → GPU node → results])
  #v(0.2cm)
  - SLURM assigns GPU
  - Container with the software embedded starts on GPU node
  - Inference engine (vLLM) loads the weights in GPU memory
  - Each request is processed by the model
  - Answers written out in JSON
  - GPU node released
  #place(bottom + right, image("images/Delta_stock_image.png", width: 8cm))
]

// ---- 8. ---------------------------------------------------------------------
#slide[Why LLMFlux][
  - All the previous can be done manually:
    - Build a Slurm script
    - Find, build, load a container
    - Start an inference engine
    - Query the engine for updates
    - Set up automatic retries
    - Partial progress save on failure
  - Or you can run a single command:
    - `llmflux run --model Qwen2.5-7B-Instruct --input prompts.jsonl`
]

// ---- 9. ---------------------------------------------------------------------
#slide(size: 18pt)[How do I fine-tune the results][
  - Training on labeled data and fine-tuning is an iterative and expensive
    process. Try these methods first:
    - Prompt tuning – rewrite the prompt with a couple of examples on the same
      data, try in a chat window first
    - Give the model full reference text – model input is much cheaper than
      model output
    - Change model – A larger or more specialized model may work better on
      your data than a smaller general purpose model
  - If those fail, then may want to fine-tune the model:
    - Train a model on your own labeled examples
    - Requires data, separate training methods
    - Pass new Model into LLMFlux via a custom config
]

// ---- 10. --------------------------------------------------------------------
#slide[Results][
  #beside(width: 34%, align-picture: top)[
    - Most of the compute time is loading the model
    - Once the model is loaded, it takes only minutes to process many input files
    - Batch submission is very efficient
  ][
    #image("images/relevant_xkcd_comic.png", height: 8.5cm)
    #text(10pt)[xkcd by Randall Munroe, CC BY-NC 2.5]
  ]
]

// ---- 11. --------------------------------------------------------------------
#slide[Analyzing the Output][
  - 48/48 replies usable
  - Format Checks
    - Checking if it's a valid JSON, requested output appears
    - Can be done programmatically
  - Correctness Checks
    - p09 - The method actually contains text from the abstract
    - p06 – Null passed as a string
]

// ---- 12. --------------------------------------------------------------------
#slide[Try it for yourself!][
  - Interactive demo: #link("https://github.com/ncsa/llmflux-workshop")
  #v(0.4cm)
  #align(center, image("images/repo-qr.svg", height: 6.5cm))
]
