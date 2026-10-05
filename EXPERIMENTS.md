# Experiment 1: models × modes

## What we're trying to find out

Given the same 6 bookshelf photos and the same prompt, how well do different AI models identify the books? And does turning on more thinking or reasoning change the result?

We're not trying to crown one "best" model. We want to see where each setup succeeds and fails: easy vs hard shelves, books missed vs books made up, and whether extra thinking helps. This is the first experiment in the project; see [PROJECT_BRIEF.md](PROJECT_BRIEF.md) for the rest.

## Setup

- **Photos:** the 6 images in `data/`: 2 easy, 2 medium and 2 hard, with 295 books in total. The answer key is `ground_truth.json`; see [README.md](README.md) for how it was made.
- **Prompt:** the same text for every run, in [benchmark/prompt.md](benchmark/prompt.md). All 6 photos are sent **together in one message**, and the model returns one JSON object with a book list for each photo (`a` to `f`). It asks for every book whose title can be read, with no guessing.
- **Interface:** the normal consumer chat apps (ChatGPT, Claude.ai and Gemini), not the APIs. That's closer to how people actually use these tools. It also means each app may resize images or add hidden instructions we can't see or control. Keep that in mind when reading the results.

## The experiments

Each experiment is one model in one mode, given all 6 photos at once. There are 12 in total. Each has its own file in `results/raw/`, where you paste the reply.

| Model | Modes | Files |
| --- | --- | --- |
| GPT 5.6 Luna | standard, thinking | [standard](results/raw/gpt-5.6-luna__standard.md), [thinking](results/raw/gpt-5.6-luna__thinking.md) |
| Claude Opus 5.5 | low, high | [low](results/raw/claude-opus-5.5__low.md), [high](results/raw/claude-opus-5.5__high.md) |
| Claude Sonnet 5.5 | low, high | [low](results/raw/claude-sonnet-5.5__low.md), [high](results/raw/claude-sonnet-5.5__high.md) |
| Claude Opus 5 | high | [high](results/raw/claude-opus-5__high.md) |
| Claude Sonnet 5 | high | [high](results/raw/claude-sonnet-5__high.md) |
| Gemini 3.8 Flash | standard, extended thinking | [standard](results/raw/gemini-3.8-flash__standard.md), [extended thinking](results/raw/gemini-3.8-flash__extended-thinking.md) |
| Gemini 3.1 Pro | standard, extended thinking | [standard](results/raw/gemini-3.1-pro__standard.md), [extended thinking](results/raw/gemini-3.1-pro__extended-thinking.md) |

Why these Claude runs:
- **Opus 5.5 and Sonnet 5.5 at low and high effort:** shows whether more effort helps, and how the top model compares with the cheaper one at the same effort. This mirrors the Gemini setup (two models, each with less and more thinking).
- **Opus 5 and Sonnet 5 at high effort:** shows whether the newer generation improved. Effort is fixed, so any difference comes from the model.
- **Medium effort is left out:** low vs high gives the clearest signal. If they differ a lot, medium can be added later.

If a mode doesn't exist for a model, or you decide to skip it, leave its file empty. The script ignores empty files.

## How to run one experiment

1. **Open the experiment's file** in `results/raw/`. Fill in `date`, and anything unusual under `notes` (for example "Gemini asked a follow-up question" or "had to retry once").
2. **Start a new chat** and pick the model and mode.
3. **Attach all 6 images** from `data/` in order (`a.jpg` to `f.jpg`). Use the original files, not screenshots.
4. **Paste the prompt** from [benchmark/prompt.md](benchmark/prompt.md) into the same message and send it.
5. **Copy the model's whole reply** and paste it under `## Reply` in the file. Include any extra text or code fences; the script finds the JSON on its own.
6. **Don't edit or fix the reply.** Broken JSON, or a photo left out of the JSON, is part of the result. Those photos are scored as if the model found no books.

A few things keep the runs comparable:
- If possible, turn off memory, custom instructions and personalisation in each app.
- If an app asks a question instead of answering, reply "Please follow the instructions and reply with the JSON only." once, and note it in `notes`.
- If a reply is cut off or errors out, retry once in a new chat and note it.

Experiments with an empty reply are skipped, so you can fill them in one at a time.

## Scoring the results

From the repo folder, run:

```
python benchmark/evaluate.py
```

