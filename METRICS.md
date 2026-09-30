# Metrics

What `benchmark/evaluate.py` calculates, and how.

## Matching a model's answer to the ground truth

Models rarely write a title exactly like the ground truth does ("Attack on Titan Omnibus" vs "Attack on Titan: Omnibus (Volumes 1-2-3)"). So each predicted title is compared to each ground-truth title for that image, and they count as the **same book** if they're similar enough.

1. **Normalise both titles:** lowercase, drop accents on Latin letters (é → e), turn `&` into "and", and replace punctuation with spaces. Non-Latin scripts such as Devanagari are kept as they are.
2. **Compare several versions of each title:** the full title, the main title (the part before `:`, `(` or `/`), the subtitle (the part after `:`), and each of those without a leading "The", "A" or "An". The subtitle version lets "Disgusting Digestion" match "Horrible Science: Disgusting Digestion".
3. **Score the pair:** the similarity is the best score across those versions, using Python's `difflib.SequenceMatcher` (0 to 1). The comparison is also run with the words sorted, so word order doesn't matter ("Racine: Modern Judgements" = "Modern Judgements: Racine").
   - If one title is the **start or the end** of the other and has at least 3 words, the pair scores 0.90. That covers a model leaving out a subtitle ("Attack on Titan Omnibus"), or adding or dropping a series or publisher name ("Penguin Parallel Text Spanish Short Stories 1", "Dictionary of Art and Artists").
   - Shorter overlaps don't count, so "You Can" doesn't match "You Can Win".
4. **Threshold:** a pair counts as a match if its score is at least **0.85**.
5. **One-to-one:** each predicted book can match at most one ground-truth book, and the other way round. The highest-scoring pairs are matched first.
6. **Duplicates:** if a model lists the same title twice, the repeat is removed before matching. It isn't counted as right or wrong. How many were removed is reported.

Authors don't affect whether a book matches. They're scored separately (see below).

## Photo labels

All 6 photos are sent in one message, and the model labels its lists `a` to `f`. Some chat apps don't show the model the filenames, so it letters the photos in the order it received them, which may not be `a` to `f`. The Claude app did this: every Claude reply had correct lists under shifted letters.

So before scoring, the script finds the one-to-one letter → photo assignment that matches the most books. If that beats the letters as written, it uses that assignment and reports it in the `relabelled` column (for example `a->d b->e ...`). Only whole lists move: a single book listed under the wrong photo still counts as a miss and as "not in the ground truth". `per_image.csv` and the details files show which letter each photo's list came from (`reply_label`).

The thresholds are constants at the top of `evaluate.py`. Every match and non-match is written to `results/details/<experiment>.json`, so you can check the matching by hand.

## Counts per image

| Term | Meaning |
| --- | --- |
| **TP** (true positive) | A predicted book that matched a ground-truth book |
| **FP** (false positive) | A predicted book that matched nothing in the ground truth |
| **FN** (false negative) | A ground-truth book the model didn't list |

**About FP:** an FP means "not in the ground truth". Usually that's a misread or a hallucination, but it can also be a real book that is too hard for a person to read and so was left out of the ground truth. The `not_in_ground_truth` list in the details file shows each one, which is where to look for failure examples. The ground truth is frozen, so FPs are not added back to it.

## Scores

| Metric | Formula | Question it answers |
| --- | --- | --- |
| **Precision** | TP / (TP + FP) | Of the books the model named, how many are really there? Low precision means more misreads or hallucinations. |
| **Recall** | TP / (TP + FN) | Of the books that are there, how many did the model find? |
| **F1** | 2 × P × R / (P + R) | One number that balances the two |
| **Macro F1** | Average of the per-image F1 scores | Treats every photo equally, so the 108-book photo doesn't outweigh the 8-book one |
| **Easy / medium / hard F1** | F1 using only the photos at that difficulty | How performance changes as photos get harder |
| **Author accuracy** | Correct authors / matched books where the model gave an author and the ground truth has one | When the model names an author, is it right? A `null` author is not counted against the model, because the prompt tells it to use `null` when unsure. |

An author counts as correct if it's at least 80% similar to the ground truth, or if it contains the surname of the first ground-truth author ("Rowling" matches "J.K. Rowling").

The overall precision, recall and F1 are **micro-averaged**: TP, FP and FN are added up across all images first, then the formulas are applied. The large photos therefore count more. Use macro F1 to compare photos equally.

## Reliability

| Field | Meaning |
| --- | --- |
| **relabelled** | Letters that were reassigned to a different photo before scoring (see [Photo labels](#photo-labels)). Empty if the letters were already right. |
| **reply_readable** | Whether the reply contained a JSON object with keys naming the photos (`a` to `f`; `A` and `a.jpg` also work). If not (a refusal, or broken JSON), every photo is scored as an empty answer. |
| **missing_images** | Photos with no book list in the reply, because the model left them out or the whole reply was unreadable. Each counts as an empty answer: all FN, recall 0 for that photo. Its status in `per_image.csv` is `missing` or `parse_error`. |
| **duplicates_removed** | Repeated titles within a photo, removed before scoring |

Empty reply files are skipped entirely: they're experiments that haven't been run yet.

## Output files

| File | Contents |
| --- | --- |
| `results/summary.csv` | One row per experiment, with all the scores above |
| `results/per_image.csv` | One row per experiment × image: counts, precision, recall, F1, author accuracy, parse status |
| `results/details/<experiment>.json` | For each image: every matched pair with its similarity, every missed book, and every book not in the ground truth |

## Known limitations

- **Different scripts don't match.** A title transliterated into Latin letters ("Life Ke Kadve Sach") doesn't match the same title in Devanagari (लाइफ के कड़वे सच).
- **Volume numbers are loosely checked.** "A Life of Picasso Volume I" matches the ground truth's Volume III, because the main title is the same.
- **Fuzzy matching can be wrong.** It can occasionally pair two different books with very similar titles, or miss a match when a title is reworded heavily. Check the details file if a number looks surprising.
- **Some ground-truth "authors" aren't people.** A few are publishers or institutions, such as "Tate Gallery" and "Arts Council". A model that gives the real author there will be marked wrong. This only affects author accuracy, not precision, recall or F1.
- **Every experiment runs once.** Chat models give different answers each time. Differences of a few points between experiments may be noise.
