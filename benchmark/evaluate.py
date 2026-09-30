"""Score pasted model replies against ground_truth.json.

Usage:
    python benchmark/evaluate.py [raw_dir] [out_dir]

By default reads results/raw/*.md (one reply with all 6 images per file) and writes to results/:
    summary.csv       one row per experiment
    per_image.csv     one row per experiment x image
    details/<experiment>.json   matched, missed and not-in-ground-truth books

See METRICS.md for what each number means. Uses only the Python standard library.
"""
import csv
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache
from itertools import permutations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GT_PATH = ROOT / 'ground_truth.json'
TITLE_THRESHOLD = 0.85   # minimum title similarity to count as the same book
AUTHOR_THRESHOLD = 0.80  # minimum author similarity to count the author as right
PART_SCORE = 0.90        # score when one title is the start or end of the other (subtitle or series name left out)
ARTICLES = ('the ', 'a ', 'an ')


# ---------- text normalisation and matching ----------

def normalize(text):
    """Lowercase, drop accents on Latin letters, turn punctuation into spaces."""
    text = unicodedata.normalize('NFKD', (text or '').casefold()).replace('&', ' and ')
    out, prev = [], ''
    for ch in text:
        cat = unicodedata.category(ch)
        if cat == 'Mn' and prev and ord(prev) < 0x250:
            continue  # accent on a Latin letter (é -> e); keeps Devanagari vowel signs
        if cat[0] in 'LNM':
            out.append(ch)
            prev = ch
        else:
            out.append(' ')
            prev = ''
    return ' '.join(''.join(out).split())


@lru_cache(maxsize=None)
def title_variants(title):
    """Full title, main title (before ':', '(' or '/'), subtitle (after ':', up to any '('),
    each with and without a leading article.

    Returns (variant, same words sorted) pairs; the sorted form makes word order irrelevant.
    """
    variants = {normalize(title), normalize(re.split(r'[:(/]', title)[0])}
    if ':' in title:
        variants.add(normalize(title.split(':', 1)[1].split('(')[0]))
    for v in list(variants):
        for article in ARTICLES:
            if v.startswith(article):
                variants.add(v[len(article):])
    variants.discard('')
    return tuple((v, ' '.join(sorted(v.split()))) for v in sorted(variants))


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def similarity_if_close(a, b):
    """Exact similarity when it could reach the match threshold, otherwise 0 (fast path)."""
    sm = SequenceMatcher(None, a, b)
    if sm.real_quick_ratio() < TITLE_THRESHOLD or sm.quick_ratio() < TITLE_THRESHOLD:
        return 0.0
    return sm.ratio()


def is_specific_part(a, b):
    """True if the shorter title (3+ words) is the start or the end of the longer one."""
    short, long_ = sorted((a.split(), b.split()), key=len)
    return len(short) >= 3 and short in (long_[:len(short)], long_[-len(short):])


def title_score(pred, gt):
    """(best variant similarity, full-title similarity). The second breaks ties.

    Scores below TITLE_THRESHOLD come back as 0, since only matches matter.
    """
    best = 0.0
    for p, p_sorted in title_variants(pred):
        for g, g_sorted in title_variants(gt):
            best = max(best, similarity_if_close(p, g), similarity_if_close(p_sorted, g_sorted))
            if is_specific_part(p, g):
                best = max(best, PART_SCORE)
    if best < TITLE_THRESHOLD:
        return 0.0, 0.0
    return best, similarity(normalize(pred), normalize(gt))


def author_correct(pred, gt):
    p, g = normalize(pred), normalize(gt)
    if not p:
        return False
    if similarity(p, g) >= AUTHOR_THRESHOLD:
        return True
    # Surname check: the last word of the first listed author appears in the prediction.
    first_author = re.split(r'\s*(?:&|,|/|\band\b|\bwith\b)\s*', gt)[0]
    words = normalize(first_author).split()
    return bool(words) and len(words[-1]) > 2 and words[-1] in p.split()


def match_books(preds, gts):
    """Greedy one-to-one matching, best pairs first."""
    pairs = []
    for i, p in enumerate(preds):
        for j, g in enumerate(gts):
            best, full = title_score(p['title'], g['title'])
            if best >= TITLE_THRESHOLD:
                pairs.append((best, full, i, j))
    pairs.sort(reverse=True)
    used_p, used_g, matches = set(), set(), []
    for best, _, i, j in pairs:
        if i in used_p or j in used_g:
            continue
        used_p.add(i)
        used_g.add(j)
        matches.append((i, j, round(best, 3)))
    return matches, used_p, used_g


# ---------- reading the pasted replies ----------

