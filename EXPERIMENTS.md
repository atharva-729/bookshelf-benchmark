# Experiment 1: models × modes

## What we're trying to find out

Given the same 6 bookshelf photos and the same prompt, how well do different AI models identify the books? And does turning on more thinking or reasoning change the result?

We're not trying to crown one "best" model. We want to see where each setup succeeds and fails: easy vs hard shelves, books missed vs books made up, and whether extra thinking helps. This is the first experiment in the project; see [PROJECT_BRIEF.md](PROJECT_BRIEF.md) for the rest.

## Setup

- **Photos:** the 6 images in `data/`: 2 easy, 2 medium and 2 hard, with 295 books in total. The answer key is `ground_truth.json`; see [README.md](README.md) for how it was made.
- **Prompt:** the same text for every run, in [benchmark/prompt.md](benchmark/prompt.md). All 6 photos are sent **together in one message**, and the model returns one JSON object with a book list for each photo (`a` to `f`). It asks for every book whose title can be read, with no guessing.
- **Interface:** the normal consumer chat apps (ChatGPT, Claude.ai and Gemini), not the APIs. That's closer to how people actually use these tools. It also means each app may resize images or add hidden instructions we can't see or control. Keep that in mind when reading the results.

## The experiments

Each experiment is one model in one mode, given all 6 photos at once. There are 18 in total. Each has its own file in `results/raw/`, where you paste the reply.

| Model | Modes | Files |
| --- | --- | --- |
| GPT 5.6 Luna | standard, thinking | [standard](results/raw/gpt-5.6-luna__standard.md), [thinking](results/raw/gpt-5.6-luna__thinking.md) |
| Claude Opus 5.5 | low, medium, high | [low](results/raw/claude-opus-5.5__low.md), [medium](results/raw/claude-opus-5.5__medium.md), [high](results/raw/claude-opus-5.5__high.md) |
| Claude Opus 5 | low, medium, high | [low](results/raw/claude-opus-5__low.md), [medium](results/raw/claude-opus-5__medium.md), [high](results/raw/claude-opus-5__high.md) |
| Claude Sonnet 5.5 | low, medium, high | [low](results/raw/claude-sonnet-5.5__low.md), [medium](results/raw/claude-sonnet-5.5__medium.md), [high](results/raw/claude-sonnet-5.5__high.md) |
| Claude Sonnet 5 | low, medium, high | [low](results/raw/claude-sonnet-5__low.md), [medium](results/raw/claude-sonnet-5__medium.md), [high](results/raw/claude-sonnet-5__high.md) |
| Gemini 3.8 Flash | standard, extended thinking | [standard](results/raw/gemini-3.8-flash__standard.md), [extended thinking](results/raw/gemini-3.8-flash__extended-thinking.md) |
| Gemini 3.1 Pro | standard, extended thinking | [standard](results/raw/gemini-3.1-pro__standard.md), [extended thinking](results/raw/gemini-3.1-pro__extended-thinking.md) |

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
- **All photos in one message:** the model has to keep 6 photos apart. A book listed under the wrong photo counts as both a miss and a "not in the answer key" error. Comparing this with one photo per message is a later experiment (see the brief).
- **Not in the answer key ≠ made up:** a book counted against precision might be real but too hard for a person to read. Check the details file before calling something a hallucination.
- **Consumer apps, not APIs:** results describe "model X in app Y on this date". The apps may change without notice, so record the date.
- **Don't change the answer key** because of what a model says. It's frozen.
