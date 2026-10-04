# Pitfalls and the evidence behind each repair

[Book](../README.md) · [Complete results](results.md)

These are observed failures and recorded repairs unless explicitly marked as an open recommendation.
They are grouped by where a reader would encounter them; they are not claims that every repair was tested on a fresh production deployment.

## Deployment and cache layout

| Symptom | Root cause | Fix |
|---|---|---|
| Published release cannot be pulled anonymously | tag and digest returned unauthorized on 2026-09-25 and 2026-09-26 | build the pinned recipe Dockerfile; both bases pulled anonymously |
| Launcher cannot find the model | entrypoint resolves a Hugging Face cache, not an arbitrary local directory | use the finalizer and write refs/main, or use revision-pinned cache download |
| Cache copy returns rsync exit 23 | root-owned b12x tuning-cache files cannot be read by the copying user | copy snapshots only; expect cold tuning at the destination |
| A caller's override appears ignored | launcher sources the env file after caller variables | generate a per-arm file and select ENV_FILE |
| First short request takes 12 s | kernel-tuning caches are cold | warm once before measuring steady-state throughput |
| An ordinary request returns empty content | maximum thinking consumes the output budget | disable thinking per request or use the documented tier proxy |
| A served-name list fails to provide aliases | entrypoint passes one served-name string | choose one name and alias at the gateway |
| A non-default engine port conflicts with a tier | vLLM probes upward for internal ports | start the tier proxy first; see the tier-proxy sibling |

The reference env leaves GPU memory utilization blank, which resolved to 0.86 for the recorded model. That is a historical condition, not a proof of headroom on a different host state.
Likewise the recorded KV pool varied from 585,831 to 637,044 tokens across eight boots; a different pool is not by itself evidence that a KV dtype change worked.
The finalizer's DL_EXIT=0 marker means the caller reported successful acquisition. It is not a substitute for checking the manifest.
The public validator requires expected model metadata and nonempty text/image output; image correctness still requires inspection against the image.

## Acceptance and comparability

| Symptom | Root cause | Fix |
|---|---|---|
| Text-only control gets zero vision | image requests fail on text-only weights | show no-vision status and means both including and excluding C6 |
| Median hides unstable runs | small item counts and spread above 5 | retain run values and mark the spread |
| Same nominal effort has different cost | engines generate different reasoning lengths | publish completion tokens alongside scores |
| A timeout-heavy category looks like pure capability loss | question timeout scales with output budget | record both budget and timeout scale |
| A larger needle prompt appears to prefill faster | shared prefix gives cache hits | print cached_tokens; use shuffled filler for a separate cold-style probe |
| A doubled-timeout experiment changes nothing | runner overwrites timeout scale from token budget | inspect the stored effective run header |
| A reference alias is assumed to identify a model | the shared served alias pointed at Qwen3.8-Flash-Next instead of the intended DeepSeek model | retain the column only as a worked example of a mislabeled two-node baseline; verify backend identity before comparison |
| The rewritten acceptance gate appears to validate the deployment | both the original quality gate comparison and the rewritten gate were judged against the wrong baseline | mark both decisions invalid for the intended model comparison; rewriting thresholds cannot repair the baseline |

The mislabeled Qwen baseline's 16,384 output tokens and x2.048 timeout scale differ from the single-node DeepSeek arms' 8,000 and x1.0.
The grader build and thinking keys/application also differ: the baseline request enabled thinking with proxy-forced low, while single-node runs used `--thinking on` and request `reasoning_effort: low`. Exact baseline key spelling and grader build identifiers are not recorded here.
The baseline ran on 2026-09-24 versus 2026-09-26 for single-node arms; its pack sessions required a separate port-forwarded re-run after a client network-permission failure. The shared own-bank hash did not equalize the models or conditions. The [worked example](baseline-source-conflict.md) supports no conclusion about the quality cost of moving the intended model from two nodes to one.
The supplementary C9 run is a successful re-run at x1.0, not evidence for doubled timeouts.
The public comparison utility reports arithmetic without quality-gate verdicts and reports missing safety data as unknown; result labels cannot establish model identity, and absence of a safety field cannot establish zero failures.

## Streaming measurements