def parse_raw_file(path):
    """Return (metadata dict, reply text). The reply is everything under the '## Reply' heading."""
    text = re.sub(r'<!--.*?-->', '', path.read_text(encoding='utf-8'), flags=re.S)
    parts = re.split(r'^##\s+Reply\s*$', text, maxsplit=1, flags=re.M)
    head, reply = parts[0], parts[1] if len(parts) > 1 else ''
    meta = {}
    for line in head.splitlines():
        kv = re.match(r'^(\w+):\s*(.*)$', line)
        if kv:
            meta[kv.group(1)] = kv.group(2).strip()
    return meta, reply.strip()


def to_books(items):
    books = []
    for item in items:
        if isinstance(item, str):
            item = {'title': item}
        if isinstance(item, dict) and str(item.get('title') or '').strip():
            author = item.get('author')
            books.append({'title': str(item['title']).strip(),
                          'author': str(author).strip() if author else None})
    return books


def extract_predictions(reply, images):
    """Find the first JSON object in the reply whose keys name the images.

    Keys can be 'a', 'a.jpg', 'A', ... Each value is {"books": [...]} or a bare list.
    Returns {image filename: books}, or None if no such JSON was found.
    """
    stems = {Path(img).stem.casefold(): img for img in images}
    decoder = json.JSONDecoder()
    for m in re.finditer(r'\{', reply):
        try:
            obj, _ = decoder.raw_decode(reply[m.start():])
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        found = {}
        for key, value in obj.items():
            image = stems.get(Path(str(key).strip()).stem.casefold())
            items = value.get('books') if isinstance(value, dict) else value
            if image and isinstance(items, list):
                found[image] = to_books(items)
        if found:
            return found
    return None


def dedupe(books):
    seen, out = set(), []
    for b in books:
        key = normalize(b['title'])
        if key not in seen:
            seen.add(key)
            out.append(b)
    return out, len(books) - len(out)


# ---------- scoring ----------

def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def score_image(preds, gts):
    matches, used_p, used_g = match_books(preds, gts)
    author_known = author_right = 0
    matched = []
    for i, j, score in matches:
        p, g = preds[i], gts[j]
        ok = None
        if g['author'] and p['author']:  # only judge authors the model actually gave
            author_known += 1
            ok = author_correct(p['author'], g['author'])
            author_right += ok
        matched.append({'predicted': p, 'ground_truth': g, 'title_similarity': score, 'author_correct': ok})
    return {
        'tp': len(matches),
        'fp': len(preds) - len(used_p),
        'fn': len(gts) - len(used_g),
        'author_known': author_known,
        'author_right': author_right,
        'matched': matched,
        'not_in_ground_truth': [p for i, p in enumerate(preds) if i not in used_p],
        'missed': [g for j, g in enumerate(gts) if j not in used_g],
    }


def fmt(x):
    return f'{x:.3f}'


def align_labels(predictions, gt):
    """Undo whole-list label swaps.

    Some chat apps don't show the model the filenames, so it letters the photos in whatever
    order they arrived. This finds the one-to-one label -> photo assignment that matches the
    most books and uses it if it beats the labels as written. Individual books listed under
    the wrong photo are not moved and still count as errors.

    Returns (predictions keyed by the photo they were scored against, {label: photo} for moved labels).
    """
    labels, photos = sorted(predictions), sorted(gt)
    tp = {(label, photo): len(match_books(dedupe(predictions[label])[0], gt[photo]['books'])[0])
          for label in labels for photo in photos}
    best_perm = tuple(labels)
    best = sum(tp[label, label] for label in labels)
    for perm in permutations(photos, len(labels)):
        total = sum(tp[label, photo] for label, photo in zip(labels, perm))
        if total > best:
            best, best_perm = total, perm
    mapping = dict(zip(labels, best_perm))
    moved = {label: photo for label, photo in mapping.items() if label != photo}
    return {photo: predictions[label] for label, photo in mapping.items()}, moved


def label_of(image):
    return Path(image).stem