It needs Python 3 only, with no packages to install. You can run it as often as you like, for example after every experiment you fill in. It prints one row per experiment, best F1 first:

```
experiment                                  P      R     F1   easy    med   hard   auth
<model>__<mode>                           ...    ...    ...    ...    ...    ...    ...
```

If a model left photos out of its JSON, the row says how many.

It also writes:
- `results/summary.csv`: one row per experiment
- `results/per_image.csv`: one row per experiment × photo
- `results/details/<experiment>.json`: exactly which books were matched, missed, or named but not in the answer key. Use these for failure examples.

## What gets measured

The main scores are **precision** (of the books the model named, how many are really there), **recall** (of the books there, how many it found) and **F1** (the two combined). These are reported overall, per photo and per difficulty level. The script also reports **author accuracy**, whether the reply could be read, how many photos were **missing** from it, and **duplicates**.

Titles are matched approximately, so small differences in wording or punctuation don't count as wrong. The full definitions and matching rules are in [METRICS.md](METRICS.md).

## Things to keep in mind when reading the results

- **One run each:** chat models vary from run to run, so small gaps between experiments may be noise. Running the same experiment again is a later experiment (consistency).
- **All photos in one message:** the model has to keep 6 photos apart. A book listed under the wrong photo counts as both a miss and a "not in the answer key" error. Experiment 2 below compares this with one photo per chat on the hard photos.
- **Photo letters can be shifted:** the Claude app doesn't seem to show the model the filenames, so Claude lettered the photos in a different order (for example, its `a` list was really photo `d`). The script detects this and corrects it before scoring, and reports it in the `relabelled` column. See [METRICS.md](METRICS.md#photo-labels).
- **Not in the answer key ≠ made up:** a book counted against precision might be real but too hard for a person to read. Check the details file before calling something a hallucination.
- **Consumer apps, not APIs:** results describe "model X in app Y on this date". The apps may change without notice, so record the date.
- **Don't change the answer key** because of what a model says. It's frozen.

---

# Experiment 1, run 2: repeat run and cost estimate

## Why

To estimate cost (the chat apps show no token counts) we needed timing and usage data, and the original chats weren't kept. So all 12 setups were run again on 2026-10-04 with the same prompt and photos. This also gives a first look at run-to-run variation.

## How it was run

A coding agent (Claude Code with the Claude in Chrome extension, in Brave) drove the chat apps: it opened an incognito/temporary chat, set the model and mode, attached the six photos in order, pasted [benchmark/prompt.md](benchmark/prompt.md) and saved the reply exactly as the app's Copy button gave it. It also read each app's own conversation data to confirm the model and setting, and to record thinking and reply timestamps.

- Replies: `results/raw_run2/<model>__<mode>.md` (header has the send time, latency and thinking notes).
- Usage data per run: `results/raw_run2/usage/*.json` (Claude and ChatGPT; Gemini exposes nothing beyond the page).
- Scores: `python benchmark/evaluate.py results/raw_run2 results/run2`.
- Cost: `python benchmark/estimate_cost.py` → `results/run2/cost.csv`.

Notes from the run:
- Gemini 3.8 Flash with extended thinking failed once ("Sorry, something went wrong") and was retried in a new chat, as in experiment 2.
- ChatGPT (Go plan) ran Python OCR on the photos even in standard mode (11 code calls), and its Think mode was served by a different model, `gpt-5-6-t-mini`, rather than `gpt-5-6`. Think mode took 17 minutes.
- Claude hides the thinking text but records how long it thought (Opus 5.5 high: 65 s, Opus 5 high: 115 s, Sonnet 5 high: 66 s, Sonnet 5.5 high: 35 s; low effort: no thinking).

## How cost is estimated

It's the API-equivalent cost of the same request at list prices, as a low / mid / high range:
- **Input:** prompt + six photos, by each provider's image-token rule (Claude: w×h/750 after resizing to ≤2576 px, ≤4,784 per image; Gemini 3: 1,120 per image; GPT-5.x: one token per 32×32 patch of the image as ChatGPT stored it).
- **Output:** reply tokens (characters ÷ 3.5) plus thinking. Claude: thinking seconds × the same run's reply-writing speed. Gemini extended: extra seconds over the standard run × the standard run's speed. GPT: visible code and reasoning, plus unknown hidden reasoning (range 0 to latency × 50 tok/s), with the loop re-reading the images every turn.
- Hidden system prompts the apps add are not counted. Both GPT modes are priced at the GPT-5.6 Luna rate (an assumption).

