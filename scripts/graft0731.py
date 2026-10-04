#!/usr/bin/env python3
"""Graft a pinned text draft into a separate vision snapshot. Strict range checks are mandatory."""
import argparse
import json
import re
import os
import struct
import sys
import time
import urllib.request
from pathlib import Path

REPO = "wrldsuksgo2mars/DeepSeek-V4-Flash-0731-EXL3-K2.1-D2.2-calibrated-v3"
REV = "7827301eed170e2a5e394f45a13cc66561c601ed"
SHARDS = ["model-00002-of-00011.safetensors", "model-00010-of-00011.safetensors", "model-00011-of-00011.safetensors"]
HUB = Path("hf/hub")
VDIR = HUB / "models--wrldsuksgo2mars--DeepSeek-V4-Flash-Vision-Exp-EXL3-K2.2-D2-v1"
VSNAP = VDIR / "snapshots/8347bfb8776287ef2dcab2b46e9f15c655825c3a"
GREV = "0731d22a00000000000000000000000000000001"  # Local offline cache identifier.
GSNAP = VDIR / "snapshots" / GREV
OUTNAME = "model-mtp-draft0731-d22.safetensors"
GAP = 4 << 20  # Coalesce nearby source tensor ranges.


BASE_URL = None

def url(f):
    return f"{BASE_URL or f'https://huggingface.co/{REPO}/resolve/{REV}'}/{f}"


TOTALS = {}


def get(u, start, end):
    """Open an inclusive byte interval and validate status, interval and stable file size."""
    req = urllib.request.Request(u, headers={"Range": f"bytes={start}-{end}"})
    r = urllib.request.urlopen(req, timeout=300)
    cr = r.headers.get("Content-Range", "")
    m = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", cr)
    if r.status != 206 or not m or int(m.group(1)) != start or int(m.group(2)) != end or int(m.group(3)) <= end \
            or TOTALS.setdefault(u, int(m.group(3))) != int(m.group(3)):
        r.close()
        raise IOError(f"bad range response status={r.status} content-range={cr!r} want {start}-{end}")
    return r


def local_header(path):
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        return json.loads(f.read(n))


def header(f):
    with get(url(f), 0, 7) as r:
        n = struct.unpack("<Q", r.read())[0]
    with get(url(f), 8, 7 + n) as r:
        raw = r.read()
    if len(raw) != n:
        raise IOError(f"short header {len(raw)} vs {n} ({f})")
    return json.loads(raw), 8 + n


def fetch_json(name):
    with urllib.request.urlopen(url(name), timeout=120) as r:
        return json.load(r)


