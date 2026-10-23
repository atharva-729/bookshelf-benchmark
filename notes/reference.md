# Reference: data, file formats and how to add a run

The technical detail that used to live in the README. For the overview, start with the [README](../README.md).

## Dataset

6 photos and 295 labelled books, in `data/images/`. The answer key is `data/ground_truth.json`.

| Image | Difficulty | Books |
| --- | --- | ---: |
| `a.jpg` | easy | 65 |
| `b.jpg` | easy | 49 |
| `c.png` | medium | 26 |
| `d.jpg` | medium | 8 |
| `e.jpg` | hard | 108 |
| `f.jpg` | hard | 39 |

The photos are the originals, about 4–5 MB each. `docs/photos/` holds smaller copies for the web page only; the models were always given the originals.

### How the answer key was made

1. Claude Opus 5.5 at medium effort, running in Claude Code, split each of the 11 original photos into small sections of the full-resolution image (over a hundred in all) and read the spines in each.
2. From those sections it drafted a list of books per photo. A person reviewed every book on the list against the photo and kept only those really there.
3. The photos with the most unlabelled but readable books were dropped. Keeping them would have meant checking hundreds more books, and leaving them incomplete would have counted correct model answers as hallucinations. The 5 dropped photos are in `archive/`.

Labelling rules:
- Each title appears once per photo, even if there are several copies on the shelf.
- A book is included only if its title can be read in the photo.
- Unknown authors are `null`.

**The answer key is frozen.** Don't add books just because a model claims they're present. Some real books were left out because they were too hard to confirm; see "Marked wrong, but really there" on the results page.

## File formats

### Answer key

`data/ground_truth.json` maps each image filename in `data/images/` to its difficulty and list of books. Keys match the filenames exactly, including case.

```json
{
  "d.jpg": {
    "difficulty": "medium",
    "books": [
      { "title": "Win Your Inner Battles", "author": "Darius Foroux" },
      { "title": "Fast Like a Girl", "author": "Mindy Pelz" }
    ]
  }
}
```

`difficulty` is one of `easy`, `medium` or `hard`.

### Model replies

In experiment 1, models get all 6 photos in one message and reply with one JSON object keyed by photo (`a` to `f`, without the extension). `difficulty` is optional, and `author` may be `null`.

```json
{
  "d": {
    "difficulty": "medium",
    "books": [
      { "title": "Determined", "author": "Robert Sapolsky" }
    ]
  }
}
```

In experiment 2 (one photo per chat), the reply is a single `{"books": [...]}` list.

### Reply files

Each setup has one Markdown file in a run's `replies/` folder, named `<model>__<mode>.md`. The header holds `key: value` lines (model, mode, interface, date, notes; run 2 adds timings), then the model's reply under `## Reply`, pasted unedited. The scorer finds the JSON on its own, so code fences and extra text are fine. Experiment 2 files have a `## e.jpg` and a `## f.jpg` section instead.

An empty reply means "not run yet" and is skipped.

## Repository layout

| Path | What it is |
| --- | --- |
| `data/images/` | The 6 benchmark photos |
| `data/ground_truth.json` | The answer key. Frozen. |
| `benchmark/prompts/` | `all_photos.md` (experiment 1) and `one_photo.md` (experiment 2) |
| `benchmark/evaluate.py` | Scores experiment 1 replies: precision, recall, F1, per photo and per difficulty |
| `benchmark/evaluate_single.py` | Scores experiment 2 and compares it with experiment 1 |
| `benchmark/estimate_cost.py` | API-equivalent cost estimate for run 2 |
| `benchmark/build_site.py` | Writes `docs/data.js` for the results page |
| `results/exp1-run1/` | Experiment 1, first run: `replies/`, `details/`, `summary.csv`, `per_image.csv` |
| `results/exp1-run2/` | Experiment 1, repeat run: the same, plus `usage/` (timing data) and `cost.csv` |
| `results/exp2-one-photo/` | Experiment 2: `replies/`, `details/`, `summary.csv` |
| `docs/` | The results page (GitHub Pages): `index.html`, `data.js`, `photos/` |
| `notes/` | This file, the experiment notes and the scoring rules |
| `archive/` | Material not used by the benchmark (see its README) |

## Adding a run

1. Make a new folder, for example `results/exp1-run3/replies/`, and copy the reply files from `results/exp1-run2/replies/` as templates. Clear each reply and fill in the header.
2. Run every setup as described in [experiments.md](experiments.md#how-to-run-one-experiment), pasting each reply under `## Reply`.
3. Score it with `python benchmark/evaluate.py results/exp1-run3`. Running `evaluate.py` with no argument scores every `results/exp1-*` folder.
4. The results page currently shows runs 1 and 2. To add a third, extend `benchmark/build_site.py` and the run buttons in `docs/index.html`.