| Symptom | Root cause | Fix |
|---|---|---|
| Decode rate looks about three times too low | streamed deltas counted as tokens | use usage.completion_tokens |
| Heartbeat reports a long idle interval after natural stop | completed streams remain in the idle list | exclude finished streams; check running-request state |
| Aggregate rate looks implausibly low | client-cut streams counted as zero tokens | require complete usage or publish a labeled estimate |
| Health is 200 while generation is stuck | health endpoint remains responsive during engine hang | detect silence on the token stream |

The historical maximum-thinking x6 round cut five streams at the 1,700 s client cap.
Those streams did not supply usage, so the reported aggregate is estimated from character/token ratios with roughly 15% uncertainty.
The public client emits an incomplete-usage aggregate as null, and returns nonzero for incomplete or failed rounds.
Its timeout is a socket read timeout: incoming bytes can prevent that timeout even if useful token progress stops. That behavior bounds what the test detects.

## Runtime A/B work

| Symptom | Root cause | Fix |
|---|---|---|
| Single-sequence, greedy and NVFP4 arms reproduce baseline | env file overwrites caller settings | separate env files; inspect effective startup arguments |
| Draft-load line cannot identify the active draft | both print "111 params" | log revision plus acceptance length |
| Startup failure has no useful root cause left | next arm removes the container and its logs | save the whole failure log before advancing |
| Production looks much slower than the bench | concurrent live traffic | measure baseline on the idle bench |
| New b12x image builds but will not start | engine/adapter API mismatch | a port is required; no speed claim can be made from the build |
| One-next-layer edit produces no improvement | loader ignores the value in this path | do not transfer the SGLang tip without loader evidence |

The clock-lock command's success did not preserve a post-run frequency measurement.
The corrected single-sequence initialization failure has no recovered root cause.
Do not give either result a stronger causal explanation than the retained evidence supports.
Word-list native replicates span 18%, so a small apparent gain in that class is not resolved by this suite.

## Grafting and verification

| Symptom | Root cause | Fix |
|---|---|---|
| New snapshot is invisible in the container | absolute links refer to a host-only location | use relative links within the cache layout |
| Old draft still loads | index still references original mtp tensors | remap every mtp key to the new file |
| Graft fails loading | stale total_size or quantization storage metadata | recompute referenced bytes; replace mtp storage; copy mixed namespaces |
| Right-size payload contains wrong bytes | server ignored Range or returned another interval | require 206, exact Content-Range and body length; verify source bytes |
| K4/K5 rejected before loading | entrypoint enforces divisibility by 3 | experimental derived image with a guarded removal of that check |
| A/B gain appears and disappears | noisy class and different native replicate | keep repeated native baselines and per-class results |
| Successful load is mistaken for capability acceptance | draft identity and task quality are different checks | verify revision, bytes, speed and capability separately |

The byte verifier checks copied source tensors and the three derived visual biases. It does not establish model-quality equivalence.
The speed gate was missed by shipped K3; K5 passed the written gate but regressed prose. The decision preferred K3's measured all-shape gains and unchanged image.
The capability subset also has a strict C1 miss against the minus-1 rule. Treating it as single-item noise was a recorded decision, not an automatic pass.
The replacement synthetic reasoning prompt carries no historical result.

## Switching and availability

| Symptom | Root cause | Fix |
|---|---|---|
| Switch leaves tier endpoints unavailable | internal engine port claimed a proxy port | start proxy before engine |
| Existence test always finds a proxy | search matches its own shell wrapper | separate check, self-match-resistant pattern, exclude ancestors |
| Switch advances after failed command | failure swallowed in shell control flow | preserve command failure status |
| Rollback reports success with the wrong draft | stale container answers health/alias | check container start time and logged snapshot path |
| Re-running switch keeps wrong state | idempotency checks mode only | compare revision and proxy state |
| Cleanup removes another invocation's state | resources identified only by name | track ownership and verify removal |
| Lock is released twice | duplicate interrupt/cleanup ownership | one owner for lock release |
| Stop touches the second machine's work | stop path also stands down that worker | confirm it is idle first |
| Service stays down after power returns | restart policy no; proxies are background processes | boot units or an effective restart policy plus repeated acknowledged alerts; not implemented in the recorded deployment |

A recipe compose declaration of unless-stopped did not describe the policy of the actual launcher container.
The monitor alerted once on the outage state transition and did not repeat the continuing failure.
The service remained down for three days before detection. The recovery was recorded; a boot-path fix was not.
The post-graft observation has no closing record: no incident was recorded, and the observation was not formally closed.
