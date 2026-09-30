# bookshelf-benchmark

A small benchmark for testing how well vision-language models can read book spines. Each image is a photo of a bookshelf. The task is to list every book visible in it, with title and author.

For the full project goals and planned experiments, see [PROJECT_BRIEF.md](PROJECT_BRIEF.md).

## Contents

| Path | What it is |
| --- | --- |
| `data/` | The 6 benchmark photos |
| `ground_truth.json` | Hand-labelled books for each photo, plus a difficulty rating. **Frozen.** |
| `claude_sonnet_5_5_*.json` | Model predictions, one file per model/setting (from before the dataset was cut down; they still cover all 11 original photos) |
| `unused/` | The 5 photos dropped from the benchmark, and their draft labels |
| `bookshelf photos.zip` | Archive of all 11 original photos |

## Dataset

6 images and 295 labelled books in total.

| Image | Difficulty | Books |
| --- | --- | ---: |
| `a.jpg` | easy | 65 |
| `b.jpg` | easy | 49 |
| `c.png` | medium | 26 |
| `d.jpg` | medium | 8 |
| `e.jpg` | hard | 108 |
| `f.jpg` | hard | 39 |

### How the ground truth was made

1. Books were first labelled by hand for 11 photos.
2. Each photo was then checked shelf by shelf with zoomed-in crops. Every proposed addition or correction was confirmed by a person against a crop of the photo.
3. The photos with the most unlabelled but readable books were dropped. Keeping them would have meant checking hundreds more books, and leaving them incomplete would have counted correct model answers as hallucinations.

Labelling rules:
- Each title appears once per photo, even if there are several copies on the shelf.
- A book is included only if its title can be read in the photo.
- Unknown authors are `null`.

The ground truth is frozen. Don't add books just because a model claims they're present.

## File formats

### Ground truth

`ground_truth.json` maps each image filename in `data/` to its difficulty and list of books. Keys match the filenames exactly, including case.

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

### Predictions

Models get all 6 photos in one message and reply with one JSON object keyed by photo (`a` to `f`, without the extension). `difficulty` is optional, and `author` may be `null`.

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

Each reply is pasted, unedited, into its experiment's file in `results/raw/`.

## Running the benchmark

- [EXPERIMENTS.md](EXPERIMENTS.md): what we're testing (models × modes), and step-by-step instructions for running it in the chat apps.
- [benchmark/prompt.md](benchmark/prompt.md): the standard prompt.
- `results/raw/`: one file per experiment, where the model replies are pasted.
- `python benchmark/evaluate.py`: scores everything pasted so far. See [METRICS.md](METRICS.md) for what it measures.
- Experiment 2 (one photo per chat, hard photos only): [benchmark/prompt_single.md](benchmark/prompt_single.md), replies in `results/raw_single/`, scored with `python benchmark/evaluate_single.py`. See [EXPERIMENTS.md](EXPERIMENTS.md).