def main():
    global REPO, REV, SHARDS, VSNAP, GREV, GSNAP, BASE_URL
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--donor-repo", default=REPO)
    ap.add_argument("--donor-revision", default=REV)
    ap.add_argument("--shards", nargs="+", default=SHARDS)
    ap.add_argument("--target", type=Path, default=VSNAP)
    ap.add_argument("--new-revision", default=GREV)
    ap.add_argument("--source-base", help="Pinned source directory URL; useful for a loopback fixture")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", a.new_revision):
        ap.error("new revision must be a 40-character lowercase hexadecimal value")
    REPO, REV, SHARDS = a.donor_repo, a.donor_revision, a.shards
    VSNAP, GREV = a.target.resolve(), a.new_revision
    GSNAP, BASE_URL = VSNAP.parent / GREV, a.source_base
    TOTALS.clear()
    dry = a.dry_run
    if GSNAP.exists():
        raise SystemExit(f"{GSNAP} already exists; refusing to overwrite a published revision")
    src_q = fetch_json("quantize_config.json")
    src_c = fetch_json("config.json")
    tensors = []  # (file, abs_start, abs_end, name, dtype, shape)
    meta_src = None
    for f in SHARDS:
        h, base = header(f)
        meta_src = h.get("__metadata__", meta_src)
        for k, v in h.items():
            if k.startswith("mtp."):
                a, b = v["data_offsets"]
                tensors.append((f, base + a, base + b, k, v["dtype"], v["shape"]))
    tensors.sort(key=lambda t: (SHARDS.index(t[0]), t[1]))
    total = sum(t[2] - t[1] for t in tensors)
    by_name = {t[3]: t for t in tensors}
    extra = []  # Derive visual router biases from the corresponding donor biases.
    for s in range(3):
        src = by_name[f"mtp.{s}.ffn.gate.bias"]
        extra.append((f"mtp.{s}.ffn.gate.bias_vl", src))
    print(f"mtp tensors {len(tensors)}  bytes {total/1e9:.2f} GB  + bias_vl {len(extra)}", flush=True)


    # Pack source tensors first, followed by derived visual biases.
    hdr, off = {}, 0
    for t in tensors:
        n = t[2] - t[1]
        hdr[t[3]] = {"dtype": t[4], "shape": t[5], "data_offsets": [off, off + n]}
        off += n
    for name, src in extra:
        n = src[2] - src[1]
        hdr[name] = {"dtype": src[4], "shape": src[5], "data_offsets": [off, off + n]}
        off += n
    hdr["__metadata__"] = meta_src or {"format": "pt"}
    hb = json.dumps(hdr, separators=(",", ":")).encode()
    hb += b" " * ((8 - len(hb) % 8) % 8)


    # Preserve source order while coalescing payload requests.
    groups = []
    for t in tensors:
        if groups and groups[-1][0] == t[0] and t[1] - groups[-1][2] <= GAP:
            groups[-1][2] = t[2]
            groups[-1][3].append(t)
        else:
            groups.append([t[0], t[1], t[2], [t]])
    print(f"range requests {len(groups)}", flush=True)
    if dry:
        return

    stage = GSNAP.parent / f".staging-{GREV}-{os.getpid()}"
    stage.mkdir(parents=True)
    out = stage / OUTNAME
    part = out.with_suffix(".part")
    t0 = time.time()
    done = 0
    with open(part, "wb") as w:
        w.write(struct.pack("<Q", len(hb)))
        w.write(hb)
        for f, gs, ge, members in groups:
            for attempt in range(5):
                r = None
                try:
                    r = get(url(f), gs, ge - 1)
                    pos = gs
                    mi = 0
                    while pos < ge:
                        chunk = r.read(min(64 << 20, ge - pos))
                        if not chunk:
                            raise IOError("short read")
                        cstart, cend = pos, pos + len(chunk)
                        while mi < len(members) and members[mi][1] < cend:
                            _, ts, te, *_ = members[mi]
                            a, b = max(ts, cstart), min(te, cend)
                            if a < b:
                                w.write(chunk[a - cstart:b - cstart])
                            if te <= cend:
                                mi += 1
                            else:
                                break
                        pos = cend
                    if r.read(1):
                        raise IOError("extra body")
                    r.close()
                    break
                except Exception as e:
                    if r is not None:
                        r.close()
                    print(f"retry {f} {gs}-{ge} ({e})", flush=True)
                    w.flush()

                    group_out_start = 8 + len(hb) + sum(t[2] - t[1] for t in tensors if (SHARDS.index(t[0]), t[1]) < (SHARDS.index(f), gs))
                    # A retry replaces this group; it never appends to a partial copy.
                    w.seek(group_out_start)
                    w.truncate()
                    time.sleep(5 * (attempt + 1))
            else:
                raise SystemExit(f"FAILED group {f} {gs}-{ge}")
            done += ge - gs
            print(f"  {done/1e9:.2f} GB  {(done/1e6)/(time.time()-t0):.0f} MB/s", flush=True)

        w.flush()
    # Read the copied donor bias bytes locally to create each visual counterpart.
    with open(part, "r+b") as w:
        w.seek(0, 2)
        for name, src in extra:
            so = hdr[src[3]]["data_offsets"]
            w.seek(8 + len(hb) + so[0])
            data = w.read(so[1] - so[0])
            w.seek(0, 2)
            w.write(data)
    size = part.stat().st_size
    assert size == 8 + len(hb) + off, (size, 8 + len(hb) + off)
    part.rename(out)
    print(f"WROTE {out} {size/1e9:.2f} GB in {time.time()-t0:.0f}s", flush=True)


    # Relative links survive a different host/container cache mount path.
    for p in VSNAP.iterdir():
        if p.name in ("model.safetensors.index.json", "config.json", "quantize_config.json"):
            continue
        dst = stage / p.name
        if not dst.exists() and not dst.is_symlink():

            dst.symlink_to(os.path.relpath(p, stage))
    idx = json.loads((VSNAP / "model.safetensors.index.json").read_text())
    for k in list(idx["weight_map"]):
        if k.startswith("mtp."):
            del idx["weight_map"][k]
    for k in hdr:
        if k != "__metadata__":
            idx["weight_map"][k] = OUTNAME

    # Count only tensors referenced by the final index, excluding old draft bytes.
    sizes = {}
    for fname in set(idx["weight_map"].values()):
        path = (stage / fname) if fname == OUTNAME else (VSNAP / fname)
        for k, v in local_header(path).items():
            if k != "__metadata__":
                sizes[(fname, k)] = v["data_offsets"][1] - v["data_offsets"][0]
    idx.setdefault("metadata", {})["total_size"] = sum(sizes[(f, k)] for k, f in idx["weight_map"].items())
    (stage / "model.safetensors.index.json").write_text(json.dumps(idx, indent=2))

    q = json.loads((VSNAP / "quantize_config.json").read_text())
    for k in [k for k in q["tensor_storage"] if k.startswith("mtp.")]:
        del q["tensor_storage"][k]
    for k, v in src_q["tensor_storage"].items():
        if k.startswith("mtp."):
            q["tensor_storage"][k] = v
    q["meta"].setdefault("ds4rt_inline_mixed_namespaces", {})["mtp"] = src_q["meta"]["ds4rt_inline_mixed_namespaces"]["mtp"]
    (stage / "quantize_config.json").write_text(json.dumps(q, indent=2))
    c = json.loads((VSNAP / "config.json").read_text())
    c["quantization_config"]["meta"].setdefault("ds4rt_inline_mixed_namespaces", {})["mtp"] = src_c["quantization_config"]["meta"]["ds4rt_inline_mixed_namespaces"]["mtp"]
    c["num_nextn_predict_layers"] = src_c.get("num_nextn_predict_layers", 1)
    (stage / "config.json").write_text(json.dumps(c, indent=2))
    n_mtp_q = sum(1 for k in q["tensor_storage"] if k.startswith("mtp."))
    stage.rename(GSNAP)  # Publish the completed snapshot atomically.
    print(f"GRAFT_DONE snapshot={GSNAP} mtp_storage={n_mtp_q} nextn={c['num_nextn_predict_layers']}", flush=True)


if __name__ == "__main__":
    main()
