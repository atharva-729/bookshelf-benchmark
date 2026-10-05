"""Estimate what each run 2 chat would have cost on the API.

Usage:
    python benchmark/estimate_cost.py

The runs were done in consumer chat apps, which report no token counts, so this is an
estimate built from what the apps do expose (logged in results/raw_run2/):

- input: the prompt text plus the six photos, using each provider's published image-token rule;
- visible output: the reply text, counted from the saved reply;
- thinking: hidden by every app, so estimated from timing (see below);
- ChatGPT: the app ran Python on the images in a loop, so each loop turn re-reads the context.

Every estimate is a low / mid / high range. Prices are list API prices per million tokens on
2026-10-04. Hidden app system prompts are not counted. Writes results/run2/cost.csv.
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'results' / 'raw_run2'
USAGE = RAW / 'usage'
OUT = ROOT / 'results' / 'run2' / 'cost.csv'

# $ per 1M tokens (input, output). GPT: the ChatGPT Go plan served gpt-5-6 (standard) and
# gpt-5-6-t-mini (Think); both priced at the GPT-5.6 Luna tier, an assumption.
PRICES = {
    'claude-opus-5.5': (4.00, 20.00),
    'claude-opus-5': (5.00, 25.00),
    'claude-sonnet-5.5': (2.00, 10.00),
    'claude-sonnet-5': (2.00, 10.00),
    'gemini-3.1-pro': (2.00, 12.00),
    'gemini-3.8-flash': (0.75, 3.75),  # introductory price, valid to 2026-12-31
    'gpt-5.6-luna': (0.20, 1.20),
}
GPT_CACHED_INPUT_SHARE = 0.10  # cached input costs 10% of the normal input price

CHARS_PER_TOKEN_TEXT = 4.0  # English prompt
CHARS_PER_TOKEN_JSON = 3.5  # replies: JSON with many short strings
PHOTO_PX = {'a': (1300, 956), 'b': (1300, 956), 'c': (1080, 1440),
            'd': (5712, 4284), 'e': (5712, 4284), 'f': (5712, 4284)}


def claude_image_tokens(long_edge_cap, token_cap):
    """Claude: tokens ~ w*h/750 after resizing to fit the long-edge cap, capped per image."""
    total = 0
    for w, h in PHOTO_PX.values():
        scale = min(1.0, long_edge_cap / max(w, h))
        total += min(token_cap, (w * scale) * (h * scale) / 750)
    return total


def gpt_image_tokens(stored):
    """GPT-5.x: one token per 32x32 patch of the image as ChatGPT stored it."""
    return sum(-(-w // 32) * -(-h // 32) for w, h in stored)


def read_raw(path):
    text = path.read_text(encoding='utf-8')
    meta = dict(re.findall(r'^(\w+):\s*(.*)$', text.split('## Reply')[0], flags=re.M))
    reply = text.split('## Reply', 1)[1].strip()
    latency = float(re.match(r'[~]?([\d.]+)', meta['latency_s']).group(1))
    return meta, reply, latency


def fmt_range(lo, mid, hi):
    return {'low': lo, 'mid': mid, 'high': hi}


def cost(tokens_in, tokens_out, price):
    return tokens_in / 1e6 * price[0] + tokens_out / 1e6 * price[1]


def estimate(name, meta, reply, latency, usage, gemini_std_rate):
    family = name.split('__')[0]
    mode = name.split('__')[1]
    price = PRICES[family]
    prompt_tok = 1021 / CHARS_PER_TOKEN_TEXT
    reply_tok = len(reply) / CHARS_PER_TOKEN_JSON
    note = ''

    if family.startswith('claude'):
        # Opus 5.5 / Opus 5 / Sonnet 5.5 / Sonnet 5: up to 2576 px long edge, <=4784 tokens per image.
        # Low end assumes the app downsized to the older 1568 px limit.
        img = fmt_range(claude_image_tokens(1568, 1568), claude_image_tokens(2576, 4784),
                        claude_image_tokens(2576, 4784))
        think_s = (usage.get('thinking') or {}).get('seconds', 0)
        stream_s = usage.get('reply_stream_s')
        if think_s and stream_s:
            rate = reply_tok / stream_s  # this run's own output speed
            t_mid = think_s * rate
            note = f'thinking {think_s:.0f} s x {rate:.0f} tok/s (reply speed)'
        else:
            t_mid = 0
            note = 'no thinking block'
        think = fmt_range(0.5 * t_mid, t_mid, 1.5 * t_mid)
        tin = {k: prompt_tok + img[k] for k in img}
        tout = {k: reply_tok + think[k] for k in think}
        costs = {k: cost(tin[k], tout[k], price) for k in tin}

    elif family.startswith('gemini'):
        # Gemini 3: 1120 tokens per image at the default resolution (560 medium, 2240 ultra high).
        img = fmt_range(6 * 560, 6 * 1120, 6 * 2240)
        if mode == 'standard':
            think = fmt_range(0, 0, 0.5 * reply_tok)
            note = 'no thinking shown'
        else:
            # Extra time over the standard run of the same model, at the standard run's speed.
            std_latency, rate = gemini_std_rate[family]
            t_mid = max(0.0, latency - std_latency) * rate
            think = fmt_range(0.5 * t_mid, t_mid, 1.5 * t_mid)
            note = f'thinking ~ ({latency:.0f} - {std_latency:.0f}) s x {rate:.0f} tok/s'
        tin = {k: prompt_tok + img[k] for k in img}
        tout = {k: reply_tok + think[k] for k in think}
        costs = {k: cost(tin[k], tout[k], price) for k in tin}

    else:  # GPT in ChatGPT: a Python tool loop
        base_in = prompt_tok + gpt_image_tokens(usage['images_as_stored_px'])
        ch = usage['chars']
        turns = usage['message_counts']['assistant:code'] + 1
        loop_tok = (ch['code'] + ch['tool_output'] + ch['thoughts_visible']) / CHARS_PER_TOKEN_TEXT
        visible_out = reply_tok + (ch['code'] + ch['thoughts_visible']) / CHARS_PER_TOKEN_TEXT
        # Each turn re-reads the images and the transcript so far (on average half the loop text).
        reread = (turns - 1) * (base_in + loop_tok / 2)
        hidden_hi = latency * 50  # upper bound: the whole wait spent reasoning at 50 tok/s
        hidden = fmt_range(0, (visible_out * hidden_hi) ** 0.5, hidden_hi)
        tin_full = base_in + loop_tok / 2 + reread
        costs = {
            'low': cost(base_in + GPT_CACHED_INPUT_SHARE * reread, visible_out, price),
            'mid': cost(base_in + GPT_CACHED_INPUT_SHARE * reread, visible_out + hidden['mid'], price),
            'high': cost(tin_full, visible_out + hidden['high'], price),
        }
        tin = fmt_range(base_in, base_in + reread, tin_full)
        tout = {k: visible_out + hidden[k] for k in hidden}
        note = f'{turns} model turns (Python tool loop); hidden reasoning unknown'

    return {'experiment': name, 'model': meta['model'], 'mode': meta['mode'], 'latency_s': latency,
            'input_tokens_mid': round(tin['mid']), 'output_tokens_mid': round(tout['mid']),
            'cost_low': round(costs['low'], 5), 'cost_mid': round(costs['mid'], 5),
            'cost_high': round(costs['high'], 5), 'price_in': price[0], 'price_out': price[1],
            'method': note}


def main():
    raws = {p.stem: read_raw(p) for p in sorted(RAW.glob('*.md'))}
    usage = {p.stem: json.loads(p.read_text(encoding='utf-8-sig')) for p in USAGE.glob('*.json')}
    for name, u in usage.items():  # older usage files store image sizes under a different key
        if 'images_as_stored' in u:
            u['images_as_stored_px'] = [(x['width'], x['height']) if isinstance(x, dict) else tuple(x)
                                        for x in u['images_as_stored']]

    gemini_std_rate = {}
    for name, (meta, reply, latency) in raws.items():
        if name.startswith('gemini') and name.endswith('__standard'):
            gemini_std_rate[name.split('__')[0]] = (latency, len(reply) / CHARS_PER_TOKEN_JSON / latency)

    rows = [estimate(n, m, r, lat, usage.get(n, {}), gemini_std_rate) for n, (m, r, lat) in raws.items()]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f'{"experiment":<38}{"in tok":>9}{"out tok":>9}{"low $":>9}{"mid $":>9}{"high $":>9}  method')
    for r in sorted(rows, key=lambda r: r['cost_mid']):
        print(f'{r["experiment"]:<38}{r["input_tokens_mid"]:>9}{r["output_tokens_mid"]:>9}'
              f'{r["cost_low"]:>9.4f}{r["cost_mid"]:>9.4f}{r["cost_high"]:>9.4f}  {r["method"]}')
    print(f'\nWrote {OUT}')


if __name__ == '__main__':
    main()
