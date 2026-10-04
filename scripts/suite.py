#!/usr/bin/env python3
"""Short-prompt decode suite. Synthetic replacement thinking results must be measured anew."""
import argparse, json, statistics, time, urllib.request, os, uuid
P = {
 "code": "Write a complete Python module implementing an LRU cache with TTL, thread safety, and unit tests using unittest. Code only.",
 "json": "Return a JSON array of 40 objects describing fictional products, each with fields id, name, category, price, tags (list of 3), and a 2-sentence description. JSON only.",
 "words": "List numbered lowercase English words, one per line, from 1 to 500: 1. apple 2. ...",
 "prose": "Write a detailed, concrete travel itinerary for three days in Kyoto in autumn, with times, places, food and transit. Plain prose, no lists.",
}
THINK = {
 "think_synthetic": "A warehouse team must route a mobile robot through crowded aisles while completing an ordered set of deliveries. Charging takes time, some aisles may close without warning, and urgent packages can arrive after departure. Explain how to construct a feasible schedule, compare alternative routes, preserve enough battery for returning, and revise the plan when conditions change. State assumptions and reason through the trade-offs before answering.",
 "think_en": "A warehouse robot must visit 6 shelves with given pairwise travel times and a battery that lasts 40 minutes; explain step by step how you would find a feasible route and what trade-offs matter. Think carefully before answering.",
}
def run(base, model, prompt, max_tokens=512, think=None):
    kw = {"thinking": False} if think is None else {"thinking": True, "reasoning_effort": think}
    body = {"model": model, "messages": [{"role": "user", "content": f"[{uuid.uuid4().hex[:6]}] {prompt}"}], "max_tokens": max_tokens,
            "temperature": 0.6, "top_p": 0.95, "stream": True, "chat_template_kwargs": kw, "stream_options": {"include_usage": True}}
    req = urllib.request.Request(f"{base}/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0 = time.time(); first = None; usage = None; n = 0
    with urllib.request.urlopen(req, timeout=900) as r:
        for line in r:
            line = line.decode().strip()
            if not line.startswith("data:") or line.endswith("[DONE]"): continue
            d = json.loads(line[5:])
            if d.get("usage"): usage = d["usage"]
            for ch in d.get("choices") or []:
                dl = ch.get("delta", {})
                if dl.get("content") or dl.get("reasoning_content") or dl.get("reasoning"):
                    n += 1
                    if first is None: first = time.time() - t0
    wall = time.time() - t0
    ct = (usage or {}).get("completion_tokens")
    if ct is None or first is None or wall <= first:
        raise ValueError("missing usage or token timing; deltas are not tokens")
    return {"ttft": round(first or 0, 2), "wall": round(wall, 1), "tokens": ct, "tok_s": round(ct / (wall - first), 1)}
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--base", default="http://127.0.0.1:8888"); ap.add_argument("--model", default="deepseek-v4-flash-vision-exp")
    ap.add_argument("--trials", type=int, default=3); ap.add_argument("--label", required=True); ap.add_argument("--out", default="arms.jsonl"); ap.add_argument("--warmup", type=int, default=1); ap.add_argument("--think", default=None, choices=("low", "high", "max"), help="Run the two thinking prompts with 1024 output tokens")
    a = ap.parse_args()
    for _ in range(a.warmup): run(a.base, a.model, P["prose"], 64)
    res = {}
    items = THINK.items() if a.think else P.items()
    for k, p in items:
        rs = [run(a.base, a.model, p, 1024 if a.think else 512, a.think) for _ in range(a.trials)]
        res[k] = {"tok_s_median": statistics.median([r["tok_s"] for r in rs]), "ttft_median": statistics.median([r["ttft"] for r in rs]), "trials": rs}
        print(k, res[k]["tok_s_median"], "tok/s", "ttft", res[k]["ttft_median"], flush=True)
    rec = {"label": a.label, "ts": time.strftime("%F %T"), "base": a.base, "summary": {k: v["tok_s_median"] for k, v in res.items()}, "detail": res}
    with open(a.out, "a") as f: f.write(json.dumps(rec) + "\n")
    print("SUITE_DONE", json.dumps(rec["summary"]))
if __name__ == "__main__": main()
