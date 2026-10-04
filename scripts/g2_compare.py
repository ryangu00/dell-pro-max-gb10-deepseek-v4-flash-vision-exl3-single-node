#!/usr/bin/env python3
"""Report category arithmetic; aggregate rows cannot validate quality gates."""
import argparse
import json
import statistics
from pathlib import Path

OWN = ['c1-kbqa', 'c2-longctx', 'c4-code', 'c5-extract', 'c6-vision', 'c7-zhif', 'c9-long-coding', 'c10-sre-ops']
PACK = ['c3-tool', 'c7-agentic-if', 'c8-judgment']


def rows(result):
    out = {}
    for row in result['rows']:
        cat = row.get('cat') or row.get('category') or row.get('id')
        runs = [v for v in row.get('runs', []) if v is not None]
        if runs:
            out[cat] = {'runs': runs, 'med': statistics.median(runs),
                        'spread': max(runs)-min(runs), 'safety': row.get('safety')}
    return out


def load(root, labels):
    merged = {}
    for label in labels.split(','):
        direct = root / label / 'results.json'
        candidates = [direct] if direct.is_file() else sorted(root.glob(f'*-{label}/results.json'))
        if not candidates:
            raise ValueError(f'no results for {label}')
        merged.update(rows(json.loads(candidates[-1].read_text())))
    return merged


def render(baseline, vision, control, own, pack):
    lines = ['Arithmetic only: reference model identity and matched run conditions are not verified.',
             'A shared served alias or result label does not establish a valid two-node baseline.',
             '',
             '| Category | Reference (unverified) | Vision | Arithmetic delta | Control | Arithmetic delta |',
             '|---|---|---|---|---|---|']
    def cell(data, cat):
        if cat not in data:
            return 'not provided', None
        r = data[cat]
        marker = '*' if r['spread'] > 5 else ''
        return f"{r['med']:.1f}{marker} ({'/'.join(f'{v:.0f}' for v in r['runs'])})", r['med']
    means = {}
    for name, group in [('own', own), ('pack', pack)]:
        for cat in group:
            b,bm = cell(baseline,cat); v,vm = cell(vision,cat); c,cm = cell(control,cat)
            dv = f'{vm-bm:+.1f}' if vm is not None and bm is not None else 'not provided'
            dc = f'{cm-bm:+.1f}' if cm is not None and bm is not None else 'not provided'
            lines.append(f'| {cat} | {b} | {v} | {dv} | {c} | {dc} |')
        for tag,data in [('baseline',baseline),('vision',vision),('control',control)]:
            means[name,tag] = statistics.mean(data[c]['med'] for c in group) if group and all(c in data for c in group) else None
        values = [means[name,t] for t in ('baseline','vision','control')]
        b,v,c = ['not provided' if x is None else f'{x:.1f}' for x in values]
        lines.append(f'| {name} mean | {b} | {v} | | {c} | |')
    lines += ['', '* marks spread above 5 points; these runs are not comparable by the harness rule.', '']
    lines.append('Original and rewritten quality gates: not evaluated '
                 '(reference identity and run conditions are not verified).')
    lines.append('These deltas do not establish the quality cost of moving a model from two nodes to one.')
    missing = [c for c in pack if c not in vision or vision[c]['safety'] is None]
    failures = [c for c in pack if c in vision and (vision[c]['safety'] or 0)>0]
    lines.append('Safety: not evaluated (missing data).' if missing else f'Safety failures: {failures or "none recorded"}.')
    return '\n'.join(lines)+'\n'


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--runs',type=Path,required=True)
    ap.add_argument('--baseline',required=True,
                    help='Reference label, or comma-separated labels to merge; selects arithmetic inputs only, not a validated baseline')
    ap.add_argument('--vision',required=True)
    ap.add_argument('--control',required=True)
    ap.add_argument('--own',default=','.join(OWN))
    ap.add_argument('--pack',default=','.join(PACK))
    ap.add_argument('--out',type=Path)
    a=ap.parse_args()
    text=render(load(a.runs,a.baseline),load(a.runs,a.vision),load(a.runs,a.control),
                [c for c in a.own.split(',') if c],[c for c in a.pack.split(',') if c])
    print(text,end='')
    if a.out: a.out.write_text(text)


if __name__=='__main__': main()
