# Bookshelf Benchmark / Multimodal Information Representation Benchmark

## 1. Context

This is an innovation-team experiment at Straive. The objective is to build a small, presentable benchmark that explores how multimodal AI models perform when given real-world bookshelf photographs and asked to identify the books visible in them.

The original idea came from trying to use an LLM to identify books from photographs of chaotic bookstore/bookshelf displays. The models sometimes struggled with OCR, image quality, and hallucinated or incorrectly identified book titles.

The innovation-team lead reframed this into a benchmark:

> Given a collection of bookshelf photographs for which the actual books are known, compare how well different frontier multimodal models and different ways of interacting with those models can identify the books.

The implementation should be lightweight and completed quickly. The goal is an experimental prototype and GitHub Pages presentation, not a production application.

---

## 2. Current Dataset

The ground-truth dataset is complete and frozen.

* 6 bookshelf photographs: 2 easy, 2 medium, 2 hard.
* 295 identifiable books across the photographs.
* Each photograph has a manually curated list of books that can be identified from that image. Each title appears once per photograph, even if there are several copies.
* Unknown authors are recorded as `null`.
* The ground truth contains book titles and authors where available.
* Books that could not be deciphered confidently were intentionally excluded.

The ground truth must be treated as immutable during evaluation. Do not add books to it merely because a model claims that they are present.

The purpose of the ground truth is to provide a reference against which model outputs can be evaluated.

---

## 3. Initial Benchmark

The first experiment should compare multimodal models on the same bookshelf-identification task.

Candidate models depend on what access is available. There is no requirement to purchase additional subscriptions or APIs solely for this project.

Potential models include GPT, Gemini, Claude, or other accessible multimodal models.

The benchmark should use a standardized prompt so that the models receive substantially the same task definition.

The basic task is:

> Given a bookshelf photograph, identify every book whose title can be determined from the image.

Models should return structured JSON containing:

```json
{
  "books": [
    {
      "title": "Book Title",
      "author": "Author Name"
    }
  ]
}
```

Models should be instructed not to guess or hallucinate books that cannot be confidently identified.

---

## 4. Evaluation

The benchmark should compare model outputs against the ground truth.

Important metrics include:

### Precision

Of the books identified by the model, what proportion were actually present?

This is useful for measuring hallucinated/incorrect identifications.

### Recall

Of the books actually present in the image, what proportion did the model successfully identify?

This is especially important for the bookshelf task.

### F1 Score

A combined measure of precision and recall.

### Per-image performance

Performance should also be calculated separately for each bookshelf photograph, rather than only producing one overall score.

Example:

| Model   | Shelf 1 | Shelf 2 | Shelf 3 | Overall |
| ------- | ------: | ------: | ------: | ------: |
| Model A |     ... |     ... |     ... |     ... |
| Model B |     ... |     ... |     ... |     ... |
| Model C |     ... |     ... |     ... |     ... |

The evaluator must not rely solely on exact string matching. Minor title-formatting differences should not automatically count as incorrect if the model has clearly identified the same book.

---

## 5. Direct Model vs Harness / Agent

The innovation-team lead specifically raised the distinction between models and the systems/harnesses used to operate them.

A later experiment should compare:

1. Direct model prompting.
2. A model operated through a simple verification/agentic harness.

A possible verification workflow:

```text
Image
  ↓
Model identifies books
  ↓
Model identifies uncertain results
  ↓
Model re-inspects/crops/uses available tools if appropriate
  ↓
Final book list
```

The objective is to determine whether orchestration/verification improves identification accuracy compared with a single direct model response.

This does not require a complicated agent framework. A lightweight implementation is preferred.

---

# 6. Broader Research Question

During development, a broader and potentially more interesting research question emerged:

> Does the representation or packaging of information affect LLM performance?

The bookshelf benchmark can be treated as one concrete experiment within this larger idea.

