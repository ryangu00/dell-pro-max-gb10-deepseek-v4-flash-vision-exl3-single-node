#!/usr/bin/env python3
"""Compare local draft tensor bytes with the pinned donor; return nonzero on a mismatch."""
import argparse
import hashlib
import json
import random
import re
import struct
import sys
import urllib.request
from pathlib import Path

REPO = "wrldsuksgo2mars/DeepSeek-V4-Flash-0731-EXL3-K2.1-D2.2-calibrated-v3"
REV = "7827301eed170e2a5e394f45a13cc66561c601ed"
SHARDS = ["model-00002-of-00011.safetensors", "model-00010-of-00011.safetensors", "model-00011-of-00011.safetensors"]
LOCAL = Path("hf/hub/models--wrldsuksgo2mars--DeepSeek-V4-Flash-Vision-Exp-EXL3-K2.2-D2-v1/snapshots/0731d22a00000000000000000000000000000001/model-mtp-draft0731-d22.safetensors")
BASE_URL = None
TOTALS = {}
GROUP_MAX = 256 << 20


def rng(f, a, b):
    """Fetch the inclusive byte interval [a,b]."""
    req = urllib.request.Request(f"{BASE_URL or f'https://huggingface.co/{REPO}/resolve/{REV}'}/{f}", headers={"Range": f"bytes={a}-{b}"})
    with urllib.request.urlopen(req, timeout=600) as r:
        cr = r.headers.get("Content-Range", "")
        m = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", cr)
        if r.status != 206 or not m or int(m.group(1)) != a or int(m.group(2)) != b or int(m.group(3)) <= b:
            raise SystemExit(f"FAIL bad range response {r.status} {cr!r} want {a}-{b} ({f})")
        tot = int(m.group(3))
        if TOTALS.setdefault(f, tot) != tot:
            raise SystemExit(f"FAIL total length changed for {f}: {TOTALS[f]} vs {tot}")
        data = r.read()
    if len(data) != b - a + 1:
        raise SystemExit(f"FAIL short body {len(data)} vs {b - a + 1} ({f} {a}-{b})")
    return data


def header(f):
    n = struct.unpack("<Q", rng(f, 0, 7))[0]
    return json.loads(rng(f, 8, 7 + n)), 8 + n


def main():
    global REPO, REV, SHARDS, LOCAL, BASE_URL
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--donor-repo", default=REPO)
    ap.add_argument("--donor-revision", default=REV)
    ap.add_argument("--shards", nargs="+", default=SHARDS)
    ap.add_argument("--local", type=Path, default=LOCAL)
    ap.add_argument("--source-base", help="Pinned source directory URL; useful for a loopback fixture")
    a = ap.parse_args()
    REPO, REV, SHARDS, LOCAL, BASE_URL = a.donor_repo, a.donor_revision, a.shards, a.local, a.source_base
    TOTALS.clear()
    src = {}
    for f in SHARDS:
        h, base = header(f)
        for k, v in h.items():
            if k.startswith("mtp."):
                s, e = v["data_offsets"]
                src[k] = (f, base + s, base + e)
    with open(LOCAL, "rb") as fh:
        n = struct.unpack("<Q", fh.read(8))[0]
        lh = json.loads(fh.read(n))
        lbase = 8 + n

        def local_bytes(k):
            ls, le = lh[k]["data_offsets"]
            fh.seek(lbase + ls)
            return fh.read(le - ls)

        keys = sorted(src)
        if a.all:
            sample = keys
        else:
            random.seed(20260927)
            big = sorted(keys, key=lambda k: src[k][2] - src[k][1], reverse=True)[:10]
            sample = sorted(set(big + random.sample(keys, min(a.n, len(keys)))))
        
        order = sorted(sample, key=lambda k: (SHARDS.index(src[k][0]), src[k][1]))
        groups = []
        for k in order:
            f, s, e = src[k]
            if groups and groups[-1][0] == f and s - groups[-1][2] <= (1 << 20) and e - groups[-1][1] <= GROUP_MAX:
                groups[-1][2] = e
                groups[-1][3].append(k)
            else:
                groups.append([f, s, e, [k]])
        bad, nbytes = [], 0
        for gi, (f, gs, ge, members) in enumerate(groups):
            blob = rng(f, gs, ge - 1)
            for k in members:
                _, s, e = src[k]
                up = blob[s - gs:e - gs]
                nbytes += len(up)
                if hashlib.sha256(up).digest() != hashlib.sha256(local_bytes(k)).digest():
                    bad.append(k)
                    print("MISMATCH", k, flush=True)
            if a.all and gi % 20 == 0:
                print(f"  {gi + 1}/{len(groups)} groups {nbytes / 1e9:.2f} GB", flush=True)
        
        for s in range(3):
            if local_bytes(f"mtp.{s}.ffn.gate.bias_vl") != local_bytes(f"mtp.{s}.ffn.gate.bias"):
                bad.append(f"mtp.{s}.ffn.gate.bias_vl")
                print("MISMATCH bias_vl", s)
    print(f"VERIFY mode={'all' if a.all else 'sample'} rev={REV} tensors={len(sample)} bytes={nbytes / 1e9:.2f}GB mismatches={len(bad)}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