## Results

| Run | F1 run 1 → run 2 | Est. cost (mid) |
| --- | ---: | ---: |
| Claude Opus 5.5, high | 0.856 → 0.886 | $0.31 |
| Claude Opus 5.5, low | 0.717 → **0.869** | $0.17 |
| Claude Opus 5, high | 0.834 → 0.837 | $0.45 |
| Claude Sonnet 5.5, high | 0.799 → 0.807 | $0.13 |
| Claude Sonnet 5.5, low | 0.726 → 0.704 | $0.07 |
| Claude Sonnet 5, high | 0.582 → 0.662 | $0.15 |
| Gemini 3.8 Flash, extended thinking | 0.704 → 0.694 | $0.09 |
| Gemini 3.8 Flash, standard | 0.687 → 0.618 | $0.02 |
| Gemini 3.1 Pro, extended thinking | 0.610 → 0.654 | $0.07 |
| Gemini 3.1 Pro, standard | 0.596 → 0.643 | $0.05 |
| GPT 5.6 Luna, thinking | 0.450 → 0.592 | $0.03 |
| GPT 5.6 Luna, standard | 0.474 → 0.569 | $0.02 |

- **Variation between runs is large.** Opus 5.5 at low effort jumped by 0.15 F1. One run per setting can mislead.
- **Extra effort pays off unevenly.** +0.01–0.02 F1 for Opus 5.5, Gemini 3.1 Pro and GPT; +0.10 for Sonnet 5.5 and +0.08 for Gemini 3.8 Flash.
- The results page plots F1 against estimated cost (log scale) for run 2.

---

# Experiment 2: one photo per chat (hard photos)

## What we're trying to find out

In experiment 1, every model was far more precise than complete on the hard photos: what they listed was almost always right, but they listed too few books. On `e` (108 books), most runs found under half, and every Gemini run stopped at about 20–27 books.

Does a model list more books when it gets **one photo at a time** instead of all 6 at once? If it does, sending everything together was holding it back: the model was rationing its answer across 6 photos, or cutting it short.

## Setup

- **Photos:** only the two hard ones, `e.jpg` (108 books) and `f.jpg` (39 books). They have the most room for improvement.
- **Runs:** the same 12 model × mode combinations as experiment 1, each on both photos. That's **24 chats**.
- **Prompt:** [benchmark/prompt_single.md](benchmark/prompt_single.md). It has the same rules as the standard prompt, minus the parts about several photos, and asks for a single `{"books": [...]}` list.
- **Replies:** `results/raw_single/<model>__<mode>.md`. There's one file per run, with a section for `e.jpg` and one for `f.jpg`.

## How to run it

For each of the 12 files in `results/raw_single/`:
1. Fill in `date` (and `notes` if anything unusual happens).
2. **New chat**, same model and mode as the file name. Attach only `e.jpg`, paste the prompt from [prompt_single.md](benchmark/prompt_single.md), and send it. Paste the whole reply under `## e.jpg`.
3. **Another new chat.** Do the same with `f.jpg`, and paste the reply under `## f.jpg`.

Use incognito or temporary chats and the same app settings as in experiment 1, so the only thing that changes is one photo instead of six.

## Scoring

```
python benchmark/evaluate_single.py
```

For each run and photo, it shows the all-at-once result (taken from experiment 1) next to the one-photo result: books listed, recall, precision and F1, plus the change. Sections you haven't filled in yet are skipped. Output goes to `results/single/summary.csv` and `results/single/details/`.

A clear rise in books listed and recall, with precision holding, means batching was limiting the models. No change means the limit is how well each model reads a crowded shelf.

## Results

9 of the 12 runs were done:
- **Gemini 3.8 Flash, extended thinking:** dropped because it kept giving trouble in the Gemini app.
- **GPT 5.6 Luna, standard and thinking:** dropped because ChatGPT also kept giving trouble on these runs, and it had the lowest scores in experiment 1.

The reason is recorded in each of those files.

### Both hard photos combined (147 books)