The same underlying information could potentially be provided to an AI system in different representations:

* Individual images.
* Multiple images simultaneously.
* ZIP containing multiple images.
* PDF.
* Markdown.
* Plain text.
* DOCX.
* Other structured formats.
* Encoded representations such as base64/string representations where technically applicable.

The objective would be to determine whether changing the representation of identical information changes model behaviour.

---

## 7. ZIP vs Individual Images

One immediate experiment is:

### Condition A

Provide the 6 bookshelf images individually, either one at a time or through an API.

### Condition B

Provide all 6 images together as a ZIP/archive if the model/interface supports this.

Then compare:

* Identification accuracy.
* Precision.
* Recall.
* F1.
* Latency.
* Input/token usage where available.
* Cost where available.
* Failure rate.
* Consistency.

The hypothesis must remain open.

Do not assume that ZIP is worse than individual images. The experiment is intended to determine whether batching/packaging affects performance.

Possible explanations for performance differences include visual processing limitations, context limitations, attention across multiple images, file handling, or differences in how the interface preprocesses the input.

---

## 8. File Representation Experiment

The broader experiment can compare different representations of the same underlying information.

For example:

```text
Same information
      ↓
 ┌────┼─────┬─────┬──────┐
 PDF  MD    TXT   Images ZIP
 └────┼─────┴─────┴──────┘
      ↓
    Same model
      ↓
Performance comparison
```

The experiment should investigate whether representation affects:

* Accuracy.
* Completeness.
* Hallucination/error rate.
* Input token usage.
* Context consumption.
* Latency.
* API cost.
* Reliability/consistency.

Do not assume that one format is inherently superior. Markdown may sometimes be more convenient for an LLM than PDF, but this project should measure rather than assume such effects.

---

## 9. Image Compression Experiment

The bookshelf photographs are relatively large, approximately 4–5 MB each.

Another possible experiment is to test whether image compression changes:

* Input/token usage.
* Upload/network size.
* Processing latency.
* Identification accuracy.
* Hallucination/error rate.

Important distinction:

> File size in MB is not necessarily equivalent to model input token usage.

Different multimodal models/APIs may resize, tile, preprocess, or otherwise encode images before processing them.

Therefore, test different versions of the same image where practical:

```text
Original high-resolution image
        ↓
Moderately compressed image
        ↓
Highly compressed image
```

Then compare visual performance and resource usage.

The objective is to determine the trade-off between image quality and inference/resource requirements.

---

## 10. API vs Consumer Interface

Where API access is available, prefer API-based experiments for controlled measurements.

Consumer interfaces such as ChatGPT, Claude, or Gemini may introduce hidden system prompts, preprocessing, context handling, reasoning configurations, file handling, or other behaviour that cannot be fully controlled.

Therefore distinguish between:

* Model.
* Interface.
* API.
* Harness.
* Agent.
* Prompt/system prompt.
* Tools.

When comparing systems, document how each model was accessed.

---

## 11. Important Terminology

### Model

The underlying trained AI system, such as GPT, Gemini, Claude, or Llama.

### Interface

The mechanism through which a user interacts with a model, such as a chat application, API, SDK, or CLI.

### Harness

The surrounding orchestration system controlling how a model is used, including prompts, tools, context, retries, verification, and multi-step workflows.

### Agent

A model-based system capable of taking multiple actions/steps toward a goal, often using tools and iterative reasoning.

### Tool

An external capability available to a model/agent, such as web search, Python, databases, filesystem access, browsers, or APIs.

### Framework

Software infrastructure used to build model/agent systems, such as LangChain, LlamaIndex, AutoGen, etc.

### Inference

Running a trained model to generate an output.

### Multimodal model

A model capable of processing multiple modalities such as text and images.

### Input tokens

The tokenized representation of information supplied to the model. For multimodal inputs, the exact accounting depends on the model/API and may not correspond directly to file size.

### Latency

