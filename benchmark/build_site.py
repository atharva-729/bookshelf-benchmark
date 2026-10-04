"""Write docs/data.js for the results page (docs/index.html).

Usage (after scoring):
    python benchmark/evaluate.py
    python benchmark/evaluate_single.py
    python benchmark/build_site.py

Reads results/summary.csv, results/per_image.csv and results/single/summary.csv, plus run 2
(results/run2/summary.csv, per_image.csv, and cost.csv from benchmark/estimate_cost.py) if present.
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


def provider(model):
    return model.split()[0]  # Claude / Gemini / GPT


def run_meta(row):
    return {'id': row['experiment'], 'model': row['model'], 'mode': MODE_LABELS.get(row['mode'], row['mode']),
            'provider': provider(row['model'])}


def exp1_runs(folder):
    """Experiment 1 runs (all six photos in one message) from a scored results folder."""
    per_image = read_csv(folder / 'per_image.csv')
    runs = []
    for row in read_csv(folder / 'summary.csv'):
        cells = {}
        for r in per_image:
            if r['experiment'] == row['experiment']:
                cells[Path(r['image']).stem] = {
                    'precision': num(r['precision']), 'recall': num(r['recall']), 'f1': num(r['f1']),
                    'found': int(r['tp']), 'wrong': int(r['fp']), 'listed': int(r['predicted']),
                    'total': int(r['gt_books'])}
        runs.append({**run_meta(row), 'relabelled': row['relabelled'],
                     'overall': {'precision': num(row['precision']), 'recall': num(row['recall']),
                                 'f1': num(row['f1']), 'found': int(row['tp']), 'wrong': int(row['fp']),
                                 'total': int(row['tp']) + int(row['fn'])},
                     'photos': cells})
    return runs


def skipped_single_runs():
    """Experiment 2 runs that weren't done, with the note from their reply file."""
    out = []
    for path in sorted((RESULTS / 'raw_single').glob('*.md')):
        text = path.read_text(encoding='utf-8')
        note = re.search(r'^notes:\s*(Not run.*)$', text, flags=re.M)
        if note:
            model = re.search(r'^model:\s*(.*)$', text, flags=re.M).group(1).strip()
            mode = re.search(r'^mode:\s*(.*)$', text, flags=re.M).group(1).strip()
            out.append({'model': model, 'mode': MODE_LABELS.get(mode, mode), 'note': note.group(1).strip()})
    return out


def main():
    gt = json.loads((ROOT / 'ground_truth.json').read_text(encoding='utf-8'))
    photos = [{'id': Path(k).stem, 'file': k, 'difficulty': v['difficulty'], 'books': len(v['books'])}
              for k, v in sorted(gt.items())]

    exp1 = exp1_runs(RESULTS)
    exp1_run2 = exp1_runs(RESULTS / 'run2') if (RESULTS / 'run2' / 'summary.csv').exists() else []
    cost = {}
    if (RESULTS / 'run2' / 'cost.csv').exists():
        for r in read_csv(RESULTS / 'run2' / 'cost.csv'):
            cost[r['experiment']] = {'low': num(r['cost_low']), 'mid': num(r['cost_mid']), 'high': num(r['cost_high']),
                                     'inTokens': int(r['input_tokens_mid']), 'outTokens': int(r['output_tokens_mid']),
                                     'latency': num(r['latency_s']), 'method': r['method']}

    exp2 = {}
    for r in read_csv(RESULTS / 'single' / 'summary.csv'):
        run = exp2.setdefault(r['experiment'], {**run_meta(r), 'photos': {}})
        cond = {}
        for key, prefix in (('batch', 'batch_'), ('single', 'single_')):
            cond[key] = {'precision': num(r[prefix + 'precision']), 'recall': num(r[prefix + 'recall']),
                         'f1': num(r[prefix + 'f1']), 'found': int(r[prefix + 'tp']),
                         'wrong': int(r[prefix + 'fp']), 'listed': int(r[prefix + 'listed'])}
        cond['total'] = int(r['gt_books'])
        run['photos'][Path(r['image']).stem] = cond
    for run in exp2.values():  # both hard photos combined
        combined = {'total': sum(p['total'] for p in run['photos'].values())}
        for key in ('batch', 'single'):
            tp = sum(p[key]['found'] for p in run['photos'].values())
            fp = sum(p[key]['wrong'] for p in run['photos'].values())
            prec = tp / (tp + fp) if tp + fp else 0.0
            rec = tp / combined['total']
            combined[key] = {'precision': round(prec, 3), 'recall': round(rec, 3),
                             'f1': round(2 * prec * rec / (prec + rec), 3) if prec + rec else 0.0,
                             'found': tp, 'wrong': fp}
        run['photos']['combined'] = combined

    data = {'photos': photos, 'exp1': exp1, 'exp1Run2': exp1_run2, 'cost': cost,
            'exp2': list(exp2.values()), 'exp2Skipped': skipped_single_runs()}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text('// Generated by benchmark/build_site.py - do not edit by hand.\n'
                   'window.BENCH = ' + json.dumps(data, ensure_ascii=False, indent=1) + ';\n', encoding='utf-8')
    print(f'Wrote {OUT} ({len(exp1)} experiment 1 runs, {len(exp2)} experiment 2 runs)')


if __name__ == '__main__':
    main()
