"""Write docs/data.js for the results page (docs/index.html).

Usage (after scoring):
    python benchmark/evaluate.py
    python benchmark/evaluate_single.py
    python benchmark/estimate_cost.py
    python benchmark/build_site.py

Reads the scored results in results/exp1-run1, results/exp1-run2 (with cost.csv) and
results/exp2-one-photo, plus the book-by-book details files, so every tile on the page can
show which books were found, missed or named but not in the answer key.
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / 'results'
OUT = ROOT / 'docs' / 'data.js'

MODE_LABELS = {'standard': 'standard', 'thinking': 'thinking', 'extended-thinking': 'extended thinking',
               'low': 'low effort', 'medium': 'medium effort', 'high': 'high effort'}


def read_csv(path):
    with open(path, encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def num(x):
    return float(x) if x not in ('', None) else None


def setup_meta(row):
    return {'id': row['experiment'], 'model': row['model'], 'mode': MODE_LABELS.get(row['mode'], row['mode']),
            'provider': row['model'].split()[0]}  # Claude / Gemini / GPT


def book_label(book):
    return f"{book['title']} ({book['author']})" if book.get('author') else book['title']


def books_of(detail, gt_titles):
    """Compact book lists for one photo: found [ground-truth index, how the model wrote it or 0]
    and extra (named, not in the answer key). Missed books are the ground-truth indexes not found."""
    found = []
    for m in detail['matched']:
        idx = gt_titles.index(m['ground_truth']['title'])
        written = m['predicted']['title']
        found.append([idx, 0 if written.casefold() == m['ground_truth']['title'].casefold() else written])
    return {'hit': sorted(found), 'extra': [book_label(b) for b in detail['not_in_ground_truth']]}


def exp1_run(folder, gt_titles):
    """One run of experiment 1 (all six photos in one message), keyed by setup id."""
    per_image = read_csv(folder / 'per_image.csv')
    run = {}
    for row in read_csv(folder / 'summary.csv'):
        details = json.loads((folder / 'details' / f"{row['experiment']}.json").read_text(encoding='utf-8'))
        cells = {}
        for r in per_image:
            if r['experiment'] == row['experiment']:
                pid = Path(r['image']).stem
                cells[pid] = {'precision': num(r['precision']), 'recall': num(r['recall']), 'f1': num(r['f1']),
                              'found': int(r['tp']), 'wrong': int(r['fp']), 'listed': int(r['predicted']),
                              'total': int(r['gt_books']),
                              **books_of(details['images'][r['image']], gt_titles[pid])}
        run[row['experiment']] = {
            'relabelled': bool(row['relabelled']),
            'overall': {'precision': num(row['precision']), 'recall': num(row['recall']), 'f1': num(row['f1']),
                        'found': int(row['tp']), 'wrong': int(row['fp']), 'total': int(row['tp']) + int(row['fn'])},
            'photos': cells}
    return run


def skipped_single_runs():
    """Experiment 2 setups that weren't run, with the note from their reply file."""
    out = []
    for path in sorted((RESULTS / 'exp2-one-photo' / 'replies').glob('*.md')):
        text = path.read_text(encoding='utf-8')
        note = re.search(r'^notes:\s*(Not run.*)$', text, flags=re.M)
        if note:
            out.append({'id': path.stem, 'note': note.group(1).strip()})
    return out


def main():
    gt = json.loads((ROOT / 'data' / 'ground_truth.json').read_text(encoding='utf-8'))
    gt_titles = {Path(k).stem: [b['title'] for b in v['books']] for k, v in gt.items()}
    photos = [{'id': Path(k).stem, 'file': k, 'difficulty': v['difficulty'], 'books': len(v['books']),
               'titles': gt_titles[Path(k).stem]} for k, v in sorted(gt.items())]

    setups = [setup_meta(r) for r in read_csv(RESULTS / 'exp1-run1' / 'summary.csv')]
    exp1 = {'run1': exp1_run(RESULTS / 'exp1-run1', gt_titles),
            'run2': exp1_run(RESULTS / 'exp1-run2', gt_titles)}

    cost = {}
    for r in read_csv(RESULTS / 'exp1-run2' / 'cost.csv'):
        cost[r['experiment']] = {'low': num(r['cost_low']), 'mid': num(r['cost_mid']), 'high': num(r['cost_high']),
                                 'inTokens': int(r['input_tokens_mid']), 'outTokens': int(r['output_tokens_mid']),
                                 'latency': num(r['latency_s']), 'method': r['method']}

    exp2 = {}
    exp2_dir = RESULTS / 'exp2-one-photo'
    for r in read_csv(exp2_dir / 'summary.csv'):
        pid = Path(r['image']).stem
        details = json.loads((exp2_dir / 'details' / f"{r['experiment']}.json").read_text(encoding='utf-8'))
        cond = {}
        for key, prefix in (('batch', 'batch_'), ('single', 'single_')):
            cond[key] = {'precision': num(r[prefix + 'precision']), 'recall': num(r[prefix + 'recall']),
                         'f1': num(r[prefix + 'f1']), 'found': int(r[prefix + 'tp']),
                         'wrong': int(r[prefix + 'fp']), 'listed': int(r[prefix + 'listed']),
                         'total': int(r['gt_books'])}
        # The all-at-once books are experiment 1 run 1's, already in exp1; only the one-photo ones are new.
        cond['single'].update(books_of(details['images'][r['image']], gt_titles[pid]))
        exp2.setdefault(r['experiment'], {})[pid] = cond
    for photos_of in exp2.values():  # both hard photos combined
        total = sum(c['batch']['total'] for c in photos_of.values())
        combined = {}
        for key in ('batch', 'single'):
            tp = sum(c[key]['found'] for c in photos_of.values())
            fp = sum(c[key]['wrong'] for c in photos_of.values())
            prec = tp / (tp + fp) if tp + fp else 0.0
            rec = tp / total
            combined[key] = {'precision': round(prec, 3), 'recall': round(rec, 3),
                             'f1': round(2 * prec * rec / (prec + rec), 3) if prec + rec else 0.0,
                             'found': tp, 'wrong': fp, 'listed': tp + fp, 'total': total}
        photos_of['combined'] = combined

    data = {'photos': photos, 'setups': setups, 'exp1': exp1, 'cost': cost,
            'exp2': exp2, 'exp2Skipped': skipped_single_runs()}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text('// Generated by benchmark/build_site.py - do not edit by hand.\n'
                   'window.BENCH = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n',
                   encoding='utf-8')
    print(f'Wrote {OUT} ({len(setups)} setups, {len(exp2)} experiment 2 setups, {OUT.stat().st_size // 1024} KB)')


if __name__ == '__main__':
    main()