The time required to process the request and return the result.

---

## 12. Engineering Principles

Keep the implementation minimal.

Do not spend substantial time building infrastructure that does not improve the experiment.

Preferred architecture:

```text
data/
    images/
    ground_truth.json

results/
    raw model outputs
    evaluation results

benchmark/
    model runners
    evaluator

docs/
    index.html
```

The GitHub Pages site should be static HTML unless there is a strong reason to use a framework.

The final presentation should prioritize:

1. What was tested.
2. Dataset.
3. Models/configurations.
4. Evaluation methodology.
5. Results.
6. Failure examples.
7. Interesting observations.
8. Possible next experiments.

The benchmark should be reproducible where possible.

---

## 13. Current Immediate Objective

The immediate objective is NOT to build the entire broader file-format benchmark.

First establish the bookshelf benchmark:

1. Freeze the 6-photo / 295-book ground truth.
2. Run at least 2–3 accessible multimodal models.
3. Use a standardized prompt.
4. Save raw outputs.
5. Build an evaluator.
6. Calculate precision, recall, F1, and per-image performance.
7. Produce a simple visual results table.
8. If time permits, test direct prompting vs a lightweight verification harness.
9. Publish the results as a static GitHub Pages site.

The broader information-representation experiments should be treated as extensions of the benchmark rather than prerequisites for completing the first MVP.

---

## 14. Key Principle

The project is fundamentally an experiment about **how multimodal AI systems process and identify information under different conditions**.

Do not approach the project as an attempt to determine a universally "best" model.

Instead, measure specific capabilities and document where different approaches succeed and fail.

The goal is to produce an interesting, measurable, reproducible experiment that can be discussed with the innovation team and potentially expanded into a more general benchmark of AI information representation and processing.

---

## 15. TODO

### MVP: Bookshelf benchmark

- [x] Curate ground truth (originally 11 photographs; cut down to 6 photographs / 295 books after review. The other 5 are kept in `unused/`).
- [x] Freeze the ground truth (treat `ground_truth.json` as immutable from here on).
- [ ] Reorganise the repo into the preferred layout (`data/images/`, `data/ground_truth.json`, `results/`, `benchmark/`, `docs/`).
- [x] Write and freeze the standardized prompt (JSON output with title/author, instruction not to guess).
- [x] Run at least 2–3 accessible multimodal models (e.g. Claude, GPT, Gemini) with the standardized prompt.
- [x] Save all raw model outputs under `results/`, and record how each model was accessed (API vs consumer interface, model version, settings).
- [x] Build the evaluator with fuzzy title/author matching (not exact string match).
- [x] Calculate precision, recall and F1, both overall and per image.
- [x] Produce a per-image results table (models × shelves).
- [x] Collect failure examples (hallucinations, misreads, missed books).

### Harness experiment

- [ ] Build a lightweight verification harness (not done: needs API access. Observation recorded on the results page: the same model found nearly all books when used with zooming, multiple passes and human checks, vs ~77% on the hardest photo in one chat) (identify → flag uncertain → re-inspect/crop → final list).
- [ ] Compare direct prompting vs the harness on the same models.

### Representation / packaging experiments

- [x] Check whether model performance is the same when multiple pictures are given at once in a single prompt versus one picture per prompt.
- [ ] Compare individual images vs a ZIP of all 6 images, where supported (accuracy, latency, tokens, cost, failure rate, consistency).
- [ ] Image compression: test original vs moderately vs highly compressed images (tokens, upload size, latency, accuracy, hallucination rate).
- [ ] Test other representations of the same information (PDF, DOCX, Markdown, plain text, base64) where applicable.
- [ ] Run repeated trials to measure consistency.

### Presentation

- [x] Build the static GitHub Pages site (`docs/index.html`): what was tested, dataset, models/configurations, methodology, results, failure examples, observations, next experiments.
- [ ] Publish the site to GitHub Pages.
