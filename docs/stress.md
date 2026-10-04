# The maximum-thinking stress run

[Book](../README.md) · [Complete round table](results.md#maximum-thinking-stress)

## Problem

The two-node engine hung twice with maximum reasoning effort, max_tokens 32,768 and two concurrent streams, on 2026-09-19 and 2026-09-25.
During those hangs `/health` continued answering 200.
The single-node test asks whether that symptom reproduces under a related workload. Different engines and quantizations prevent it from identifying the original cause.

## Client mechanism

[ve_stress.py](../scripts/ve_stress.py) starts concurrent standard-library HTTP clients with streaming and `stream_options.include_usage` enabled.
The four preserved generic prompts ask for a scheduler design/implementation, a real-analysis proof sequence, a Lisp interpreter in Rust, and an extended technical-book outline and chapters.
Requests use temperature 0.6. A round is written as `port:concurrency`; the optional `h` suffix applies high effort directly in request chat-template kwargs.
For unsuffixed rounds the server or a separately configured tier proxy determines effort. The original maximum-effort tier's address is not published.

Each stream records status, first output time, first visible-content time, delta count, reasoning/content character counts, finish reason, usage and elapsed time.
A socket read timeout of 180 s is the silence detector. It detects lack of bytes, not semantic progress; an endless heartbeat stream would be a different failure.
The recorded rationale was that 180 s was well below the roughly 5-minute RPC timeout seen during the two-node failure, not a formally derived threshold.
The 1,700 s client cap is checked while reading events; it is not an independent wall-clock cancellation thread.

Before and after rounds, the client checks health, optionally local Docker container health, and Linux MemAvailable.
On a platform without `/proc/meminfo`, the public version records null memory rather than failing.
Docker checking is opt-in through `--container`; omitting it means container health was not checked.
The heartbeat interval defaults to 120 s. The public adaptation excludes already-finished streams from idle counters and joins completed threads promptly.

## Procedure as run

A single production session ran maximum effort at 2, 4 and 6 concurrent streams, then high effort at 2 streams on the raw endpoint.
The six-stream round reached the configured sequence limit.
Some live fallback traffic continued during the session and competed with the tests.
Every stream requested 32,768 output tokens; the client asked for usage records.
The exact session date is not recorded beyond September 2026.

For an endpoint whose default is already maximum effort, the public equivalent using the recipe's default loopback port is:

```bash
python3 scripts/ve_stress.py --rounds 8888:2,8888:4,8888:6,8888h:2 --health-url http://127.0.0.1:8888/health --model deepseek-v4-flash-vision-exp --container ds4-mia-vision-k22-tp1 --max-tokens 32768 --stall 180 --timeout 1700 --out results/stress
```

This is a generic endpoint substitution, not the historical private port mapping. Confirm the endpoint's effective thinking default before calling an unsuffixed round maximum effort.
The offline recipe runs the same parser and stream logic with synthetic responses, never a model.

## What the results show

The [round table](results.md#maximum-thinking-stress) records 102 minutes with 0 stalls and 0 preemptions; the latter came from server metrics, not the shipped client's counters.
Every sampled health/container check was healthy, MemAvailable stayed between 6.9 and 7.2 GiB, and KV occupancy was about 3%.
At max x2 both streams reached length; at max x4 one stopped naturally at 13,145 tokens.
At max x6 one stopped naturally at 21,795 and five were cut by the client cap.
Full 32,768-token generations at that concurrency would need roughly 1,800-2,100 s, beyond the allowed cap.

The cut streams had no terminal usage record. The reported about 90-100 tok/s aggregate is an estimate, not a measured token count.
Its inputs were 511,788 characters from the five cut streams, the complete stream's 21,795 tokens, and 1,700 s.
Nine streams with usage gave 3.34-3.97 characters/token, mean 3.74: the arithmetic gives 89-103 tok/s, or 93 at the mean, with roughly 15% uncertainty.
The public script emits no full-round aggregate when usage is incomplete; it does not silently substitute zero tokens.

## Measurement failures and limits

Counting streamed deltas made the first estimate about three times too low: speculative acceptance can batch several tokens into one delta.
Use completion tokens from usage. The content-suite public adaptation rejects missing usage for the same reason.

The original heartbeat kept aging finished streams; natural-stop streams appeared idle for 736 s and 346 s.
A high idle value for a finished stream was not evidence of a stall.
The public adaptation excludes them, but this does not retroactively alter historical logs or round wall times.

The x6 round is not a completed full-length concurrency benchmark.
One successful session on one single-node engine neither proves long-term reliability nor explains the two-node hang.
A health-only probe would have missed the original symptom.

**Rule:** detect failure at the token stream, count tokens from usage, and label missing-usage estimates rather than treating client-cut streams as zero-throughput successes.