def main():
    raw_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'results' / 'raw'
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / 'results'
    gt = json.loads(GT_PATH.read_text(encoding='utf-8'))
    (out_dir / 'details').mkdir(parents=True, exist_ok=True)

    summary_rows, image_rows = [], []
    for path in sorted(raw_dir.glob('*.md')):
        experiment = path.stem
        meta, reply = parse_raw_file(path)
        if not reply:
            continue  # not run yet
        predictions = extract_predictions(reply, gt)
        moved = {}
        if predictions is None:
            print(f'WARNING {path.name}: no JSON with image keys (a, b, ...) found; every image scored as empty')
        else:
            predictions, moved = align_labels(predictions, gt)
        reply_label = {photo: label for label, photo in moved.items()}
        relabelled = ' '.join(f'{label_of(label)}->{label_of(photo)}' for label, photo in sorted(moved.items()))

        totals = {'tp': 0, 'fp': 0, 'fn': 0, 'author_known': 0, 'author_right': 0}
        by_difficulty, f1s, details = {}, [], {}
        missing_images = duplicates = 0
        for image in sorted(gt):
            entry = gt[image]
            if predictions is None:
                status, books = 'parse_error', []
            elif image not in predictions:
                status, books = 'missing', []
            else:
                status, books = 'ok', predictions[image]
            missing_images += status != 'ok'
            books, dups = dedupe(books)
            duplicates += dups
            s = score_image(books, entry['books'])
            p, r, f = prf(s['tp'], s['fp'], s['fn'])
            f1s.append(f)
            for k in totals:
                totals[k] += s[k]
            d = by_difficulty.setdefault(entry['difficulty'], [0, 0, 0])
            d[0] += s['tp']; d[1] += s['fp']; d[2] += s['fn']
            image_rows.append({
                'experiment': experiment, 'image': image, 'difficulty': entry['difficulty'],
                'reply_label': label_of(reply_label.get(image, image)) if status == 'ok' else '',
                'status': status, 'gt_books': len(entry['books']), 'predicted': len(books),
                'tp': s['tp'], 'fp': s['fp'], 'fn': s['fn'],
                'precision': fmt(p), 'recall': fmt(r), 'f1': fmt(f),
                'author_accuracy': fmt(s['author_right'] / s['author_known']) if s['author_known'] else '',
            })
            details[image] = {'status': status, 'reply_label': label_of(reply_label.get(image, image)),
                              'duplicates_removed': dups,
                              **{k: s[k] for k in ('matched', 'not_in_ground_truth', 'missed')}}

        p, r, f = prf(totals['tp'], totals['fp'], totals['fn'])
        row = {
            'experiment': experiment, 'model': meta.get('model', ''), 'mode': meta.get('mode', ''),
            'reply_readable': predictions is not None, 'relabelled': relabelled,
            'missing_images': missing_images, 'duplicates_removed': duplicates,
            'tp': totals['tp'], 'fp': totals['fp'], 'fn': totals['fn'],
            'precision': fmt(p), 'recall': fmt(r), 'f1': fmt(f),
            'macro_f1': fmt(sum(f1s) / len(f1s)),
            'author_accuracy': fmt(totals['author_right'] / totals['author_known']) if totals['author_known'] else '',
        }
        for level in ('easy', 'medium', 'hard'):
            if level in by_difficulty:
                row[f'{level}_f1'] = fmt(prf(*by_difficulty[level])[2])
        summary_rows.append(row)
        (out_dir / 'details' / f'{experiment}.json').write_text(
            json.dumps({'metadata': meta, 'images': details}, ensure_ascii=False, indent=2), encoding='utf-8')

    if not summary_rows:
        print(f'No results found in {raw_dir}. Paste model replies into the files there first.')
        return

    summary_fields = ['experiment', 'model', 'mode', 'reply_readable', 'relabelled', 'missing_images',
                      'duplicates_removed', 'tp', 'fp', 'fn', 'precision', 'recall', 'f1', 'macro_f1',
                      'easy_f1', 'medium_f1', 'hard_f1', 'author_accuracy']
    with open(out_dir / 'summary.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=summary_fields, restval='')
        w.writeheader()
        w.writerows(summary_rows)
    with open(out_dir / 'per_image.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(image_rows[0]))
        w.writeheader()
        w.writerows(image_rows)

    summary_rows.sort(key=lambda r: float(r['f1']), reverse=True)
    print(f"{'experiment':<38}{'P':>7}{'R':>7}{'F1':>7}{'easy':>7}{'med':>7}{'hard':>7}{'auth':>7}")
    for r in summary_rows:
        flag = f"  ({r['missing_images']} image(s) missing)" if r['missing_images'] else ''
        if r['relabelled']:
            flag += f"  (photo labels corrected: {r['relabelled']})"
        print(f"{r['experiment']:<38}{r['precision']:>7}{r['recall']:>7}{r['f1']:>7}"
              f"{r.get('easy_f1', ''):>7}{r.get('medium_f1', ''):>7}{r.get('hard_f1', ''):>7}"
              f"{r['author_accuracy']:>7}{flag}")
    print(f'\nWrote {out_dir / "summary.csv"}, {out_dir / "per_image.csv"} and {out_dir / "details"}/')


if __name__ == '__main__':
    main()