| Run | Books found: all at once → one per chat | Recall | Precision | F1 | F1 change |
| --- | ---: | ---: | ---: | ---: | ---: |
| Claude Opus 5.5, high | 110 → 112 | 0.75 → 0.76 | 0.96 → 0.95 | 0.840 → 0.845 | +0.006 |
| Claude Opus 5.5, low | 69 → **114** | 0.47 → **0.78** | 0.96 → 0.91 | 0.630 → 0.838 | **+0.208** |
| Claude Opus 5, high | 99 → 105 | 0.67 → 0.71 | 0.95 → 0.92 | 0.789 → 0.805 | +0.016 |
| Claude Sonnet 5.5, high | 90 → 101 | 0.61 → 0.69 | 0.96 → 0.96 | 0.747 → 0.802 | +0.055 |
| Claude Sonnet 5.5, low | 74 → 95 | 0.50 → 0.65 | 0.88 → 0.86 | 0.641 → 0.736 | +0.096 |
| Claude Sonnet 5, high | 63 → 77 | 0.43 → 0.52 | 1.00 → 0.95 | 0.600 → 0.675 | +0.075 |
| Gemini 3.1 Pro, extended thinking | 37 → 36 | 0.25 → 0.24 | 0.76 → 0.84 | 0.378 → 0.379 | +0.001 |
| Gemini 3.8 Flash, standard | 26 → 31 | 0.18 → 0.21 | 0.79 → 0.91 | 0.289 → 0.343 | +0.054 |
| Gemini 3.1 Pro, standard | 26 → 29 | 0.18 → 0.20 | 0.81 → 0.88 | 0.291 → 0.322 | +0.032 |
| **All Claude runs** | | 0.57 → **0.68** | 0.95 → 0.92 | 0.714 → **0.786** | +0.072 |
| **All Gemini runs** | | 0.20 → 0.22 | 0.78 → **0.87** | 0.321 → 0.348 | +0.027 |

### Recall per photo, all at once → one per chat

| Run | `e` (108 books) | `f` (39 books) |
| --- | --- | --- |
| Claude Opus 5.5, high | 0.77 → 0.79 | 0.69 → 0.69 |
| Claude Opus 5.5, low | 0.44 → **0.79** | 0.56 → 0.74 |
| Claude Opus 5, high | 0.69 → 0.74 | 0.62 → 0.64 |
| Claude Sonnet 5.5, high | 0.62 → 0.71 | 0.59 → 0.62 |
| Claude Sonnet 5.5, low | 0.48 → 0.62 | 0.56 → 0.72 |
| Claude Sonnet 5, high | 0.47 → 0.52 | 0.31 → **0.54** |
| Gemini 3.1 Pro, extended thinking | 0.20 → 0.20 | 0.38 → 0.36 |
| Gemini 3.8 Flash, standard | 0.16 → 0.20 | 0.23 → 0.23 |
| Gemini 3.1 Pro, standard | 0.16 → 0.16 | 0.23 → 0.31 |

### Findings

1. **Sending all 6 photos together held Claude back, especially at low effort.** Every Claude run found at least as many books with one photo per chat. Overall Claude recall rose from 0.57 to 0.68, and precision barely moved (0.95 → 0.92).
2. **The gain is biggest where the model had the least room.** Opus 5.5 at low effort went from 0.47 to 0.78 recall, the same level as Opus 5.5 at high effort, which barely changed (0.75 → 0.76). Low effort plus 6 photos made the model cut its answer short.
   - **Revises experiment 1:** most of the gap between low and high effort there came from the 6-photo setup, not the effort setting.
3. **Gemini's limit is its reading, not the batching.** Sent alone, Gemini still listed only about 19–25 books on `e`, and recall barely moved (0.20 → 0.22). What improved was precision (0.78 → 0.87): with one photo it named fewer wrong books.
4. **Claude's lead on crowded shelves grows.** With one photo, the weakest Claude run (Sonnet 5, recall 0.52) finds about twice as many books as the best Gemini run (0.24).

### Caveats

- **One run each:** changes of about ±0.05 could be normal run-to-run variation. The large jumps (Opus 5.5 low, Sonnet 5.5 low, Sonnet 5 on `f`) are well beyond that.
- **Some books counted as wrong are real.** Several books left out of the ground truth because they were hard to confirm were found repeatedly: *Farm Boy*, *COVID-19* (Michael Mosley), *The Secret Life of Bees*, *The Bitcoin Standard* and *Jiggy McCue*. Precision is slightly understated as a result, in both setups alike.
