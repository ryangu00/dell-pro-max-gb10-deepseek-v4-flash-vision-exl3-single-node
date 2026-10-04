#!/usr/bin/env python3
"""Verify pinned file sizes and available SHA-256 values without downloading files."""
import argparse
import hashlib
import json
from pathlib import Path

def verify(rows, root, sizes_only=False):
    for row in rows:
        p = root / row['name']
        if not p.is_file() or p.stat().st_size != row['bytes']:
            raise ValueError(f"missing/size mismatch: {p}")
        if not sizes_only and row.get('sha256'):
            h = hashlib.sha256()
            with p.open('rb') as stream:
                for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
                    h.update(block)
            if h.hexdigest() != row['sha256']:
                raise ValueError(f"SHA256 mismatch: {p}")

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('candidate', choices=['ve-k22-d2'])
    ap.add_argument('root', type=Path)
    ap.add_argument('--sizes-only', action='store_true')
    ap.add_argument('--manifest', type=Path, default=Path(__file__).resolve().parents[1]/'configs/asset-plan.json')
    a = ap.parse_args()
    plan = json.loads(a.manifest.read_text())
    rows = plan['candidates'][a.candidate]['files']
    verify(rows, a.root, a.sizes_only)
    print(f"PASS {len(rows)} files; available_sha256_checked={not a.sizes_only}")
