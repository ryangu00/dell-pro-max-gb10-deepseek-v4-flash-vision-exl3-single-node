#!/usr/bin/env python3
"""Needle recall probe with optional randomized filler; credentials are read only from an optional environment variable."""
import argparse
import json
import os
import random
import time
import urllib.request
import urllib.error

VOCAB = ("the quick brown fox jumps over a lazy dog near the quiet river bank while tall trees sway "
         "under bright skies and small boats drift past old stone bridges toward the open sea").split()


def post(base, key, body, timeout):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(f"{base}/v1/chat/completions", data=json.dumps(body).encode(), headers=headers)
    return urllib.request.urlopen(req, timeout=timeout)


def stream_first_and_text(resp, t0):
    ttft, text, usage, model = None, [], None, None
    reasoning = []
    for line in resp:
        if not line.startswith(b"data:"):
            continue
        p = line[5:].strip()
        if p == b"[DONE]":
            break
        d = json.loads(p)
        model = d.get("model") or model
        if d.get("usage"):
            usage = d["usage"]
        ch = d.get("choices") or []
        delta = (ch[0].get("delta") or {}) if ch else {}
        tok = delta.get("content") or delta.get("reasoning_content") or delta.get("reasoning")
        if tok:
            if ttft is None:
                ttft = time.time() - t0
            if delta.get("content"):
                text.append(delta["content"])
            else:
                reasoning.append(tok)
    return ttft, "".join(text), usage, model, "".join(reasoning)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8888")
    ap.add_argument("--model", required=True)
    ap.add_argument("--tokens", type=int, required=True)
    ap.add_argument("--timeout", type=float, default=1800)
    ap.add_argument("--max-tokens", type=int, default=400, help="Allow enough output for reasoning and the answer")
    ap.add_argument("--shuffle", action="store_true", help="Randomize filler to reduce prefix-cache reuse")
    ap.add_argument("--key-env", default="API_KEY", help="Optional credential environment variable")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    key = os.environ.get(a.key_env, "")
    out = open(a.out, "a")
    rng = random.Random()
    secret = f"{rng.randint(10**7, 10**8 - 1)}"
    words = [rng.choice(VOCAB) for _ in range(a.tokens)] if a.shuffle else [VOCAB[i % len(VOCAB)] for i in range(a.tokens)]
    pos = rng.randint(int(a.tokens * 0.35), int(a.tokens * 0.65))
    words[pos:pos] = ["\nIMPORTANT: the secret access code is", secret, ". Remember it.\n"]
    prompt = ("Read the following long document. At the end answer the question.\n\n" + " ".join(words) +
              "\n\nQuestion: What is the secret access code mentioned in the document? Answer with digits only.")
    t0 = time.time()
    rec = {"event": "long", "model": a.model, "target_tokens": a.tokens, "needle_pos": pos, "at": t0}
    try:
        with post(a.base, key, {"model": a.model, "stream": True, "max_tokens": a.max_tokens, "temperature": 0.0,
                               "stream_options": {"include_usage": True},
                               "messages": [{"role": "user", "content": prompt}]}, a.timeout) as r:
            ttft, text, usage, model, reasoning = stream_first_and_text(r, t0)
        rec.update(status=200, ttft_s=round(ttft or 0, 1), wall_s=round(time.time() - t0, 1), backend_model=model,
                   usage=usage, answer=text.strip()[:80], exact=(secret in text), secret_in_reasoning=(secret in reasoning),
                   reasoning_chars=len(reasoning))
    except urllib.error.HTTPError as e:
        rec.update(status=e.code, wall_s=round(time.time() - t0, 1), err=e.read()[:300].decode(errors="replace"))
    except Exception as e:
        rec.update(status=-1, wall_s=round(time.time() - t0, 1), err=f"{type(e).__name__}: {e}"[:200])
    out.write(json.dumps(rec) + "\n"); out.close()
    print(json.dumps(rec))
    raise SystemExit(0 if rec.get("status") == 200 and rec.get("exact") else 1)


if __name__ == "__main__":
    main()
