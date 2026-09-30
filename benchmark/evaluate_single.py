"""Experiment 2: score one-photo-per-chat replies and compare them with the all-at-once runs.

Usage:
    python benchmark/evaluate_single.py

Reads results/raw_single/*.md (one section per photo: '## e.jpg', '## f.jpg') and, for the
same experiment, results/raw/*.md (all 6 photos in one message). Writes to results/single/:
    summary.csv                  one row per experiment x photo, both conditions side by side
    details/<experiment>.json    matched, missed and not-in-ground-truth books (single-photo runs)

Matching and scoring are the same as benchmark/evaluate.py; see METRICS.md.
"""
import csv
import json
import re
from pathlib import Path

import evaluate as ev

SINGLE_DIR = ev.ROOT / 'results' / 'raw_single'
BATCH_DIR = ev.ROOT / 'results' / 'raw'
OUT_DIR = ev.ROOT / 'results' / 'single'


def parse_single_file(path):
    """Return (metadata dict, {photo filename: reply text})."""
    text = re.sub(r'<!--.*?-->', '', path.read_text(encoding='utf-8'), flags=re.S)
    meta, sections, current = {}, {}, None
    for line in text.splitlines():
        header = re.match(r'^##\s+(\S+)\s*$', line)
        if header:
            current = header.group(1)
            sections[current] = []
        elif current is None:
            kv = re.match(r'^(\w+):\s*(.*)$', line)
            if kv:
                meta[kv.group(1)] = kv.group(2).strip()
        else:
            sections[current].append(line)
    return meta, {k: '\n'.join(v).strip() for k, v in sections.items()}


def extract_single(reply):
    """Book list from {"books": [...]}, a bare list, or a one-photo object like {"e": {"books": [...]}}."""
    decoder = json.JSONDecoder()
    for m in re.finditer(r'[{\[]', reply):
        try:
            obj, _ = decoder.raw_decode(reply[m.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, list):
            return ev.to_books(obj)
        if isinstance(obj, dict):
            if isinstance(obj.get('books'), list):
                return ev.to_books(obj['books'])
            inner = [v['books'] for v in obj.values() if isinstance(v, dict) and isinstance(v.get('books'), list)]
            if len(inner) == 1:
                return ev.to_books(inner[0])
    return None


def batch_books(experiment, gt):
    """The all-at-once run's book lists per photo (after photo-label correction), or None."""
    path = BATCH_DIR / f'{experiment}.md'
    if not path.exists():
        return None
    _, reply = ev.parse_raw_file(path)
    predictions = ev.extract_predictions(reply, gt) if reply else None
    if predictions is None:
        return None
    return ev.align_labels(predictions, gt)[0]


def scores(books, gt_books):
    books, _ = ev.dedupe(books)
    s = ev.score_image(books, gt_books)
    p, r, f = ev.prf(s['tp'], s['fp'], s['fn'])
    return s, {'listed': len(books), 'tp': s['tp'], 'fp': s['fp'], 'p': p, 'r': r, 'f1': f}


def main():
    gt = json.loads(ev.GT_PATH.read_text(encoding='utf-8'))
    (OUT_DIR / 'details').mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(SINGLE_DIR.glob('*.md')):
        experiment = path.stem
        meta, sections = parse_single_file(path)
        unknown = [k for k in sections if k not in gt]
        if unknown:
            print(f'WARNING {path.name}: headings not in ground_truth.json: {unknown}')
        batch = batch_books(experiment, gt)
        details = {}
        for image, reply in sections.items():
            if image not in gt or not reply:
                continue  # not run yet
            books = extract_single(reply)
            status = 'ok'
            if books is None:
                status, books = 'parse_error', []
                print(f'WARNING {path.name}: no readable book list under {image}; scored as empty')
            s, single = scores(books, gt[image]['books'])
            details[image] = {'status': status, **{k: s[k] for k in ('matched', 'not_in_ground_truth', 'missed')}}
            row = {
                'experiment': experiment, 'model': meta.get('model', ''), 'mode': meta.get('mode', ''),
                'image': image, 'gt_books': len(gt[image]['books']), 'status': status,
                'single_listed': single['listed'], 'single_tp': single['tp'], 'single_fp': single['fp'],
                'single_precision': ev.fmt(single['p']), 'single_recall': ev.fmt(single['r']),
                'single_f1': ev.fmt(single['f1']),
            }
            if batch is not None:
                _, b = scores(batch.get(image, []), gt[image]['books'])
                row.update({
                    'batch_listed': b['listed'], 'batch_tp': b['tp'], 'batch_fp': b['fp'],
                    'batch_precision': ev.fmt(b['p']), 'batch_recall': ev.fmt(b['r']), 'batch_f1': ev.fmt(b['f1']),
                    'recall_change': f"{single['r'] - b['r']:+.3f}", 'f1_change': f"{single['f1'] - b['f1']:+.3f}",
                })
            rows.append(row)
        if details:
            (OUT_DIR / 'details' / f'{experiment}.json').write_text(
                json.dumps({'metadata': meta, 'images': details}, ensure_ascii=False, indent=2), encoding='utf-8')

    if not rows:
        print(f'No results found in {SINGLE_DIR}. Paste model replies into the files there first.')
        return

    fields = ['experiment', 'model', 'mode', 'image', 'gt_books', 'status',
              'batch_listed', 'single_listed', 'batch_tp', 'single_tp', 'batch_fp', 'single_fp',
              'batch_precision', 'single_precision', 'batch_recall', 'single_recall', 'recall_change',
              'batch_f1', 'single_f1', 'f1_change']
    with open(OUT_DIR / 'summary.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=fields, restval='')
        w.writeheader()
        w.writerows(rows)

    print(f"{'experiment':<36}{'photo':>6}{'listed':>14}{'recall':>16}{'change':>8}{'precision':>16}")
    print(f"{'':<36}{'':>6}{'all -> one':>14}{'all -> one':>16}{'':>8}{'all -> one':>16}")
    for r in sorted(rows, key=lambda r: (r['image'], r['experiment'])):
        print(f"{r['experiment']:<36}{r['image'][0]:>6}"
              f"{str(r.get('batch_listed', '-')):>7} ->{r['single_listed']:>4}"
              f"{r.get('batch_recall', '-'):>8} ->{r['single_recall']:>6}{r.get('recall_change', ''):>8}"
              f"{r.get('batch_precision', '-'):>8} ->{r['single_precision']:>6}")
    print(f'\nWrote {OUT_DIR / "summary.csv"} and {OUT_DIR / "details"}/')


if __name__ == '__main__':
    main()
